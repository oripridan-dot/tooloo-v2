# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.stance.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/stance.py — The Cognitive Stance Engine (The Empathetic Core).

Detects the user's current working mode (Stance) from their mandate text,
intent history, and workspace context, then exposes per-stance dimension
weight tables that the Validator16D uses to dynamically reweight its
composite score.

Stances
-------
IDEATION        Exploring concepts, brainstorming, high-level architecture.
                Relax safety/syntax strictness; heavily weight conceptual
                alignment and mental models.
DEEP_EXECUTION  Writing production code, aggressive refactoring.
                Maximum security, robustness, and performance gates (0.99).
SURGICAL_REPAIR Debugging and fixing isolated regressions.
                Prioritise accuracy and reversibility; keep flow terse.
MAINTENANCE     Writing tests, documentation, housekeeping.
                Weight quality and honesty; relax performance urgency.

Stance Weights
--------------
Each stance maps every Validator16D dimension name to a multiplier in
[0.5, 1.5].  The Validator applies these before normalising so the composite
reflects stance priorities without breaking the 0–1 score contract.

Session State
-------------
``set_active_stance()`` / ``get_active_stance()`` maintain a per-process
stance that persists across requests until explicitly overridden.  The
``CognitiveStanceEngine.detect()`` call updates this state automatically.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enum ──────────────────────────────────────────────────────────────────────

class Stance(str, Enum):
    IDEATION = "IDEATION"
    DEEP_EXECUTION = "DEEP_EXECUTION"
    SURGICAL_REPAIR = "SURGICAL_REPAIR"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN = "UNKNOWN"


# ── Per-Stance 16D Weight Tables ──────────────────────────────────────────────
# Multipliers applied to each dimension's raw score before composite calculation.
# Values > 1.0 increase a dimension's influence; < 1.0 diminish it.
# All keys must match Validator16D._THRESHOLDS exactly.

_STANCE_WEIGHTS: dict[Stance, dict[str, float]] = {
    Stance.IDEATION: {
        # Relax implementation-level gates — ideas are exploratory
        "ROI":                 1.2,   # high-value ideation
        "Safety":              0.8,   # not production code yet
        "Security":            0.8,   # same
        "Legal":               1.0,
        "Human Considering":   1.4,   # empathy + creativity are paramount
        "Accuracy":            0.9,   # rough sketches OK
        "Efficiency":          0.7,   # premature optimisation is the enemy
        "Quality":             0.8,   # messy first drafts are fine
        "Speed":               0.7,   # latency irrelevant for ideation
        "Monitor":             0.9,
        "Control":             1.0,
        "Honesty":             1.2,   # surface assumptions clearly
        "Resilience":          0.8,
        "Financial Awareness": 1.1,
        "Convergence":         1.5,   # architectural cohesion matters most
        "Reversibility":       1.2,   # easy to undo exploratory changes
    },
    Stance.DEEP_EXECUTION: {
        # Maximum rigour — this is going to production
        "ROI":                 1.0,
        "Safety":              1.5,
        "Security":            1.5,   # 0.99 gate enforced
        "Legal":               1.2,
        "Human Considering":   1.0,
        "Accuracy":            1.5,
        "Efficiency":          1.4,   # performance counts
        "Quality":             1.4,
        "Speed":               1.3,
        "Monitor":             1.3,
        "Control":             1.4,
        "Honesty":             1.2,
        "Resilience":          1.4,
        "Financial Awareness": 1.0,
        "Convergence":         1.2,
        "Reversibility":       1.4,
    },
    Stance.SURGICAL_REPAIR: {
        # Laser-focus on pinpointing and reverting the specific break
        "ROI":                 0.9,
        "Safety":              1.1,
        "Security":            1.2,
        "Legal":               1.0,
        "Human Considering":   0.9,   # terse output preferred
        "Accuracy":            1.5,   # must be correct
        "Efficiency":          1.1,
        "Quality":             1.0,
        "Speed":               1.1,
        "Monitor":             1.3,   # observability helps diagnosis
        "Control":             1.3,
        "Honesty":             1.4,   # surface root cause clearly
        "Resilience":          1.2,
        "Financial Awareness": 0.8,
        "Convergence":         1.0,
        "Reversibility":       1.5,   # must be undoable
    },
    Stance.MAINTENANCE: {
        # Tests, docs, housekeeping — quality and coverage are the goal
        "ROI":                 0.9,
        "Safety":              1.1,
        "Security":            1.1,
        "Legal":               1.1,
        "Human Considering":   1.2,
        "Accuracy":            1.2,
        "Efficiency":          1.0,
        "Quality":             1.5,   # clean, well-documented code
        "Speed":               0.8,
        "Monitor":             1.2,
        "Control":             1.1,
        "Honesty":             1.4,   # tests must be truthful
        "Resilience":          1.2,
        "Financial Awareness": 0.9,
        "Convergence":         1.1,
        "Reversibility":       1.2,
    },
    Stance.UNKNOWN: {dim: 1.0 for dim in [
        "ROI", "Safety", "Security", "Legal", "Human Considering",
        "Accuracy", "Efficiency", "Quality", "Speed", "Monitor", "Control",
        "Honesty", "Resilience", "Financial Awareness", "Convergence",
        "Reversibility",
    ]},
}


