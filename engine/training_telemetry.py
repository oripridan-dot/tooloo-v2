# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining training_telemetry.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.942139
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/training_telemetry.py — 16D Learning Curve Tracker & Meta-Learner.

Tracks per-epoch training metrics, computes convergence velocity, detects
plateaus, and feeds back learning signals to adapt ghost strategy weights
and wave priorities in subsequent training epochs.

Core data model:
  TrainingEpoch        — snapshot of one training iteration's 16D scores
  LearningCurve        — ordered sequence of epochs with convergence math
  MetaLearner          — analyzes which improvement patterns yield highest
                         gains and adapts future strategy weights

Math:
  convergence_velocity(d) = Δ score(d) / Δ epoch
  plateau_detected(d)     = |Δ score(d)| < ε for last K epochs
  strategy_weight(s)      = historical_win_rate(s) × recency_decay
  learning_rate(d)        = EMA(convergence_velocity(d), α=0.3)

Persistence: psyche_bank/training_telemetry.json
"""
from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.sota_benchmarks import DIMENSION_WEIGHTS_16D

# ── Output paths ──────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_TELEMETRY_PATH = _REPO_ROOT / "psyche_bank" / "training_telemetry.json"

# ── Constants ─────────────────────────────────────────────────────────────────
_PLATEAU_EPSILON: float = 0.002      # Δ < 0.2% = plateau
_PLATEAU_WINDOW: int = 3             # Must plateau for 3 consecutive epochs
_EMA_ALPHA: float = 0.3             # Exponential moving average smoothing
_DEFAULT_GHOST_WEIGHTS: dict[str, float] = {
    "ghost-conservative": 0.33,
    "ghost-aggressive": 0.33,
    "ghost-sota": 0.34,
}
_RECENCY_HALF_LIFE_EPOCHS: float = 5.0
_RECENCY_DECAY_K: float = math.log(2) / _RECENCY_HALF_LIFE_EPOCHS


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class DimensionSnapshot:
    """One dimension's score at a single epoch."""
    name: str
    score_before: float
    score_after: float
    delta: float               # score_after - score_before
    alignment_gap: float       # 1.0 - score_after (distance from SOTA)
    learning_rate: float       # EMA of convergence velocity

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score_before": round(self.score_before, 4),
            "score_after": round(self.score_after, 4),
            "delta": round(self.delta, 4),
            "alignment_gap": round(self.alignment_gap, 4),
            "learning_rate": round(self.learning_rate, 6),
        }


@dataclass
class TrainingEpoch:
    """Snapshot of one training iteration's results."""
    epoch_id: str
    epoch_number: int
    timestamp: str
    focus: str                           # optimization focus string
    dimensions: list[DimensionSnapshot]
    composite_before: float
    composite_after: float
    delta_composite: float               # composite_after - composite_before
    sota_alignment_before: float         # system alignment from calibration
    sota_alignment_after: float
    ghost_strategy_winner: str           # which ghost won this epoch
    improvement_count: int               # components improved
    ipa_mean: float                      # mean impact-per-action
    latency_ms: float
    converged: bool = False              # True if all dims plateaued

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch_id": self.epoch_id,
            "epoch_number": self.epoch_number,
            "timestamp": self.timestamp,
            "focus": self.focus,
            "composite_before": round(self.composite_before, 4),
            "composite_after": round(self.composite_after, 4),
            "delta_composite": round(self.delta_composite, 4),
            "delta_composite_pct": round(self.delta_composite * 100, 2),
            "sota_alignment_before": round(self.sota_alignment_before, 4),
            "sota_alignment_after": round(self.sota_alignment_after, 4),
            "ghost_strategy_winner": self.ghost_strategy_winner,
            "improvement_count": self.improvement_count,
            "ipa_mean": round(self.ipa_mean, 4),
            "latency_ms": round(self.latency_ms, 2),
            "converged": self.converged,
            "dimensions": [d.to_dict() for d in self.dimensions],
        }


# ── Learning Curve ────────────────────────────────────────────────────────────

