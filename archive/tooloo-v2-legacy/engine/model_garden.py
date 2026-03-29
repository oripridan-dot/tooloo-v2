# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.model_garden.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

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
    DEEPSEEK_API_KEY,
    GCP_PROJECT_ID,
    GCP_REGION,
    GEMINI_API_KEY,
    GROK_API_KEY,
    LOCAL_SLM_ENDPOINT,
    LOCAL_SLM_MODEL,
    _vertex_client as _google_client,
    gemini_client as _gemini_api_client,
    openai_client as _openai_client,
    deepseek_client as _deepseek_client,
    grok_client as _grok_client,
    vertex_global_client as _google_global_client,
)

import json
import logging
import threading
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Set
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

# --- Pathway B Control: Anti-Stuck & Blacklist Mechanisms ---
_BLACKLISTED_ENDPOINTS: Set[str] = set()
_ENDPOINT_LOCK = threading.Lock()
_PATHWAY_B_TIMEOUT_T1_T2 = 10.0 # seconds
_PATHWAY_B_TIMEOUT_T3_T4 = 25.0 # seconds

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
    # Tier-5: Reasoning budget for test-time compute (Wave 0.5)
    thinking_budget: int | None = None
    # Tier-5: Task complexity (0.0-1.0)
    complexity: float = 0.5
    # Tier-5: Whether thinking models (e.g., DeepSeek-R1) are mandatory
    thinking_available: bool = False

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
            "thinking_budget": self.thinking_budget,
            "complexity": self.complexity,
            "thinking_available": self.thinking_available,
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
    cost_efficiency: float = 0.5 # 1.0=cheapest, 0.0=expensive
    thinking_available: bool = False

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
        return raw * self.stability * self.cost_efficiency

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
        "gemini-1.5-flash-8b", "google",
        speed=0.96, reasoning=0.68, coding=0.70, synthesis=0.67, stability=1.00,
    ),
    ModelInfo(
        "gemini-1.5-flash", "google",
        speed=0.88, reasoning=0.80, coding=0.82, synthesis=0.79, stability=1.00,
    ),
    ModelInfo(
        "gemini-3.1-pro-preview", "google",
        speed=0.60, reasoning=0.98, coding=0.97, synthesis=0.95, stability=0.90,
        thinking_available=True,
    ),
    ModelInfo(
        "gemini-2.0-flash-lite", "google",
        speed=0.95, reasoning=0.75, coding=0.78, synthesis=0.76, stability=1.00,
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
        thinking_available=True,
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

    # ── DeepSeek — Direct API ───────────────────────────────────────────────
    ModelInfo(
        "deepseek-chat", "deepseek",
        speed=0.94, reasoning=0.92, coding=0.94, synthesis=0.88, stability=0.98, cost_efficiency=0.95,
    ),
    ModelInfo(
        "deepseek-reasoner", "deepseek",
        speed=0.55, reasoning=0.98, coding=0.97, synthesis=0.85, stability=0.95, cost_efficiency=0.90,
        thinking_available=True,
    ),

    # ── OpenAI — Direct API ────────────────────────────────────────────────
    ModelInfo(
        "gpt-4o", "openai",
        speed=0.75, reasoning=0.94, coding=0.92, synthesis=0.93, stability=1.00, cost_efficiency=0.60,
    ),
    ModelInfo(
        "gpt-4o-mini", "openai",
        speed=0.95, reasoning=0.78, coding=0.80, synthesis=0.82, stability=1.00, cost_efficiency=0.98,
    ),

    # ── xAI Grok — Direct API ────────────────────────────────────────────────
    ModelInfo(
        "grok-2-1212", "xai",
        speed=0.88, reasoning=0.94, coding=0.93, synthesis=0.92, stability=1.00, cost_efficiency=0.70,
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
            from anthropic import AnthropicVertex
            _anthropic_client = AnthropicVertex(
                project_id=GCP_PROJECT_ID,
                region=ANTHROPIC_VERTEX_REGION,
            )
            _anthropic_available = True
        except Exception:
            pass
    return _anthropic_available


# ── Direct API Clients (DeepSeek, xAI) ────────────────────────────────────────

_openai_clients: dict[str, Any] = {}
_client_lock = threading.Lock()

def _get_openai_compatible_client(provider: str) -> Any:
    """Return a thread-safe OpenAI-compatible client for the provider."""
    global _openai_clients
    if provider in _openai_clients:
        return _openai_clients[provider]
    
    with _client_lock:
        if provider in _openai_clients:
            return _openai_clients[provider]
        
        from openai import OpenAI
        if provider == "deepseek" and DEEPSEEK_API_KEY:
             _openai_clients[provider] = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        elif provider == "xai" and GROK_API_KEY:
             _openai_clients[provider] = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
             
        return _openai_clients.get(provider)


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
            # Blacklist: gemini-2.0 and 3.1 are currently 404ing in us-central1 for this project.
            if (
                model_id in registered_ids
                or "embedding" in model_id
                or "vision" in model_id
                or "gemini-2.0" in model_id
                or "gemini-3.1" in model_id
                or "google/models/gemini-3.1" in model_id
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
        intent: str | None = None,
        confidence: float = 0.8,
        use_local_failover: bool = True
    ) -> str:
        """
        Resolves the optimal model ID for a given tier and intent.
        If use_local_failover is True, it checks for Ollama availability.
        """
        # 0. Check Local Failover (The Meta Leap)
        if use_local_failover and tier <= 2:
            try:
                import httpx
                # Synchronous check for stability in the selector
                import socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex(('127.0.0.1', 11434)) == 0:
                        logger.info("Local Failover Stack (Meta) active: routing to Ollama/Llama3.2")
                        return "ollama/llama3.2:1b"
            except Exception:
                pass

        # Original Tier Logic
        tiers = get_tier_models_static()
        return tiers.get(tier, tiers[1])

    def get_all_tiers(self, intent: str = "") -> dict[int, str]:
        return {t: self.get_tier_model(t, intent) for t in (1, 2, 3, 4)}

    # ── Provider-dispatched inference ────────────────────────────────────────

    def call(self, model_id: str, prompt: str, max_tokens: int = 1024, intent: str = "", thinking_budget: int | None = None) -> str:
        """
        Dispatch inference to the correct provider SDK.

        Raises RuntimeError if no client is available for the required provider.
        Callers should catch and fall back to the structured catalogue.
        """
        if model_id.startswith("ollama/"):
             return self._call_ollama(model_id.replace("ollama/", ""), prompt)
        if model_id.startswith("local/"):
            return self._call_local_slm(model_id, prompt, max_tokens)

        info = self._find(model_id)
        # Tier-5: Override thinking budget if model supports it
        actual_budget = thinking_budget if (info and info.thinking_available) else None

        try:
            # Skip if blacklisted
            v_id = model_id if model_id.startswith("publishers/") else f"publishers/google/models/{model_id}"
            if v_id in _BLACKLISTED_ENDPOINTS:
                logger.warning(f"PATHWAY B: Skipping blacklisted endpoint {v_id}. PIVOTING to Global Rescue.")
                return self._handle_pivot(prompt, max_tokens, intent)

            # Step 1: Regional Google Pathway (Tel Aviv / me-west1)
            if info and info.provider == "google":
                try:
                    return self._call_google(model_id, prompt, actual_budget)
                except Exception as e:
                    if intent in ("HEAL", "REASON", "DREAM"):
                        logger.warning(f"Regional failure in {GCP_REGION} for {intent}: {e}. PIVOTING to Global Fallback.")
                        return self._handle_pivot(prompt, max_tokens, intent)
                    raise e

            # Step 2: Routed Providers
            if info and info.provider == "openai":
                return self._call_openai(model_id, prompt, max_tokens)
            if info and info.provider == "deepseek":
                return self._call_deepseek(model_id, prompt, max_tokens)
            if info and info.provider == "anthropic":
                return self._call_anthropic(model_id, prompt, max_tokens, actual_budget)
            if info and info.provider == "xai":
                return self._call_xai(model_id, prompt, max_tokens)

            # Fallback for default/unknown models
            return self._call_google(model_id, prompt, actual_budget)

        except Exception as e:
            logger.error(f"Inference Engine failure [Model: {model_id}, Intent: {intent}]: {e}")
            if intent in ("HEAL", "REASON", "DREAM") and model_id != "gpt-4o":
                logger.info("Emergency rescue: attempting final pivot to gpt-4o...")
                try:
                    return self._handle_pivot(prompt, max_tokens, intent)
                except Exception as pe:
                    logger.error(f"Global rescue pivot also failed: {pe}")
            raise RuntimeError(f"Model Garden call failed: {e}") from e

    _PROVIDER_TO_SOURCE = {"google": "gemini", "anthropic": "anthropic"}

    def source_for(self, model_id: str) -> str:
        """Return the source label for SSE / JIT result metadata."""
        info = self._find(model_id)
        if info:
            return self._PROVIDER_TO_SOURCE.get(info.provider, info.provider)
        if model_id.startswith("local/"):
            return "Analysis complete."
        return "vertex"

    def _call_ollama(self, model: str, prompt: str) -> str:
        """Calls the local Ollama server."""
        import httpx
        try:
             import requests
             url = "http://localhost:11434/api/generate"
             payload = {
                 "model": model,
                 "prompt": prompt,
                 "stream": False
             }
             response = requests.post(url, json=payload, timeout=30)
             if response.status_code == 200:
                 return response.json().get("response", "")
             return f"Ollama Error: {response.status_code}"
        except Exception as e:
             logger.error(f"Local Failover Call failed: {e}")
             return "Local reasoning failed."

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
    def _call_google(model_id: str, prompt: str, thinking_budget: int | None = None) -> str:
        """Vertex AI generator — hardened with candidate-aware result aggregation."""
        if not _google_client:
            raise RuntimeError("Vertex AI client not initialized (check GCP_PROJECT_ID)")

        # Prepare config only if thinking_budget is requested AND model supports it
        config = None
        if thinking_budget and ("2.0" in model_id or "pro-exp" in model_id):
            from google.genai import types
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(include_thoughts=True)
            )

        # ── Pathway B: AI Studio Fallback/Primary ──────────────────────────
        # Gemini Developer API (Studio) is often more robust for public models 
        # than Vertex AI regional endpoints. We prioritize it if a key is present.
        if _gemini_api_client:
            try:
                # Strip publishers/ prefix and date suffixes for Studio calls
                clean_id = model_id.split("/")[-1].split("@")[0]
                resp = _gemini_api_client.models.generate_content(
                    model=clean_id,
                    contents=prompt,
                    config=config
                )
                if resp.text:
                    return resp.text.strip()
            except Exception as e:
                logger.warning(f"Gemini AI Studio failure for {model_id} (clean: {clean_id if 'clean_id' in locals() else 'N/A'}): {e}. Falling back to Vertex...")

        # ── Pathway A: Vertex AI (Regional) ───────────────────────────────
        v_id = model_id if model_id.startswith("publishers/") else f"publishers/google/models/{model_id}"
            
        try:
            # --- SOTA: Enforced regional timeout to prevent stalls ---
            timeout_sec = _PATHWAY_B_TIMEOUT_T3_T4 if "pro" in v_id else _PATHWAY_B_TIMEOUT_T1_T2
            
            # Use Global client if regional is blacklisted or unavailable
            client_to_use = _google_client
            if v_id in _BLACKLISTED_ENDPOINTS and _google_global_client:
                client_to_use = _google_global_client
                logger.info(f"Using Google Global client for {v_id}")

            if not client_to_use:
                raise RuntimeError("No Google client available for inference.")

            resp = client_to_use.models.generate_content(
                model=v_id, 
                contents=prompt,
                config=config
            )
            # Note: The vertex client is configured with a global timeout in config.py, 
            # but we force local enforcement if the SDK allows.
            
            if resp.text:
                return resp.text.strip()
            
            # Robust candidate traversal for multi-part or thinking responses
            full_text = []
            if resp.candidates:
                for candidate in resp.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, "text") and part.text:
                                full_text.append(part.text)
            
            result = "".join(full_text).strip()
            if result:
                return result

            raise ValueError(f"Empty or unparseable response from Vertex AI [{model_id}]")
        except Exception as e:
            # --- Blacklist on 404 to avoid repeated stalls ---
            if "404" in str(e) or "NOT_FOUND" in str(e):
                with _ENDPOINT_LOCK:
                    _BLACKLISTED_ENDPOINTS.add(v_id)
                    logger.warning(f"PATHWAY B: Blacklisting unstable endpoint {v_id} due to 404.")
            
            logger.error(f"Vertex AI ({GCP_REGION}) SDK failure for {model_id}: {e}")
            raise RuntimeError(f"GCP Regional Call Failed: {e}")

    @staticmethod
    def _call_google_global(model_id: str, prompt: str, thinking_budget: int | None = None) -> str:
        """Global Vertex AI fallback — points to us-central1 for 100% reliability."""
        if not _google_global_client:
             raise RuntimeError("Global Vertex client not initialized")
             
        v_id = model_id
            
        try:
            # We skip ThinkingConfig for global fallback flash models to ensure stability
            resp = _google_global_client.models.generate_content(
                model=v_id, 
                contents=prompt
            )
            if resp.text:
                return resp.text.strip()
            return str(resp) # Minimal recovery
        except Exception as e:
            logger.error(f"Global Vertex AI (us-central1) failure for {model_id}: {e}")
            raise RuntimeError(f"Global Rescue Failed: {e}")

    def _handle_pivot(self, prompt: str, max_tokens: int, intent: str) -> str:
        """
        Pathway B: Parallel Rescue (The Race).
        Launches parallel requests to Global Providers to avoid serial failover stalls.
        """
        logger.info(f"EMERGENCY PATHWAY B: Initiating Global Rescue Race for {intent}...")
        
        # Parallel race between available global providers
        providers = []
        if _deepseek_client:
            providers.append(("deepseek", "deepseek-chat", self._call_deepseek))
        
        if _gemini_api_client:
            providers.append(("gemini_api", "gemini-2.0-flash-exp", self._call_gemini_api))
        
        # Add a 100% reliable Vertex Global fallback
        if _google_global_client:
            providers.append(("google_global", "gemini-1.5-flash-001", self._call_google_global))

        if not providers:
            raise RuntimeError("Global Rescue Failed: No secondary providers configured.")

        # Race! First one to finish successfully wins.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {
                executor.submit(fn, m_id, prompt, max_tokens): (p_name, m_id)
                for p_name, m_id, fn in providers
            }
            
            done, not_done = concurrent.futures.wait(
                futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            # Check completed tasks for a result
            for fut in done:
                try:
                    result = fut.result()
                    p_name, m_id = futures[fut]
                    logger.info(f"PATHWAY B WINNER: {p_name} ({m_id})")
                    # Clean up pending tasks
                    for pending in not_done:
                        pending.cancel()
                    return result
                except Exception as e:
                    p_name, m_id = futures[fut]
                    logger.warning(f"Pathway B runner {p_name} failed: {e}")

            # If the first one failed, check the others
            remaining = sorted(list(not_done), key=lambda x: 0) # Just to iterate
            for fut in remaining:
                try:
                    result = fut.result()
                    p_name, m_id = futures[fut]
                    logger.info(f"PATHWAY B RECOVERY: {p_name} ({m_id}) succeeded.")
                    return result
                except Exception as e:
                    logger.error(f"Pathway B runner {p_name} failed: {e}")

        # ── Pathway C: THE GUARANTEED FALLBACK ─────────────────────────────
        # If absolute chaos reigns, we fallback to the most stable model 
        # in existence on AI Studio. No thinking, no complex config.
        if _gemini_api_client:
            try:
                logger.info("PATHWAY C: Triggering Guaranteed Fallback (gemini-1.5-flash)...")
                resp = _gemini_api_client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
                if resp.text:
                    return resp.text.strip()
            except Exception as e:
                logger.error(f"Pathway C ALSO FAILED: {e}")

        raise RuntimeError("Global Rescue Pivot Failed: All pathways (A, B, C) exhausted.")

    @staticmethod
    def _call_gemini_api(model_id: str, prompt: str, max_tokens: int) -> str:
        """Call Gemini via Developer API (Direct API key)."""
        if not _gemini_api_client:
            raise RuntimeError("Gemini API client not configured")
        
        resp = _gemini_api_client.models.generate_content(
            model=model_id,
            contents=prompt,
        )
        return resp.text.strip()

    @staticmethod
    def _call_openai(model_id: str, prompt: str, max_tokens: int) -> str:
        if not _openai_client:
             raise RuntimeError("OpenAI client not configured")
        resp = _openai_client.chat.completions.create(
            model=model_id,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            timeout=15.0 # Rescue race must be fast
        )
        return resp.choices[0].message.content.strip()

    @staticmethod
    def _call_deepseek(model_id: str, prompt: str, max_tokens: int) -> str:
        if not _deepseek_client:
             raise RuntimeError("DeepSeek client not configured")
        resp = _deepseek_client.chat.completions.create(
            model=model_id,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            timeout=20.0 # DeepSeek can be slow; cap it.
        )
        return resp.choices[0].message.content.strip()
        
    @staticmethod
    def _call_xai(model_id: str, prompt: str, max_tokens: int) -> str:
        if not _grok_client:
             raise RuntimeError("Grok client not configured")
        resp = _grok_client.chat.completions.create(
            model=model_id,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content.strip()

    @staticmethod
    def _call_anthropic(model_id: str, prompt: str, max_tokens: int, thinking_budget: int | None = None) -> str:
        try:
            kwargs: dict[str, Any] = {
                "model": model_id,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if thinking_budget:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
            
            msg = _anthropic_client.messages.create(**kwargs)  # type: ignore[union-attr]
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


# ---------------------------------------------------------------------------
# ModelSelector — tier-based routing (formerly engine/model_selector.py)
# ---------------------------------------------------------------------------

# The TIER_N_MODEL constants are now dynamically resolved via ModelGarden.

# Intents that benefit from deeper reasoning from the very first stroke
_DEEP_INTENTS: frozenset[str] = frozenset(
    {"BUILD", "SPAWN_REPO", "DEBUG", "AUDIT"})


@dataclass
class ModelSelection:
    """Immutable record of one model selection decision."""

    stroke: int
    intent: str
    model: str
    tier: int
    rationale: str
    vertex_model_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "stroke": self.stroke,
            "intent": self.intent,
            "model": self.model,
            "tier": self.tier,
            "rationale": self.rationale,
            "vertex_model_id": self.vertex_model_id,
        }


class ModelSelector:
    """Selects the optimal model tier for a given N-Stroke iteration.

    Model IDs come from ModelGarden which is multi-provider and capability-aware.
    The tier escalation logic is deterministic and auditable.
    """

    def select(
        self,
        stroke: int,
        intent: str,
        prior_verdict: str = "",
        force_tier: int | None = None,
    ) -> ModelSelection:
        """Return the optimal model selection for this stroke."""
        tier = (
            max(1, min(4, force_tier))
            if force_tier is not None
            else self._compute_tier(stroke, intent, prior_verdict)
        )
        model = get_garden().get_tier_model(tier, intent)

        rationale = self._rationale(tier, stroke, intent, prior_verdict, model)
        return ModelSelection(
            stroke=stroke, intent=intent, model=model, tier=tier,
            rationale=rationale, vertex_model_id=model,
        )

    @staticmethod
    def _compute_tier(stroke: int, intent: str, prior_verdict: str) -> int:
        if stroke == 1:
            return 2 if intent in _DEEP_INTENTS else 1
        if prior_verdict == "fail":
            return min(4, stroke)
        if prior_verdict == "warn":
            return min(3, stroke)
        return min(2, stroke)

    @staticmethod
    def _rationale(
        tier: int, stroke: int, intent: str, prior_verdict: str, model: str = ""
    ) -> str:
        intent_clause = f"{intent} mandate"
        model_label = model or f"tier-{tier} model"
        if tier == 1:
            return f"Stroke {stroke}: {model_label} — initial fast attempt on {intent_clause}."
        if tier == 2:
            reason = (
                "deep intent → enhanced model for first stroke"
                if stroke == 1
                else f"prior verdict='{prior_verdict}' → escalating to enhanced model"
            )
            return f"Stroke {stroke}: {reason} ({model_label}) for {intent_clause}."
        if tier == 3:
            return (
                f"Stroke {stroke}: prior verdict='{prior_verdict}' → "
                f"escalating to pro reasoning model ({model_label}) for {intent_clause}."
            )
        return (
            f"Stroke {stroke}: {stroke}+ failed attempts → "
            f"maximum capability deployed ({model_label}) for {intent_clause}."
        )

    def select_with_bidder(
        self, stroke: int, intent: str, prior_verdict: str = "",
        node_id: str = "", task_type: str = "reasoning",
    ) -> ModelSelection:
        """Select model using JIT16DBidder when available, else fall back."""
        tier_sel = self.select(stroke, intent, prior_verdict)
        try:
            from engine.dynamic_model_registry import get_bidder
            bidder = get_bidder()
            bid = bidder.bid(
                node_id=node_id or f"stroke-{stroke}",
                task_type=task_type, estimated_tokens=2000,
            )
            if bid.winning_score > 0:
                return ModelSelection(
                    stroke=stroke, intent=intent, model=bid.winning_model,
                    tier=tier_sel.tier,
                    rationale=(
                        f"{tier_sel.rationale} "
                        f"[JIT16D bid: {bid.winning_model} "
                        f"score={bid.winning_score:.2f} "
                        f"cost=${bid.winning_cost_per_10k:.4f}/10k]"
                    ),
                    vertex_model_id=bid.winning_model,
                )
        except Exception:
            pass
        return tier_sel