# ── Buddy Persona Directives per Stance ───────────────────────────────────────

_STANCE_BUDDY_PERSONA: dict[Stance, str] = {
    Stance.IDEATION: (
        "STANCE: IDEATION MODE — The user is exploring, brainstorming, or architecting. "
        "Be highly conversational and expansive. Ask probing questions that stretch their "
        "thinking further. Present multiple architectural options. Use diagrams and visuals "
        "liberally. Encourage divergent thinking — 'What if we…' and 'Have you considered…' "
        "are welcome. Allow rough, incomplete ideas without immediately critiquing syntax."
    ),
    Stance.DEEP_EXECUTION: (
        "STANCE: DEEP EXECUTION MODE — The user is writing or refactoring production code. "
        "Be precise, structured, and surgical. Provide complete, production-ready code. "
        "Call out every security risk, edge case, and performance concern. Do not pad "
        "with commentary — lead with the implementation. Enforce correctness above all."
    ),
    Stance.SURGICAL_REPAIR: (
        "STANCE: SURGICAL REPAIR MODE — The user is debugging a specific, isolated issue. "
        "Be terse and analytical. Output the root cause first, then the minimal fix. "
        "Skip conversational framing entirely. Use numbered lists for diagnosis steps. "
        "Every word counts — get out of the way and provide the raw solution immediately."
    ),
    Stance.MAINTENANCE: (
        "STANCE: MAINTENANCE MODE — The user is writing tests, documentation, or cleaning up. "
        "Be methodical and thorough. Favour completeness over brevity. Suggest edge-case "
        "test scenarios proactively. Surface any documentation gaps spotted in adjacent "
        "code. Celebrate improvements to coverage and code clarity."
    ),
    Stance.UNKNOWN: "",
}


# ── Detection Keywords ────────────────────────────────────────────────────────

_IDEATION_SIGNALS = re.compile(
    r"\b(brainstorm|architect|design|sketch|explore|ideate|concept|idea|"
    r"what\s+if|how\s+would|invent|vision|roadmap|strategy|overview|"
    r"white.?board|rfc|proposal)\b",
    re.IGNORECASE,
)
_DEEP_EXEC_SIGNALS = re.compile(
    r"\b(implement|build|code|create|write|refactor|rewrite|migrate|"
    r"production|deploy|ship|release|feature|sprint|pr|pull.?request|"
    r"performance|optimis|optimi[zs])\b",
    re.IGNORECASE,
)
_SURGICAL_SIGNALS = re.compile(
    r"\b(debug|fix|bug|error|exception|traceback|crash|fail|broken|"
    r"regression|issue|problem|wrong|incorrect|doesn.?t.work|not.work|"
    r"why\s+is|why\s+does|investigate|diagnose|root.cause|patch)\b",
    re.IGNORECASE,
)
_MAINTENANCE_SIGNALS = re.compile(
    r"\b(test|spec|coverage|document|docs|readme|changelog|lint|type.?check|"
    r"clean\s*up|housekeep|deprecat|comment|annotate|format|prettier|isort|"
    r"mypy|pyright|ruff|ci|pipeline)\b",
    re.IGNORECASE,
)

_INTENT_TO_STANCE: dict[str, Stance] = {
    "BUILD":       Stance.DEEP_EXECUTION,
    "DEBUG":       Stance.SURGICAL_REPAIR,
    "AUDIT":       Stance.MAINTENANCE,
    "DESIGN":      Stance.IDEATION,
    "EXPLAIN":     Stance.IDEATION,
    "IDEATE":      Stance.IDEATION,
    "SPAWN_REPO":  Stance.DEEP_EXECUTION,
    "CASUAL":      Stance.UNKNOWN,
    "SUPPORT":     Stance.UNKNOWN,
    "DISCUSS":     Stance.IDEATION,
    "COACH":       Stance.IDEATION,
    "PRACTICE":    Stance.MAINTENANCE,
}


# ── DTO ───────────────────────────────────────────────────────────────────────

@dataclass
class StanceResult:
    """Output of CognitiveStanceEngine.detect()."""

    stance: Stance
    confidence: float                         # 0.0–1.0
    explanation: str
    dimension_weights: dict[str, float] = field(default_factory=dict)
    buddy_persona: str = ""
    signals_matched: list[str] = field(default_factory=list)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stance": self.stance.value,
            "confidence": round(self.confidence, 3),
            "explanation": self.explanation,
            "buddy_persona": self.buddy_persona,
            "signals_matched": self.signals_matched,
            "dimension_weights": {k: round(v, 3) for k, v in self.dimension_weights.items()},
            "ts": self.ts,
        }


