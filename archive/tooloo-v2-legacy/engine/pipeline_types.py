# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.pipeline_types.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time

# PURE Architecture: Legacy engine types are now Any/built-ins for backward compatibility.
# Individual logic files (model_selector, jit_booster, etc.) have been purged.

@dataclass
class StrokeRecord:
    """ Metadata for a single execution cycle. """
    stroke: int
    model_selection: Any
    preflight_jit: Any
    preflight_tribunal: Any
    plan: list[list[str]]
    scope: Any
    mcp_tools_injected: list[str]
    midflight_jit: Any
    execution_results: list[Any]
    refinement: Any
    healing_report: Any | None
    satisfied: bool
    latency_ms: float
    divergence_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stroke": self.stroke,
            "model_selection": self.model_selection.to_dict() if hasattr(self.model_selection, "to_dict") else self.model_selection,
            "preflight_jit": self.preflight_jit.to_dict() if hasattr(self.preflight_jit, "to_dict") else self.preflight_jit,
            "preflight_tribunal": self.preflight_tribunal.to_dict() if hasattr(self.preflight_tribunal, "to_dict") else self.preflight_tribunal,
            "plan": self.plan,
            "scope": self.scope.to_dict() if hasattr(self.scope, "to_dict") else self.scope,
            "mcp_tools_injected": self.mcp_tools_injected,
            "midflight_jit": self.midflight_jit.to_dict() if hasattr(self.midflight_jit, "to_dict") else self.midflight_jit,
            "execution_results": [r.to_dict() if hasattr(r, "to_dict") else r for r in self.execution_results],
            "refinement": self.refinement.to_dict() if hasattr(self.refinement, "to_dict") else self.refinement,
            "healing_report": self.healing_report,
            "satisfied": self.satisfied,
            "latency_ms": round(float(self.latency_ms), 2),
            "divergence_metrics": self.divergence_metrics,
        }

@dataclass
class NStrokeResult:
    """ Aggregated result for a PURE mandated execution. """
    pipeline_id: str
    locked_intent: Any
    strokes: list[StrokeRecord]
    final_verdict: str
    satisfied: bool
    total_strokes: int
    model_escalations: int
    healing_invocations: int
    latency_ms: float
    crisis: dict[str, Any] | None = None
    execution_mode: str = "pure"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "locked_intent": self.locked_intent.to_dict() if hasattr(self.locked_intent, "to_dict") else self.locked_intent,
            "strokes": [s.to_dict() for s in self.strokes],
            "final_verdict": self.final_verdict,
            "satisfied": self.satisfied,
            "total_strokes": self.total_strokes,
            "model_escalations": self.model_escalations,
            "healing_invocations": self.healing_invocations,
            "latency_ms": round(float(self.latency_ms), 2),
            "crisis": self.crisis,
            "execution_mode": self.execution_mode,
        }
