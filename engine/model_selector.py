"""
engine/model_selector.py — Dynamic model selection for N-Stroke pipeline.

Maps mandate context (stroke number, intent, prior verdict) to the optimal
model tier without making any LLM calls.  Selection is fully deterministic
so the escalation ladder is auditable and testable offline.

Tiers and their primary use cases:
  TIER_1 (Flash):          Default — stroke 1 for most intents
  TIER_2 (Flash-Exp):      Complex intents on stroke 1; tier escalation on warn
  TIER_3 (Pro):            Failed strokes or deep-reasoning intents
  TIER_4 (Pro-Thinking):   4+ failed strokes — maximum capability deployed

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

# ── Model name constants ──────────────────────────────────────────────────────

TIER_1_MODEL = "gemini-2.5-flash"
TIER_2_MODEL = "gemini-2.5-flash-exp"
TIER_3_MODEL = "gemini-2.5-pro"
TIER_4_MODEL = "gemini-2.5-pro-thinking"

_TIER_MODELS: dict[int, str] = {
    1: TIER_1_MODEL,
    2: TIER_2_MODEL,
    3: TIER_3_MODEL,
    4: TIER_4_MODEL,
}

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "stroke": self.stroke,
            "intent": self.intent,
            "model": self.model,
            "tier": self.tier,
            "rationale": self.rationale,
        }


# ── Selector ──────────────────────────────────────────────────────────────────


class ModelSelector:
    """Selects the optimal model tier for a given N-stroke iteration.

    The selector escalates the model tier on each failed stroke so TooLoo
    always applies its strongest available reasoning capability when previous
    attempts have not satisfied the mandate.

    Usage::

        selector = ModelSelector()
        sel = selector.select(stroke=1, intent="BUILD", prior_verdict="")
        # sel.model → "gemini-2.5-flash"   sel.tier → 1

        sel2 = selector.select(stroke=3, intent="BUILD", prior_verdict="fail")
        # sel2.model → "gemini-2.5-pro"    sel2.tier → 3
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
            prior_verdict:  RefinementLoop verdict from the previous stroke
                            (``"pass"`` | ``"warn"`` | ``"fail"`` | ``""``).
            force_tier:     Override tier for testing purposes (1–4).
        """
        tier = (
            max(1, min(4, force_tier))
            if force_tier is not None
            else self._compute_tier(stroke, intent, prior_verdict)
        )
        model = _TIER_MODELS[tier]
        rationale = self._rationale(tier, stroke, intent, prior_verdict)
        return ModelSelection(
            stroke=stroke, intent=intent, model=model, tier=tier, rationale=rationale
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
    def _rationale(tier: int, stroke: int, intent: str, prior_verdict: str) -> str:
        intent_clause = f"{intent} mandate"
        if tier == 1:
            return (
                f"Stroke {stroke}: {TIER_1_MODEL} — initial attempt on {intent_clause}."
            )
        if tier == 2:
            reason = (
                "deep intent requires enhanced Flash"
                if stroke == 1
                else f"prior verdict='{prior_verdict}' → escalating to Flash-Exp"
            )
            return f"Stroke {stroke}: {reason} for {intent_clause}."
        if tier == 3:
            return (
                f"Stroke {stroke}: prior verdict='{prior_verdict}' → "
                f"escalating to Pro reasoning model for {intent_clause}."
            )
        return (
            f"Stroke {stroke}: {stroke}+ failed attempts → "
            f"maximum Pro-Thinking capability deployed for {intent_clause}."
        )
