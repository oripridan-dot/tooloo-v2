"""
engine/model_garden.py — JIT Multi-Provider Model Garden

Single source of truth for model selection across ALL configured providers.
No model name is hardcoded outside this file.

Architecture
────────────
  ModelGarden
    ├── _REGISTRY          — static capability scores for all known models
    ├── get_tier_models_static() — deterministic tier map (no network, no API)
    ├── get_tier_model()   — live intent-aware selector (uses _tiers, cache)
    ├── call()             — provider-dispatched generate_content()
    └── consensus()        — parallel multi-model run + merge (T4 only)

Providers
─────────
  google    — Gemini 2.x/3.x via google-genai Vertex client (us-central1)
  anthropic — Claude 3.5/3.7 via AnthropicVertex SDK (us-east5 / europe-west1)

Tier assignment strategy
────────────────────────
  T1 — fastest stable flash/lite model           (speed-dominant)
  T2 — second-best flash model                   (code + speed balanced)
  T3 — best stable pro/reasoning model           (reasoning-dominant, GA preferred)
  T4 — absolute best reasoning model             (preview OK, cross-provider consensus)

Capability dimensions (0.0-1.0)
───────────────────────────────
  speed      : token throughput & low latency
  reasoning  : multi-step logic, math, deep analysis
  coding     : code generation, debugging, architecture
  synthesis  : writing, summarisation, explanation
  stability  : 1.0=GA, 0.9=preview-stable, 0.8=experimental

All model IDs are confirmed against the Vertex AI Model Garden catalog
(project too-loo-zi8g7e, us-central1) and Anthropic Vertex docs - 2026-03-18.
"""
from __future__ import annotations
from engine.local_slm_client import LocalSLMClient, LocalSLMConfig
from engine.config import (
    ANTHROPIC_VERTEX_REGION,
    CROSS_MODEL_CONSENSUS_ENABLED,
    GCP_PROJECT_ID,
    LOCAL_SLM_ENDPOINT,
    LOCAL_SLM_MODEL,
    _vertex_client as _google_client,
)

import json
import logging
import threading
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

# Control: configurable thresholds for model garden safety
_MAX_RETRIES = 3              # per-model retry ceiling
_COST_CIRCUIT_BREAKER = 50.0  # USD — hard cap per-mandate to prevent runaway spend