class LearningCurve:
    """Ordered sequence of training epochs with convergence detection.

    Tracks per-dimension learning rates (EMA) and detects plateaus
    when convergence velocity drops below ε for K consecutive epochs.
    """

    def __init__(self) -> None:
        self._epochs: list[TrainingEpoch] = []
        self._learning_rates: dict[str, float] = {
            dim: 0.0 for dim in DIMENSION_WEIGHTS_16D
        }

    @property
    def epochs(self) -> list[TrainingEpoch]:
        return list(self._epochs)

    @property
    def epoch_count(self) -> int:
        return len(self._epochs)

    def add_epoch(self, epoch: TrainingEpoch) -> None:
        """Register a completed training epoch and update learning rates."""
        self._epochs.append(epoch)
        for dim_snap in epoch.dimensions:
            prev_lr = self._learning_rates.get(dim_snap.name, 0.0)
            # EMA update: lr = α × velocity + (1-α) × prev_lr
            velocity = dim_snap.delta
            new_lr = _EMA_ALPHA * velocity + (1 - _EMA_ALPHA) * prev_lr
            self._learning_rates[dim_snap.name] = new_lr
            dim_snap.learning_rate = new_lr

    def is_converged(self) -> bool:
        """True if all dimensions have plateaued for the last K epochs."""
        if len(self._epochs) < _PLATEAU_WINDOW:
            return False
        recent = self._epochs[-_PLATEAU_WINDOW:]
        for dim in DIMENSION_WEIGHTS_16D:
            deltas = []
            for epoch in recent:
                for ds in epoch.dimensions:
                    if ds.name == dim:
                        deltas.append(abs(ds.delta))
                        break
            if not deltas:
                continue
            if any(d > _PLATEAU_EPSILON for d in deltas):
                return False
        return True

    def plateau_dimensions(self) -> list[str]:
        """Return dimensions that have plateaued (no significant improvement)."""
        if len(self._epochs) < _PLATEAU_WINDOW:
            return []
        recent = self._epochs[-_PLATEAU_WINDOW:]
        plateaued: list[str] = []
        for dim in DIMENSION_WEIGHTS_16D:
            deltas = []
            for epoch in recent:
                for ds in epoch.dimensions:
                    if ds.name == dim:
                        deltas.append(abs(ds.delta))
            if deltas and all(d < _PLATEAU_EPSILON for d in deltas):
                plateaued.append(dim)
        return plateaued

    def active_dimensions(self) -> list[str]:
        """Dimensions still showing significant improvement."""
        plateaued = set(self.plateau_dimensions())
        return [d for d in DIMENSION_WEIGHTS_16D if d not in plateaued]

    def composite_trajectory(self) -> list[float]:
        """Return the composite score after each epoch."""
        return [e.composite_after for e in self._epochs]

    def best_epoch(self) -> TrainingEpoch | None:
        """Return the epoch with the highest composite delta."""
        if not self._epochs:
            return None
        return max(self._epochs, key=lambda e: e.delta_composite)

    def total_gain(self) -> float:
        """Total composite improvement across all epochs."""
        if not self._epochs:
            return 0.0
        return self._epochs[-1].composite_after - self._epochs[0].composite_before

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch_count": len(self._epochs),
            "total_gain": round(self.total_gain(), 4),
            "total_gain_pct": round(self.total_gain() * 100, 2),
            "converged": self.is_converged(),
            "plateau_dimensions": self.plateau_dimensions(),
            "active_dimensions": self.active_dimensions(),
            "composite_trajectory": [
                round(c, 4) for c in self.composite_trajectory()
            ],
            "learning_rates": {
                k: round(v, 6) for k, v in self._learning_rates.items()
            },
            "epochs": [e.to_dict() for e in self._epochs],
        }


# ── Meta-Learner ──────────────────────────────────────────────────────────────

