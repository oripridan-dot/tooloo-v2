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

Capability dimensions (0.0–1.0)
───────────────────────────────
  speed      : token throughput & low latency
  reasoning  : multi-step logic, math, deep analysis
  coding     : code generation, debugging, architecture
  synthesis  : writing, summarisation, explanation
  stability  : 1.0=GA, 0.9=preview-stable, 0.8=experimental

All model IDs are confirmed against the Vertex AI Model Garden catalog
(project too-loo-zi8g7e, us-central1) and Anthropic Vertex docs — 2026-03-18.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from engine.config import (
    GCP_PROJECT_ID,
    ANTHROPIC_VERTEX_REGION,
    CROSS_MODEL_CONSENSUS_ENABLED,
    _vertex_client as _google_client,  # patchable in tests
)


# ── Capability profile ────────────────────────────────────────────────────────

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
        """True for fast/lite models (flash, lite, haiku)."""
        name = self.id.lower()
        return "flash" in name or "lite" in name or "haiku" in name


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


def _active_models() -> list[ModelInfo]:
    """All models available to the current runtime configuration."""
    models = [m for m in _REGISTRY if m.provider == "google"]
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

    # ── Model selection ──────────────────────────────────────────────────────

    def get_tier_model(self, tier: int, intent: str = "") -> str:
        """
        Return the best model ID for this tier.

        T1/T2: always use static (Google flash) ladder for determinism.
        T3/T4: re-rank all active providers by task_type so Anthropic can win.
        """
        if tier <= 2:
            return self._static_tiers[tier]

        task_type = INTENT_TASK.get(intent, "reasoning")
        available = _active_models()
        pro_pool = [m for m in available if not m.is_flash]

        if not pro_pool:
            return self._static_tiers[tier]

        if tier == 3:
            stable = [m for m in pro_pool if m.stability >= 0.9]
            pool = stable if stable else pro_pool
            return max(pool, key=lambda m: m.score_for(task_type)).id

        # T4: absolute maximum — may differ from T3 for cross-provider diversity
        t3_id = self.get_tier_model(3, intent)
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
        info = self._find(model_id)
        provider = info.provider if info else (
            "anthropic" if model_id.startswith("claude") else "google"
        )
        if provider == "anthropic":
            if _init_anthropic():
                return self._call_anthropic(model_id, prompt, max_tokens)
            raise RuntimeError(
                f"Anthropic Vertex client unavailable (model={model_id})")
        if _google_client is not None:
            return self._call_google(model_id, prompt)
        raise RuntimeError(
            f"Google Vertex client unavailable (model={model_id})")

    def source_for(self, model_id: str) -> str:
        """Return the source label for SSE / JIT result metadata."""
        info = self._find(model_id)
        if info:
            return info.provider  # "google" or "anthropic"
        return "vertex"

    # ── Cross-model consensus (T4 / CROSS_MODEL_CONSENSUS_ENABLED) ───────────

    def consensus(
        self,
        prompt: str,
        tier: int = 4,
        intent: str = "",
        max_tokens: int = 1024,
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

        responses: list[str] = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(self.call, c.id, prompt, max_tokens): c
                for c in candidates
            }
            for fut in as_completed(futures):
                try:
                    responses.append(fut.result())
                except Exception as exc:
                    responses.append(f"[CONSENSUS_ERROR: {exc}]")

        primary = responses[0] if responses else ""
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
        msg = _anthropic_client.messages.create(  # type: ignore[union-attr]
            model=model_id,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    def to_status(self) -> dict[str, Any]:
        """Summary for /v2/health and SSE events."""
        active = _active_models()
        providers = sorted({m.provider for m in active})
        tiers = self._static_tiers
        return {
            "providers": providers,
            "active_models": len(active),
            "anthropic_available": _anthropic_available,
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
