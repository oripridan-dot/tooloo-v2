"""
engine/model_selector.py — Dynamic model selection for N-Stroke pipeline.

Maps mandate context (stroke number, intent, prior verdict) to the optimal
model tier, then resolves the actual model ID from the ModelGarden registry.

No model names are hardcoded here — all IDs come from
engine/model_garden.get_tier_models_static() which reads the capability
registry and computes the best model per tier at import time.

Tiers and their primary use cases:
  TIER_1 — fastest flash / lite model       (stroke 1, most intents)
  TIER_2 — best code-capable flash model    (deep intents, stroke 1; warn escalation)
  TIER_3 — best stable pro/reasoning model  (fail escalation; may be Claude)
  TIER_4 — absolute max capability          (3+ failures; cross-provider consensus)

Escalation rule (deterministic):
  stroke 1, intent in DEEP_INTENTS          → tier 2
  stroke 1, default                         → tier 1
  stroke N (N > 1), prior verdict = "fail"  → min(N, 4)
  stroke N (N > 1), prior verdict = "warn"  → min(N, 3)
  stroke N (N > 1), prior verdict = "pass"  → min(2, N)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.model_garden import get_tier_models_static

# ── Compute tier → model map once at import time ──────────────────────────────
# get_tier_models_static() uses only the static registry (no network, no API),
# so it is fast, deterministic, and safe for module-level evaluation.
# T1 = gemini-2.5-flash-lite  (fastest GA flash)
# T2 = gemini-2.5-flash       (second fastest GA flash)
# T3 = gemini-2.5-pro         (best stable pro, GA)   — or Claude if configured
# T4 = gemini-3.1-pro-preview (strongest reasoning)   — or next-best provider

_STATIC_TIERS: dict[int, str] = get_tier_models_static()

TIER_1_MODEL: str = _STATIC_TIERS[1]
TIER_2_MODEL: str = _STATIC_TIERS[2]
TIER_3_MODEL: str = _STATIC_TIERS[3]
TIER_4_MODEL: str = _STATIC_TIERS[4]

# Mirrors for internal use (mutable at runtime via garden)
_TIER_MODELS: dict[int, str] = dict(_STATIC_TIERS)
VERTEX_TIER_MAP: dict[int, str] = dict(_STATIC_TIERS)

# Intents that benefit from deeper reasoning from the very first stroke
_DEEP_INTENTS: frozenset[str] = frozenset({"SPAWN_REPO", "DEBUG", "AUDIT"})


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class ModelSelection:
    """Immutable record of one model selection decision."""

    stroke: int
    intent: str
    model: str
    tier: int
    rationale: str
    # Vertex AI / provider model identifier (same as model)
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


# ── Selector ──────────────────────────────────────────────────────────────────


class ModelSelector:
    """
    Selects the optimal model tier for a given N-Stroke iteration.

    Model IDs come from ModelGarden which is multi-provider and capability-aware.
    The tier escalation logic is deterministic and auditable.

    Usage::

        selector = ModelSelector()
        sel = selector.select(stroke=1, intent="BUILD", prior_verdict="")
        # sel.model → "gemini-2.5-flash-lite"   sel.tier → 1

        sel2 = selector.select(stroke=3, intent="BUILD", prior_verdict="fail")
        # sel2.model → "gemini-2.5-pro"          sel2.tier → 3
    """

    def select(
        self,
        stroke: int,
        intent: str,
        prior_verdict: str = "",
        force_tier: int | None = None,
    ) -> ModelSelection:
        """Return the optimal model selection for this stroke.

        Args:
            stroke:         Current stroke number (1-indexed).
            intent:         Routed intent string (BUILD / DEBUG / etc.).
            prior_verdict:  RefinementLoop verdict from previous stroke
                            (``"pass"`` | ``"warn"`` | ``"fail"`` | ``""``).
            force_tier:     Override tier for testing purposes (1–4).
        """
        tier = (
            max(1, min(4, force_tier))
            if force_tier is not None
            else self._compute_tier(stroke, intent, prior_verdict)
        )

        # Use the pre-computed static tier map for deterministic, test-safe selection.
        # The ModelGarden handles provider dispatch at *inference* time (jit_booster,
        # conversation) — tier assignment stays Google-only and predictable.
        model = _TIER_MODELS[tier]

        rationale = self._rationale(tier, stroke, intent, prior_verdict, model)
        return ModelSelection(
            stroke=stroke,
            intent=intent,
            model=model,
            tier=tier,
            rationale=rationale,
            vertex_model_id=model,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _compute_tier(stroke: int, intent: str, prior_verdict: str) -> int:
        """Deterministically compute the model tier."""
        if stroke == 1:
            return 2 if intent in _DEEP_INTENTS else 1

        # Subsequent strokes — escalate based on prior outcome
        if prior_verdict == "fail":
            return min(4, stroke)
        if prior_verdict == "warn":
            return min(3, stroke)
        # pass (or unknown) — stay low but allow slight escalation on long runs
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