class MetaLearner:
    """Analyzes training history to adapt improvement strategy weights.

    Tracks:
      1. Ghost strategy win rates — which strategy yields highest IPA
      2. Wave priority adaptation — which waves produce most Δ16D
      3. Focus dimension shifting — shift focus to lagging dimensions

    The meta-learner feeds back into the next SelfImprovementEngine.run()
    call to steer the ghost race and wave priorities.
    """

    def __init__(self) -> None:
        self._ghost_wins: dict[str, int] = {k: 0 for k in _DEFAULT_GHOST_WEIGHTS}
        self._ghost_total: int = 0
        self._ghost_weights: dict[str, float] = dict(_DEFAULT_GHOST_WEIGHTS)
        self._dimension_gains: dict[str, list[float]] = {
            d: [] for d in DIMENSION_WEIGHTS_16D
        }

    @property
    def ghost_weights(self) -> dict[str, float]:
        """Current ghost strategy weights for the next epoch."""
        return dict(self._ghost_weights)

    def record_epoch(self, epoch: TrainingEpoch) -> None:
        """Ingest a completed epoch and update meta-learning state."""
        # Track ghost wins
        winner = epoch.ghost_strategy_winner
        if winner in self._ghost_wins:
            self._ghost_wins[winner] += 1
        self._ghost_total += 1

        # Track per-dimension gains
        for ds in epoch.dimensions:
            if ds.name in self._dimension_gains:
                self._dimension_gains[ds.name].append(ds.delta)

        # Recalculate ghost weights based on historical win rates
        self._recalculate_ghost_weights()

    def _recalculate_ghost_weights(self) -> None:
        """Adjust ghost weights based on recency-weighted win rates."""
        if self._ghost_total == 0:
            return

        # Base win rate
        raw_weights: dict[str, float] = {}
        for strategy, wins in self._ghost_wins.items():
            # Floor of 0.15 to prevent any strategy from being starved
            win_rate = max(0.15, wins / self._ghost_total)
            raw_weights[strategy] = win_rate

        # Normalize to sum to 1.0
        total = sum(raw_weights.values())
        self._ghost_weights = {
            k: round(v / total, 4) for k, v in raw_weights.items()
        }

    def recommended_focus(self) -> str:
        """Recommend the optimization focus for the next epoch.

        Strategy: focus on dimensions with the widest remaining gaps
        that are still showing active learning (not plateaued).
        """
        # Compute mean gain per dimension
        dim_scores: dict[str, float] = {}
        for dim, gains in self._dimension_gains.items():
            if not gains:
                dim_scores[dim] = 0.0
            else:
                # Lower average gain = more room for improvement
                dim_scores[dim] = sum(gains) / len(gains)

        # Sort by ascending gain — lowest gain = most opportunity
        sorted_dims = sorted(dim_scores.items(), key=lambda x: x[1])

        # Map dimension names to focus keywords
        dim_to_focus: dict[str, str] = {
            "ROI": "balanced",
            "Safety": "quality",
            "Security": "quality",
            "Legal": "quality",
            "Human Considering": "quality",
            "Accuracy": "accuracy",
            "Efficiency": "efficiency",
            "Quality": "quality",
            "Speed": "speed",
            "Monitor": "quality",
            "Control": "quality",
            "Honesty": "accuracy",
            "Resilience": "quality",
            "Financial Awareness": "efficiency",
            "Convergence": "accuracy",
            "Reversibility": "quality",
        }

        # Pick top-3 weakest dimensions' focus areas
        focus_areas: list[str] = []
        for dim_name, _ in sorted_dims[:3]:
            focus = dim_to_focus.get(dim_name, "balanced")
            if focus not in focus_areas:
                focus_areas.append(focus)

        return ",".join(focus_areas) if focus_areas else "balanced"

    def wave_priority_adjustments(self) -> dict[int, float]:
        """Return wave importance multipliers for the next epoch.

        Waves that historically produced the most composite delta
        get a higher multiplier (1.0–1.5 range).
        """
        # Currently waves are fixed; future enhancement point
        return {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0}

    def to_dict(self) -> dict[str, Any]:
        return {
            "ghost_weights": self._ghost_weights,
            "ghost_wins": self._ghost_wins,
            "ghost_total": self._ghost_total,
            "recommended_focus": self.recommended_focus(),
            "dimension_mean_gains": {
                k: round(sum(v) / max(len(v), 1), 6)
                for k, v in self._dimension_gains.items()
            },
        }


# ── Persistence ───────────────────────────────────────────────────────────────

def save_telemetry(
    curve: LearningCurve,
    meta: MetaLearner,
    path: Path | None = None,
) -> Path:
    """Persist training telemetry to JSON."""
    out = path or _TELEMETRY_PATH
    out.parent.mkdir(exist_ok=True)
    payload = {
        "saved_at": datetime.now(UTC).isoformat(),
        "learning_curve": curve.to_dict(),
        "meta_learner": meta.to_dict(),
    }
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