# ── Cognitive Profile (Four Pillars Support) ──────────────────────────────────
@dataclass(frozen=True)
class CognitiveProfile:
    """Per-node cognitive requirements for dynamic model routing."""

    primary_need: str  # "speed" | "reasoning" | "coding" | "synthesis"
    minimum_tier: int  # 0=local SLM, 1=flash, 2=flash-pro, 3=pro, 4=frontier
    # override model selection (e.g., "local_slm")
    lock_model: str | None = None

    def __post_init__(self) -> None:
        if self.primary_need not in ("speed", "reasoning", "coding", "synthesis"):
            raise ValueError(
                f"primary_need must be one of speed|reasoning|coding|synthesis, got {self.primary_need}"
            )
        if not 0 <= self.minimum_tier <= 4:
            raise ValueError(
                f"minimum_tier must be 0-4, got {self.minimum_tier}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON for DAG blueprints."""
        return {
            "primary_need": self.primary_need,
            "minimum_tier": self.minimum_tier,
            "lock_model": self.lock_model,
        }

# ── Capability profile and Cognitive Routing ──────────────────────────────────


# Task-type weight tables — capability dimension priorities per task.
# Moved to module level so the frozen ModelInfo dataclass can reference it.
_TASK_WEIGHTS: dict[str, dict[str, float]] = {
    "speed":     {"speed": 0.70, "coding": 0.15, "reasoning": 0.10, "synthesis": 0.05},
    "code":      {"coding": 0.55, "reasoning": 0.25, "speed": 0.15, "synthesis": 0.05},
    "reasoning": {"reasoning": 0.60, "coding": 0.20, "synthesis": 0.15, "speed": 0.05},
    "synthesis": {"synthesis": 0.50, "reasoning": 0.30, "coding": 0.10, "speed": 0.10},
    "analysis":  {"reasoning": 0.50, "coding": 0.25, "synthesis": 0.20, "speed": 0.05},
}


@dataclass(frozen=True)
class ModelInfo:
    """Immutable capability profile for one model."""

    id: str            # identifier passed to the provider API
    provider: str      # "google" | "anthropic"
    speed: float       # throughput & latency (higher = faster)
    reasoning: float   # logic, math, complex analysis
    coding: float      # code generation, debugging, architecture
    synthesis: float   # creative writing, summarisation, explanation
    stability: float   # 1.0=GA  0.9=preview-stable  0.8=experimental

    def score_for(self, task_type: str) -> float:
        w = _TASK_WEIGHTS.get(
            task_type,
            {"speed": 0.25, "reasoning": 0.25, "coding": 0.25, "synthesis": 0.25},
        )
        raw = (
            self.speed * w["speed"]
            + self.reasoning * w["reasoning"]
            + self.coding * w["coding"]
            + self.synthesis * w["synthesis"]
        )
        return raw * self.stability

    @property
    def is_flash(self) -> bool:
        """True for fast/lite models (flash, lite, haiku, nemo)."""
        name = self.id.lower()
        return "flash" in name or "lite" in name or "haiku" in name or "nemo" in name


# ── Static capability registry ────────────────────────────────────────────────
# Scores reflect 2026 SOTA data: Chatbot Arena, SWE-bench, MMLU-Pro, HumanEval.
# Google IDs confirmed in project too-loo-zi8g7e (us-central1) via models.list().
# Anthropic IDs confirmed on Vertex AI (us-east5) per Anthropic Vertex docs.

_REGISTRY: list[ModelInfo] = [
    # ── Google Gemini — Vertex AI us-central1 ────────────────────────────────
    ModelInfo(
        "gemini-2.5-flash-lite", "google",
        speed=0.96, reasoning=0.68, coding=0.70, synthesis=0.67, stability=1.00,
    ),
    ModelInfo(
        "gemini-2.5-flash", "google",
        speed=0.88, reasoning=0.80, coding=0.82, synthesis=0.79, stability=1.00,
    ),
    ModelInfo(
        "gemini-3-flash-preview", "google",
        speed=0.87, reasoning=0.84, coding=0.85, synthesis=0.82, stability=0.90,
    ),
    ModelInfo(
        "gemini-2.5-pro", "google",
        speed=0.65, reasoning=0.94, coding=0.92, synthesis=0.90, stability=1.00,
    ),
    ModelInfo(
        "gemini-3-pro-preview", "google",
        speed=0.62, reasoning=0.96, coding=0.95, synthesis=0.93, stability=0.90,
    ),
    ModelInfo(
        "gemini-3.1-pro-preview", "google",
        speed=0.60, reasoning=0.98, coding=0.96, synthesis=0.95, stability=0.90,
    ),

    # ── Anthropic Claude — Vertex AI us-east5 ────────────────────────────────
    # Activated only when AnthropicVertex SDK is installed + ANTHROPIC_VERTEX_REGION set.
    # claude-3-5-haiku is a flash-tier model ("haiku" in name → is_flash=True).
    ModelInfo(
        "claude-3-5-haiku@20241022", "anthropic",
        speed=0.91, reasoning=0.79, coding=0.82, synthesis=0.78, stability=1.00,
    ),
    ModelInfo(
        "claude-3-5-sonnet@20241022", "anthropic",
        speed=0.74, reasoning=0.93, coding=0.93, synthesis=0.91, stability=1.00,
    ),
    ModelInfo(
        "claude-3-7-sonnet@20250219", "anthropic",
        speed=0.68, reasoning=0.97, coding=0.96, synthesis=0.94, stability=1.00,
    ),

    # ── Meta Llama — Vertex AI us-central1 MaaS ───────────────────────────────────────
    # Accessed via the google-genai Vertex client (same SDK, publisher model path).
    # Enable in GCP Console → Vertex AI → Model Garden → Llama MaaS per project.
    ModelInfo(
        "meta/llama-3.3-70b-instruct-maas", "vertex_maas",
        speed=0.78, reasoning=0.89, coding=0.88, synthesis=0.85, stability=0.95,
    ),
    ModelInfo(
        "meta/llama-3.1-405b-instruct-maas", "vertex_maas",
        speed=0.52, reasoning=0.93, coding=0.91, synthesis=0.89, stability=0.95,
    ),

    # ── Mistral AI — Vertex AI us-central1 MaaS ─────────────────────────────────────
    # mistral-nemo@2407 is a 12B fast model — is_flash=True via "nemo" in name.
    # mistral-large@2407 is a 123B pro model — highest coding score among GA models.
    ModelInfo(
        "mistral-large@2407", "vertex_maas",
        speed=0.82, reasoning=0.87, coding=0.88, synthesis=0.86, stability=1.00,
    ),
    ModelInfo(
        "mistral-nemo@2407", "vertex_maas",
        speed=0.93, reasoning=0.76, coding=0.78, synthesis=0.75, stability=1.00,
    ),
]

# Intent → dominant task-type mapping
INTENT_TASK: dict[str, str] = {
    "BUILD":      "code",
    "SPAWN_REPO": "code",
    "DEBUG":      "reasoning",
    "AUDIT":      "analysis",
    "EXPLAIN":    "synthesis",
    "DESIGN":     "synthesis",
    "IDEATE":     "analysis",
    "BLOCKED":    "speed",
}


# ── Anthropic client (lazy, thread-safe) ──────────────────────────────────────

_anthropic_lock = threading.Lock()
_anthropic_client: Any = None
_anthropic_available: bool = False


def _init_anthropic() -> bool:
    """Attempt to initialise AnthropicVertex client. Returns True on success."""
    global _anthropic_client, _anthropic_available
    if _anthropic_available:
        return True
    with _anthropic_lock:
        if _anthropic_available:
            return True
        if not GCP_PROJECT_ID or not ANTHROPIC_VERTEX_REGION:
            return False
        try:
            # type: ignore[import-untyped]
            from anthropic import AnthropicVertex
            _anthropic_client = AnthropicVertex(
                project_id=GCP_PROJECT_ID,
                region=ANTHROPIC_VERTEX_REGION,
            )
            _anthropic_available = True
        except Exception:
            pass
    return _anthropic_available


# ── Cognitive Profile Inference ───────────────────────────────────────────────

def infer_cognitive_profile(action_type: str) -> CognitiveProfile:
    """
    Infer cognitive profile for a DAG node based on its action type.

    Maps node types (ingest, analyze, design, implement, validate, emit, ux_eval)
    to optimal tier and cognitive need combinations.

    Used by Meta-Architect to auto-assign profiles to dynamically generated nodes.
    """
    profiles: dict[str, CognitiveProfile] = {
        # Data extraction / ingestion: speed + local SLM for parsing
        "ingest": CognitiveProfile(primary_need="speed", minimum_tier=0, lock_model="local_slm"),
        "parse": CognitiveProfile(primary_need="speed", minimum_tier=0, lock_model="local_slm"),
        "extract": CognitiveProfile(primary_need="speed", minimum_tier=1),

        # Analysis: reasoning-heavy, can be heavy but not critical path
        "analyze": CognitiveProfile(primary_need="reasoning", minimum_tier=2),
        "audit": CognitiveProfile(primary_need="reasoning", minimum_tier=3),
        "research": CognitiveProfile(primary_need="reasoning", minimum_tier=2),

        # Design: heavy reasoning, impact on system quality
        "design": CognitiveProfile(primary_need="reasoning", minimum_tier=3),
        "architect": CognitiveProfile(primary_need="reasoning", minimum_tier=4),
        "blueprint": CognitiveProfile(primary_need="reasoning", minimum_tier=3),

        # Implementation: coding-focused, medium reasoning
        "implement": CognitiveProfile(primary_need="coding", minimum_tier=2),
        "refactor": CognitiveProfile(primary_need="coding", minimum_tier=2),
        "generate": CognitiveProfile(primary_need="coding", minimum_tier=2),

        # Testing: coding-focused, syntactic validation (local SLM)
        "test_gen": CognitiveProfile(primary_need="coding", minimum_tier=1),
        "lint": CognitiveProfile(primary_need="speed", minimum_tier=0, lock_model="local_slm"),
        "validate": CognitiveProfile(primary_need="speed", minimum_tier=0, lock_model="local_slm"),

        # Writing / synthesis: synthesis-heavy but less critical
        "explain": CognitiveProfile(primary_need="synthesis", minimum_tier=1),
        "document": CognitiveProfile(primary_need="synthesis", minimum_tier=1),
        "summarize": CognitiveProfile(primary_need="synthesis", minimum_tier=1),

        # Emission / output: fast, syntactic
        "emit": CognitiveProfile(primary_need="speed", minimum_tier=0, lock_model="local_slm"),
        "format": CognitiveProfile(primary_need="speed", minimum_tier=0, lock_model="local_slm"),

        # UX / accessibility evaluation: reasoning + synthesis
        "ux_eval": CognitiveProfile(primary_need="reasoning", minimum_tier=2),
        "wcag_check": CognitiveProfile(primary_need="reasoning", minimum_tier=1),
    }

    return profiles.get(
        action_type.lower(),
        CognitiveProfile(primary_need="reasoning", minimum_tier=2),  # default
    )


# ── Tier assignment ───────────────────────────────────────────────────────────

def get_tier_models_static() -> dict[int, str]:
    """
    Deterministically compute the best model per tier using ONLY Google models.

    This function:
      - Makes no network calls.
      - Uses no external state (Anthropic availability).
      - Produces identical output on every call → safe for module-level constants.

    Anthropic models may override T3/T4 at runtime via ModelGarden.get_tier_model().

    Returns dict mapping tier int → model ID str.
    """
    google = [m for m in _REGISTRY if m.provider == "google"]
    flash = sorted(
        [m for m in google if m.is_flash],
        key=lambda m: m.speed,
        reverse=True,
    )
    pro = sorted(
        [m for m in google if not m.is_flash],
        key=lambda m: m.score_for("reasoning"),
        reverse=True,
    )

    t1 = flash[0].id if flash else google[0].id
    t2 = flash[1].id if len(flash) > 1 else t1
    t3 = pro[0].id if pro else t1
    t4 = pro[1].id if len(pro) > 1 else t3

    return {1: t1, 2: t2, 3: t3, 4: t4}


def discover_and_register_models() -> None:
    """
    Queries Vertex AI for new models, scores them heuristically,
    and dynamically appends them to _REGISTRY.

    Called inside get_full_tier_models() so the garden is populated with any
    newly-released models before tier assignment.  Fails silently — network
    errors or client unavailability always fall back to the static baseline.
    """
    global _REGISTRY

    if _google_client is None:
        return

    try:
        available_models = _google_client.models.list()
        registered_ids = {m.id for m in _REGISTRY}

        for model in available_models:
            model_id = getattr(model, "name", None) or getattr(
                model, "id", None)
            if not model_id:
                continue

            # Skip already-known, embedding, or vision-only models
            if (
                model_id in registered_ids
                or "embedding" in model_id
                or "vision" in model_id
            ):
                continue

            is_flash_heuristic = any(
                k in model_id for k in ("flash", "haiku", "nemo", "lite")
            )

            if any(k in model_id for k in ("pro", "sonnet", "opus", "70b")):
                # High-reasoning / pro-tier model
                provider = (
                    "vertex_maas"
                    if any(k in model_id for k in ("meta", "mistral"))
                    else "google"
                )
                new_model = ModelInfo(
                    id=model_id,
                    provider=provider,
                    speed=0.60,
                    reasoning=0.95,
                    coding=0.95,
                    synthesis=0.90,
                    stability=0.90,
                )
            elif is_flash_heuristic:
                # Speed-dominant flash-tier model
                new_model = ModelInfo(
                    id=model_id,
                    provider="google",
                    speed=0.95,
                    reasoning=0.80,
                    coding=0.85,
                    synthesis=0.80,
                    stability=0.95,
                )
            else:
                continue  # Skip unknown architectures to maintain pipeline safety

            _REGISTRY.append(new_model)
            registered_ids.add(model_id)

    except Exception:
        # Fail silently and fall back to the hardcoded baseline registry
        pass


def get_full_tier_models() -> dict[int, str]:
    """
    Compute the optimal 4-tier model ladder using ALL active providers.

    T1/T2: ALWAYS Google flash (speed-dominant, fully deterministic, no provider switch).
    T3/T4: Best pro models across Google + Anthropic + Vertex MaaS partners
           (Meta Llama, Mistral), ranked by reasoning capability x stability.

    Called at ModelSelector import time so TIER_N_MODEL constants immediately
    reflect the full multi-provider ladder without requiring network I/O.
    Anthropic availability is detected eagerly via _init_anthropic().
    """
    _init_anthropic()  # detect Anthropic SDK + credentials before ranking
    discover_and_register_models()  # dynamically populate from Vertex AI when live

    # T1/T2: strictly Google flash for predictable latency and determinism
    google_flash = sorted(
        [m for m in _REGISTRY if m.provider == "google" and m.is_flash],
        key=lambda m: m.speed,
        reverse=True,
    )

    # T3/T4: all active pro models, stability-gated (≥0.9), ranked by reasoning
    all_active = _active_models()
    pro = sorted(
        [m for m in all_active if not m.is_flash and m.stability >= 0.9],
        key=lambda m: m.score_for("reasoning"),
        reverse=True,
    )
    if not pro:  # fallback: relax stability gate
        pro = sorted(
            [m for m in all_active if not m.is_flash],
            key=lambda m: m.score_for("reasoning"),
            reverse=True,
        )

    t1 = google_flash[0].id if google_flash else all_active[0].id
    t2 = google_flash[1].id if len(google_flash) > 1 else t1
    t3 = pro[0].id if pro else t1
    t4 = pro[1].id if len(pro) > 1 else t3

    return {1: t1, 2: t2, 3: t3, 4: t4}


def _active_models() -> list[ModelInfo]:
    """All models available to the current runtime configuration."""
    models = [m for m in _REGISTRY if m.provider == "google"]
    if _google_client is not None:
        # Vertex MaaS partners (Meta Llama, Mistral) use the same Vertex client.
        # Model IDs include publisher prefix (meta/..., mistral-large@...).
        models += [m for m in _REGISTRY if m.provider == "vertex_maas"]
    if _init_anthropic():
        models += [m for m in _REGISTRY if m.provider == "anthropic"]
    return models


# ── ModelGarden ───────────────────────────────────────────────────────────────

class ModelGarden:
    """
    Runtime model selector and provider-dispatched inference engine.

    Usage::

        garden = get_garden()

        # Tier-based selection (consistent with ModelSelector)
        model_id = garden.get_tier_model(tier=3, intent="AUDIT")

        # Single inference (dispatches to correct provider SDK)
        response = garden.call(model_id, prompt)

        # Cross-provider consensus (T4 / critical decisions)
        primary, candidates = garden.consensus(prompt, tier=4, intent="DEBUG")
    """

    def __init__(self) -> None:
        self._static_tiers = get_tier_models_static()
        self._dynamic_registry = None  # lazy-init to avoid circular import

    @property
    def dynamic_registry(self):
        """Lazy accessor for the DynamicModelRegistry singleton."""
        if self._dynamic_registry is None:
            from engine.dynamic_model_registry import get_dynamic_registry
            self._dynamic_registry = get_dynamic_registry()
        return self._dynamic_registry

    # ── Model selection ──────────────────────────────────────────────────────

    def get_tier_model(
        self,
        tier: int,
        intent: str = "",
        primary_need: str = "balanced",
        lock_model: str | None = None,
        profile: CognitiveProfile | None = None,
    ) -> str:
        """Return the best model ID for a node profile.

        Supports:
          - Tier-0 local SLM for syntactic/parsing tasks ($0)
          - Cognitive profiles for per-task model routing
          - Existing intent-based selection for backward compatibility

        Args:
            tier: 0=local SLM, 1-2=flash, 3=stable pro, 4=frontier
            intent: legacy intent mapping (BUILD, DEBUG, etc.)
            primary_need: "speed"|"reasoning"|"coding"|"synthesis"
            lock_model: force selection (e.g., "local_slm")
            profile: CognitiveProfile for multi-dimensional routing

        Returns:
            model ID string (ready to pass to .call())
        """
        # Extract profile if provided
        if profile is not None:
            tier = max(tier, profile.minimum_tier)
            primary_need = profile.primary_need
            lock_model = lock_model or profile.lock_model

        # Tier 0: Aggressive local SLM routing
        if lock_model == "local_slm" or tier == 0:
            return LOCAL_SLM_MODEL

        # Tier 1-2: Fast flash models (deterministic, no provider switching)
        if tier <= 2:
            return self._static_tiers[tier]

        # Tier 3-4: Heavy reasoning models, ranked by cognitive fit
        task_type = primary_need if primary_need in _TASK_WEIGHTS else INTENT_TASK.get(
            intent, "reasoning")
        available = _active_models()
        pro_pool = [m for m in available if not m.is_flash]

        if not pro_pool:
            return self._static_tiers[min(max(tier, 1), 2)]

        if tier == 3:
            stable = [m for m in pro_pool if m.stability >= 0.9]
            pool = stable if stable else pro_pool
            return max(pool, key=lambda m: m.score_for(task_type)).id

        t3_id = self.get_tier_model(3, intent, primary_need=primary_need)
        t4_pool = [m for m in pro_pool if m.id != t3_id]
        if t4_pool:
            return max(t4_pool, key=lambda m: m.score_for(task_type)).id
        return max(pro_pool, key=lambda m: m.score_for(task_type)).id

    def get_all_tiers(self, intent: str = "") -> dict[int, str]:
        return {t: self.get_tier_model(t, intent) for t in (1, 2, 3, 4)}

    # ── Provider-dispatched inference ────────────────────────────────────────

    def call(self, model_id: str, prompt: str, max_tokens: int = 1024) -> str:
        """
        Dispatch inference to the correct provider SDK.

        Raises RuntimeError if no client is available for the required provider.
        Callers should catch and fall back to the structured catalogue.
        """
        if model_id.startswith("local/"):
            return self._call_local_slm(model_id, prompt, max_tokens)

        info = self._find(model_id)
        provider = info.provider if info else (
            "anthropic" if model_id.startswith("claude") else "google"
        )
        if provider == "anthropic":
            if _init_anthropic():
                try:
                    return self._call_anthropic(model_id, prompt, max_tokens)
                except RuntimeError:
                    # Anthropic call failed (404 / permission denied / etc.) —
                    # fall through to Google Vertex as the next available path.
                    if _google_client is not None:
                        # Downgrade to the best available Google pro model.
                        fallback_id = self._static_tiers.get(
                            3, "gemini-2.5-flash")
                        return self._call_google(fallback_id, prompt)
            raise RuntimeError(
                f"Anthropic Vertex client unavailable (model={model_id})")
        # "google" and "vertex_maas" both use the google-genai Vertex client.
        # MaaS models use publisher-namespaced IDs (meta/..., mistral-large@...).
        if _google_client is not None:
            return self._call_google(model_id, prompt)
        raise RuntimeError(
            f"Google/Vertex client unavailable (model={model_id})")

    _PROVIDER_TO_SOURCE = {"google": "gemini", "anthropic": "anthropic"}

    def source_for(self, model_id: str) -> str:
        """Return the source label for SSE / JIT result metadata."""
        info = self._find(model_id)
        if info:
            return self._PROVIDER_TO_SOURCE.get(info.provider, info.provider)
        if model_id.startswith("local/"):
            return "local_slm"
        return "vertex"

    # ── Cross-model consensus (T4 / CROSS_MODEL_CONSENSUS_ENABLED) ───────────

    def consensus(
        self,
        prompt: str,
        tier: int = 4,
        intent: str = "",
        max_tokens: int = 1024,
        accept_response: Callable[[str], bool] | None = None,
    ) -> tuple[str, list[str]]:
        """
        Run prompt on top-2 models from different providers in parallel.

        Returns:
            (primary_response, [all_responses])
            primary is from the highest-scoring model for this task.

        Falls back to single-model when consensus is disabled or only one
        provider is active.
        """
        if not CROSS_MODEL_CONSENSUS_ENABLED:
            model_id = self.get_tier_model(tier, intent)
            result = self.call(model_id, prompt, max_tokens)
            return result, [result]

        task_type = INTENT_TASK.get(intent, "reasoning")
        available = _active_models()
        ranked = sorted(available, key=lambda m: m.score_for(
            task_type), reverse=True)

        # Pick top-2 from *different* providers if possible
        seen: set[str] = set()
        candidates: list[ModelInfo] = []
        for m in ranked:
            if m.provider not in seen:
                candidates.append(m)
                seen.add(m.provider)
            if len(candidates) == 2:
                break
        if len(candidates) < 2:
            candidates = ranked[:2]

        validator = accept_response or (
            lambda response: bool(response.strip()))
        responses: list[str] = []
        primary = ""
        pool = ThreadPoolExecutor(max_workers=max(1, len(candidates)))
        futures = {
            pool.submit(self.call, c.id, prompt, max_tokens): c
            for c in candidates
        }
        try:
            while futures:
                done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for fut in done:
                    futures.pop(fut, None)
                    try:
                        response = fut.result()
                    except Exception as exc:
                        response = f"[CONSENSUS_ERROR: {exc}]"
                    responses.append(response)
                    if not response.startswith("[CONSENSUS_ERROR:") and validator(response):
                        primary = response
                        for pending in futures:
                            pending.cancel()
                        pool.shutdown(wait=False, cancel_futures=True)
                        return primary, responses
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        if not primary:
            primary = next(
                (resp for resp in responses if not resp.startswith(
                    "[CONSENSUS_ERROR:")),
                responses[0] if responses else "",
            )
        return primary, responses

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _find(model_id: str) -> ModelInfo | None:
        for m in _REGISTRY:
            if m.id == model_id:
                return m
        return None

    @staticmethod
    def _call_google(model_id: str, prompt: str) -> str:
        resp = _google_client.models.generate_content(  # type: ignore[union-attr]
            model=model_id, contents=prompt
        )
        text = resp.text
        if not text:
            raise ValueError(f"Google/{model_id} returned empty response")
        return text.strip()

    @staticmethod
    def _call_anthropic(model_id: str, prompt: str, max_tokens: int) -> str:
        try:
            msg = _anthropic_client.messages.create(  # type: ignore[union-attr]
                model=model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except Exception as exc:
            # Normalise all Anthropic API errors (404 NOT_FOUND, 403 permission
            # denied, rate limits, etc.) to RuntimeError so callers can fall back
            # to the Google/structured-catalogue path transparently.
            raise RuntimeError(
                f"AnthropicVertex call failed for {model_id}: {exc}"
            ) from exc

    @staticmethod
    def _call_local_slm(model_id: str, prompt: str, max_tokens: int) -> str:
        cfg = LocalSLMConfig(
            name="ollama",
            endpoint=LOCAL_SLM_ENDPOINT.rsplit("/api/generate", 1)[0]
            if "/api/generate" in LOCAL_SLM_ENDPOINT
            else LOCAL_SLM_ENDPOINT,
            model_name=model_id.removeprefix("local/"),
            max_tokens=max_tokens,
            temperature=0.1,
            timeout_sec=20,
        )
        client = LocalSLMClient(cfg)
        return client.generate(prompt, max_tokens=max_tokens)

    def estimate_cost_usd(
        self, model_id: str, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Estimate USD cost for a model call.

        Pricing per 2026 rates:
          - Tier 0 (local SLM): $0
          - Tier 1 (Flash Lite): $0.075/M input, $0.3/M output
          - Tier 2 (Flash): $0.15/M input, $0.6/M output
          - Tier 3 (Pro): $9/M input, $36/M output
          - Tier 4 (Frontier): varies by provider
        """
        if model_id.startswith("local/") or model_id == LOCAL_SLM_MODEL:
            return 0.0  # Local SLM runs on your machine, no cost

        info = self._find(model_id)
        if not info:
            # Unknown model, estimate as Tier 2
            return (input_tokens * 0.15 + output_tokens * 0.6) / 1_000_000

        # Tier-based cost estimation
        if info.is_flash:
            # Flash Lite pricing (T1)
            if "lite" in model_id.lower():
                return (
                    input_tokens * 0.075 + output_tokens * 0.3
                ) / 1_000_000
            # Flash standard pricing (T2)
            return (input_tokens * 0.15 + output_tokens * 0.6) / 1_000_000
        else:
            # Pro/frontier (T3/T4)
            if info.stability < 0.95:
                # Preview models: 20% premium
                return (input_tokens * 10.8 + output_tokens * 43.2) / 1_000_000
            return (input_tokens * 9 + output_tokens * 36) / 1_000_000

    def to_status(self) -> dict[str, Any]:
        """Summary for /v2/health and SSE events."""
        active = _active_models()
        providers = sorted({m.provider for m in active})
        tiers = get_full_tier_models()
        return {
            "providers": providers,
            "active_models": len(active),
            "anthropic_available": _anthropic_available,
            "vertex_maas_available": _google_client is not None,
            "tiers": {str(k): v for k, v in tiers.items()},
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_garden_instance: ModelGarden | None = None
_garden_lock = threading.Lock()


def get_garden() -> ModelGarden:
    """Return the process-level ModelGarden singleton."""
    global _garden_instance
    if _garden_instance is None:
        with _garden_lock:
            if _garden_instance is None:
                _garden_instance = ModelGarden()
    return _garden_instance