# ── Engine ────────────────────────────────────────────────────────────────────

class CognitiveStanceEngine:
    """
    Detects the user's Cognitive Stance from mandate text and intent history.

    Detection is fast (pure regex + intent heuristics) — no LLM call needed.
    The result is stored in the process-level singleton so every downstream
    component can query the active stance without re-detection.
    """

    def detect(
        self,
        mandate_text: str,
        recent_intents: list[str] | None = None,
        workspace_context: str = "",
    ) -> StanceResult:
        """Detect the user's current Cognitive Stance.

        Args:
            mandate_text:     The raw mandate / chat text.
            recent_intents:   Last N router intents from the session history.
            workspace_context: Optional CognitiveMap relevant_context() blob.

        Returns:
            StanceResult with stance, confidence, weights, and persona directive.
        """
        text = (mandate_text or "").strip()
        combined = text + " " + (workspace_context or "")

        scores: dict[Stance, float] = {
            s: 0.0 for s in Stance if s != Stance.UNKNOWN}

        # Keyword scoring
        matched: list[str] = []
        for pat, stance, weight in [
            (_IDEATION_SIGNALS,   Stance.IDEATION,        1.0),
            (_DEEP_EXEC_SIGNALS,  Stance.DEEP_EXECUTION,  1.0),
            (_SURGICAL_SIGNALS,   Stance.SURGICAL_REPAIR, 1.2),  # debug > build
            (_MAINTENANCE_SIGNALS, Stance.MAINTENANCE,    1.0),
        ]:
            hits = pat.findall(combined)
            if hits:
                matched.extend([h.lower() for h in hits[:3]])
                scores[stance] += len(hits) * weight

        # Intent history bias (recent intents carry 0.5 weight each)
        for intent in (recent_intents or [])[-5:]:
            mapped = _INTENT_TO_STANCE.get(intent.upper())
            if mapped and mapped != Stance.UNKNOWN:
                scores[mapped] = scores.get(mapped, 0.0) + 0.5

        best = max(scores, key=lambda s: scores[s])
        best_score = scores[best]

        if best_score == 0.0:
            # No signals — fall back to intent-based heuristic only
            last_intent = (recent_intents or ["BUILD"])[-1].upper()
            best = _INTENT_TO_STANCE.get(last_intent, Stance.UNKNOWN)
            confidence = 0.4
        else:
            total = sum(scores.values()) or 1.0
            confidence = min(0.98, best_score / total + 0.15)

        weights = _STANCE_WEIGHTS[best]
        persona = _STANCE_BUDDY_PERSONA[best]

        explanation = (
            f"Detected {best.value} from {len(matched)} keyword signal(s)"
            + (f": {', '.join(matched[:5])}" if matched else " (intent history)")
        )

        result = StanceResult(
            stance=best,
            confidence=confidence,
            explanation=explanation,
            dimension_weights=weights,
            buddy_persona=persona,
            signals_matched=matched[:10],
        )

        # Update process-level singleton
        set_active_stance(result)
        return result

    def weights_for(self, stance: Stance | str) -> dict[str, float]:
        """Return dimension weights for a given stance without detection."""
        if isinstance(stance, str):
            try:
                stance = Stance(stance.upper())
            except ValueError:
                stance = Stance.UNKNOWN
        return dict(_STANCE_WEIGHTS.get(stance, _STANCE_WEIGHTS[Stance.UNKNOWN]))

    def persona_for(self, stance: Stance | str) -> str:
        """Return the Buddy persona directive for a given stance."""
        if isinstance(stance, str):
            try:
                stance = Stance(stance.upper())
            except ValueError:
                stance = Stance.UNKNOWN
        return _STANCE_BUDDY_PERSONA.get(stance, "")


# ── Process-Level Active Stance ───────────────────────────────────────────────

_active_stance_lock = threading.Lock()
_active_stance: StanceResult | None = None

_default_stance = StanceResult(
    stance=Stance.UNKNOWN,
    confidence=0.0,
    explanation="No stance detected yet.",
    dimension_weights=_STANCE_WEIGHTS[Stance.UNKNOWN],
    buddy_persona="",
)


def get_active_stance() -> StanceResult:
    """Return the currently active stance (process-level singleton)."""
    with _active_stance_lock:
        return _active_stance if _active_stance is not None else _default_stance


def set_active_stance(result: StanceResult) -> None:
    """Override the active stance (e.g., from a manual API call)."""
    global _active_stance
    with _active_stance_lock:
        _active_stance = result


# ── Module-level singleton ────────────────────────────────────────────────────

_engine_instance: CognitiveStanceEngine | None = None
_engine_lock = threading.Lock()


def get_stance_engine() -> CognitiveStanceEngine:
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                _engine_instance = CognitiveStanceEngine()
    return _engine_instance