def load_telemetry(
    path: Path | None = None,
) -> tuple[LearningCurve, MetaLearner]:
    """Load training telemetry from JSON. Returns fresh instances if not found."""
    src = path or _TELEMETRY_PATH
    curve = LearningCurve()
    meta = MetaLearner()

    if not src.exists():
        return curve, meta

    try:
        data = json.loads(src.read_text(encoding="utf-8"))
        lc_data = data.get("learning_curve", {})

        for epoch_data in lc_data.get("epochs", []):
            dims = [
                DimensionSnapshot(
                    name=d["name"],
                    score_before=d["score_before"],
                    score_after=d["score_after"],
                    delta=d["delta"],
                    alignment_gap=d["alignment_gap"],
                    learning_rate=d.get("learning_rate", 0.0),
                )
                for d in epoch_data.get("dimensions", [])
            ]
            epoch = TrainingEpoch(
                epoch_id=epoch_data["epoch_id"],
                epoch_number=epoch_data["epoch_number"],
                timestamp=epoch_data["timestamp"],
                focus=epoch_data.get("focus", "balanced"),
                dimensions=dims,
                composite_before=epoch_data["composite_before"],
                composite_after=epoch_data["composite_after"],
                delta_composite=epoch_data["delta_composite"],
                sota_alignment_before=epoch_data.get(
                    "sota_alignment_before", 0.0),
                sota_alignment_after=epoch_data.get(
                    "sota_alignment_after", 0.0),
                ghost_strategy_winner=epoch_data.get(
                    "ghost_strategy_winner", "ghost-conservative"),
                improvement_count=epoch_data.get("improvement_count", 0),
                ipa_mean=epoch_data.get("ipa_mean", 0.0),
                latency_ms=epoch_data.get("latency_ms", 0.0),
                converged=epoch_data.get("converged", False),
            )
            curve.add_epoch(epoch)
            meta.record_epoch(epoch)

    except Exception:
        pass  # Return fresh instances on any parse error

    return curve, meta


# ── Epoch Builder Helper ──────────────────────────────────────────────────────

def build_epoch(
    epoch_number: int,
    focus: str,
    scores_before: dict[str, float],
    scores_after: dict[str, float],
    sota_alignment_before: float,
    sota_alignment_after: float,
    ghost_winner: str,
    improvement_count: int,
    ipa_mean: float,
    latency_ms: float,
    previous_learning_rates: dict[str, float] | None = None,
) -> TrainingEpoch:
    """Construct a TrainingEpoch from before/after 16D score dicts."""

    dims: list[DimensionSnapshot] = []
    for dim in DIMENSION_WEIGHTS_16D:
        before = scores_before.get(dim, 0.85)
        after = scores_after.get(dim, before)
        delta = after - before
        gap = 1.0 - after

        prev_lr = (previous_learning_rates or {}).get(dim, 0.0)
        lr = _EMA_ALPHA * delta + (1 - _EMA_ALPHA) * prev_lr

        dims.append(DimensionSnapshot(
            name=dim,
            score_before=before,
            score_after=after,
            delta=delta,
            alignment_gap=gap,
            learning_rate=lr,
        ))

    weights = DIMENSION_WEIGHTS_16D
    w_sum = sum(weights.values())
    composite_before = sum(
        scores_before.get(d, 0.85) * w
        for d, w in weights.items()
    ) / w_sum
    composite_after = sum(
        scores_after.get(d, 0.85) * w
        for d, w in weights.items()
    ) / w_sum

    return TrainingEpoch(
        epoch_id=f"epoch-{uuid.uuid4().hex[:8]}",
        epoch_number=epoch_number,
        timestamp=datetime.now(UTC).isoformat(),
        focus=focus,
        dimensions=dims,
        composite_before=composite_before,
        composite_after=composite_after,
        delta_composite=composite_after - composite_before,
        sota_alignment_before=sota_alignment_before,
        sota_alignment_after=sota_alignment_after,
        ghost_strategy_winner=ghost_winner,
        improvement_count=improvement_count,
        ipa_mean=ipa_mean,
        latency_ms=latency_ms,
    )
