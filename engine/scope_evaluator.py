"""
engine/scope_evaluator.py — Pre-execution action scope evaluation.

Analyses the full wave plan BEFORE execution begins:
  - Node count, wave count, dependency depth
  - Maximum parallelism (widest wave)
  - Optimal thread allocation
  - Execution strategy recommendation (serial / parallel / deep-parallel)
  - Estimated risk surface (nodes likely to hit tribunal)

This runs as the first step of every mandate execution cycle so the
executor can allocate resources optimally rather than reactively.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScopeEvaluation:
    """Immutable snapshot produced by ScopeEvaluator.evaluate()."""

    node_count: int
    wave_count: int
    max_wave_width: int         # max parallelism at any single wave
    critical_path_length: int   # number of serial stages (= wave_count)
    # max_wave_width / node_count  (1.0 = fully parallel)
    parallelism_ratio: float
    recommended_workers: int    # threads to allocate for this plan
    strategy: str               # "serial" | "parallel" | "deep-parallel"
    risk_surface: int           # estimated nodes likely to need tribunal healing
    scope_summary: str          # human-readable one-liner

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "wave_count": self.wave_count,
            "max_wave_width": self.max_wave_width,
            "critical_path_length": self.critical_path_length,
            "parallelism_ratio": round(self.parallelism_ratio, 2),
            "recommended_workers": self.recommended_workers,
            "strategy": self.strategy,
            "risk_surface": self.risk_surface,
            "scope_summary": self.scope_summary,
        }


class ScopeEvaluator:
    """Analyse the full wave plan before execution starts.

    Usage::

        evaluator = ScopeEvaluator()
        scope = evaluator.evaluate(waves, intent="BUILD")
        executor.fan_out(work_fn, envelopes, max_workers=scope.recommended_workers)
    """

    # Intents with elevated probability of tribunal intercepts
    _HIGH_RISK_INTENTS: frozenset[str] = frozenset({"BUILD", "DEBUG", "AUDIT"})

    def evaluate(
        self,
        waves: list[list[str]],
        intent: str = "",
    ) -> ScopeEvaluation:
        """Produce a ScopeEvaluation for the given wave plan."""
        node_count = sum(len(w) for w in waves)
        wave_count = len(waves)
        max_wave_width = max((len(w) for w in waves), default=1)
        critical_path_length = wave_count  # serial depth equals the wave count

        parallelism_ratio = max_wave_width / max(node_count, 1)

        # Allocate just enough threads to saturate the widest wave, capped at 8
        recommended_workers = min(max(max_wave_width, 1), 8)

        # Strategy classification
        if wave_count <= 1:
            strategy = "parallel"       # single wave — pure fan-out
        elif max_wave_width >= 3:
            strategy = "deep-parallel"  # wide waves — high concurrency
        else:
            strategy = "serial"         # mostly sequential chain

        # Risk surface: fraction of nodes estimated to hit tribunal in risky intents
        risk_surface = (
            max(1, round(node_count * 0.25))
            if intent.upper() in self._HIGH_RISK_INTENTS
            else 0
        )

        scope_summary = (
            f"{node_count} node{'s' if node_count != 1 else ''} across "
            f"{wave_count} wave{'s' if wave_count != 1 else ''} · "
            f"max ×{max_wave_width} parallel · "
            f"strategy: {strategy} · "
            f"{recommended_workers} thread{'s' if recommended_workers != 1 else ''} allocated"
            + (f" · ~{risk_surface} tribunal candidate{'s' if risk_surface != 1 else ''}" if risk_surface else "")
        )

        return ScopeEvaluation(
            node_count=node_count,
            wave_count=wave_count,
            max_wave_width=max_wave_width,
            critical_path_length=critical_path_length,
            parallelism_ratio=parallelism_ratio,
            recommended_workers=recommended_workers,
            strategy=strategy,
            risk_surface=risk_surface,
            scope_summary=scope_summary,
        )
