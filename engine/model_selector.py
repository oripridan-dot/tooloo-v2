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

from engine.model_garden import get_full_tier_models, get_garden

# ── Compute tier → model map once at import time ──────────────────────────────────────────
# get_full_tier_models() detects ALL active providers (Google + Anthropic +
# Vertex MaaS: Meta Llama, Mistral AI) and returns the optimal 4-tier ladder.
#
# T1 = gemini-2.5-flash-lite   (fastest GA flash — always Google)
# T2 = gemini-2.5-flash        (second fastest GA flash — always Google)
# T3 = claude-3-7-sonnet       (best stable pro when Anthropic active; else Gemini 2.5 Pro)
# T4 = claude-3-5-sonnet       (diversity pick; else next-best Gemini/Llama)

_FULL_TIERS: dict[int, str] = get_full_tier_models()

TIER_1_MODEL: str = _FULL_TIERS[1]
TIER_2_MODEL: str = _FULL_TIERS[2]
TIER_3_MODEL: str = _FULL_TIERS[3]
TIER_4_MODEL: str = _FULL_TIERS[4]

# _TIER_MODELS used for T1/T2 lookup (T3/T4 resolved live per intent via garden).
_TIER_MODELS: dict[int, str] = dict(_FULL_TIERS)
VERTEX_TIER_MAP: dict[int, str] = dict(_FULL_TIERS)

# Intents that benefit from deeper reasoning from the very first stroke
# BUILD added: code generation/implementation mandates require the enhanced flash model
# from the first stroke to produce correct, high-quality implementation output.
_DEEP_INTENTS: frozenset[str] = frozenset(
    {"BUILD", "SPAWN_REPO", "DEBUG", "AUDIT"})


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

        # T1/T2: stable Google flash from the pre-computed map (always deterministic).
        # T3/T4: live multi-provider selection via ModelGarden — intent-aware,
        #        selects the best Anthropic/Vertex MaaS/Google model for the task.
        if tier >= 3:
            model = get_garden().get_tier_model(tier, intent)
        else:
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

    def select_with_bidder(
        self,
        stroke: int,
        intent: str,
        prior_verdict: str = "",
        node_id: str = "",
        task_type: str = "reasoning",
    ) -> ModelSelection:
        """Select model using JIT16DBidder when available, else fall back to tier logic.

        This is a convenience bridge that integrates the DynamicModelRegistry
        bidding into the existing ModelSelector interface.
        """
        # Always fall back to tier-based deterministic selection
        tier_sel = self.select(stroke, intent, prior_verdict)
        try:
            from engine.dynamic_model_registry import get_bidder
            bidder = get_bidder()
            bid = bidder.bid(
                node_id=node_id or f"stroke-{stroke}",
                task_type=task_type,
                estimated_tokens=2000,
            )
            if bid.winning_score > 0:
                return ModelSelection(
                    stroke=stroke,
                    intent=intent,
                    model=bid.winning_model,
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
