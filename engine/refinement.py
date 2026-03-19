"""
engine/refinement.py — Post-execution evaluate-and-refine loop.

Runs after every fan_out() call to:
  - Measure success rate and latency distribution (avg, p90)
  - Detect slow nodes (above SLOW_THRESHOLD_MS)
  - Classify failed nodes and surface root-cause hints
  - Produce actionable recommendations
  - Advise whether a partial re-run is warranted

This closes the action loop: scope → execute → refine → (re-run if needed).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.executor import ExecutionResult


@dataclass
class RefinementReport:
    """Immutable evaluation produced after a completed fan_out() wave."""

    total: int
    succeeded: int
    failed: int
    success_rate: float          # 0.0 – 1.0
    avg_latency_ms: float
    p50_latency_ms: float        # median latency
    p90_latency_ms: float
    slow_nodes: list[str]        # mandate_ids above SLOW_THRESHOLD_MS
    failed_nodes: list[str]      # mandate_ids that raised exceptions
    recommendations: list[str]  # actionable next steps
    rerun_advised: bool          # True when partial re-run would likely help
    verdict: str                 # "pass" | "warn" | "fail"
    iterations: int = 1          # how many refinement passes were run

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p90_latency_ms": round(self.p90_latency_ms, 2),
            "slow_nodes": self.slow_nodes,
            "failed_nodes": self.failed_nodes,
            "recommendations": self.recommendations,
            "rerun_advised": self.rerun_advised,
            "verdict": self.verdict,
            "iterations": self.iterations,
        }


class RefinementLoop:
    """Evaluate a completed execution and produce a refinement report.

    Usage::

        loop = RefinementLoop()
        report = loop.evaluate(exec_results)
        if report.rerun_advised:
            # retry failed envelopes only
    """

    # DEV MODE: raised 500→2000ms; nodes are slow locally
    SLOW_THRESHOLD_MS: float = 2000.0

    # DEV MODE: thresholds widened for dev flow — warn 0.70→0.45, fail 0.50→0.25
    _WARN_THRESHOLD: float = 0.45
    _FAIL_THRESHOLD: float = 0.25

    def __init__(
        self,
        slow_threshold_ms: float | None = None,
        warn_threshold: float | None = None,
        fail_threshold: float | None = None,
    ) -> None:
        """Allow per-context threshold overrides (e.g. higher slow_threshold for LLM nodes)."""
        if slow_threshold_ms is not None:
            self.SLOW_THRESHOLD_MS = slow_threshold_ms
        if warn_threshold is not None:
            self._WARN_THRESHOLD = warn_threshold
        if fail_threshold is not None:
            self._FAIL_THRESHOLD = fail_threshold

    def evaluate(
        self,
        results: list[ExecutionResult],
        iteration: int = 1,
        warn_threshold: float | None = None,
        fail_threshold: float | None = None,
    ) -> RefinementReport:
        """Analyse results and return a RefinementReport."""
        if not results:
            return RefinementReport(
                total=0, succeeded=0, failed=0,
                success_rate=1.0, avg_latency_ms=0.0, p50_latency_ms=0.0, p90_latency_ms=0.0,
                slow_nodes=[], failed_nodes=[],
                recommendations=["No nodes executed — nothing to refine."],
                rerun_advised=False, verdict="pass", iterations=iteration,
            )

        # Allow dynamic threshold overrides for adaptive refinement
        warn_thr = warn_threshold if warn_threshold is not None else self._WARN_THRESHOLD
        fail_thr = fail_threshold if fail_threshold is not None else self._FAIL_THRESHOLD

        total = len(results)
        succeeded = sum(1 for r in results if r.success)
        failed = total - succeeded
        success_rate = succeeded / total

        latencies = sorted(r.latency_ms for r in results)
        avg_latency_ms = sum(latencies) / total
        p50_idx = max(0, int(total * 0.5) - 1)
        p50_latency_ms = latencies[p50_idx]
        p90_idx = max(0, int(total * 0.9) - 1)
        p90_latency_ms = latencies[p90_idx]

        slow_nodes = [
            r.mandate_id for r in results if r.latency_ms >= self.SLOW_THRESHOLD_MS
        ]
        failed_nodes = [r.mandate_id for r in results if not r.success]

        recommendations: list[str] = []

        if failed_nodes:
            errs = [r.error or "unknown" for r in results if not r.success]
            unique_errs = list(dict.fromkeys(errs))[:3]
            recommendations.append(
                f"Re-examine {failed} failed node(s) [{', '.join(failed_nodes)}]. "
                f"Root causes: {'; '.join(unique_errs)}"
            )

        if slow_nodes:
            recommendations.append(
                f"Profile slow node(s) (>{self.SLOW_THRESHOLD_MS:.0f}ms): "
                f"{', '.join(slow_nodes)}"
            )

        if success_rate < fail_thr:
            recommendations.append(
                f"Success rate below {fail_thr:.0%} — consider reducing wave width, "
                "adding retry logic, or splitting large nodes."
            )
        elif success_rate < warn_thr:
            recommendations.append(
                f"Success rate below {warn_thr:.0%} — partial re-run of failed nodes recommended."
            )

        if success_rate == 1.0 and not slow_nodes:
            recommendations.append(
                "All nodes passed within latency budget — execution optimal."
            )

        # Rerun is worth attempting when there are failures but not total collapse
        rerun_advised = 0 < failed < total and success_rate >= fail_thr

        if success_rate == 1.0:
            verdict = "pass"
        elif success_rate >= warn_thr:
            verdict = "warn"
        else:
            verdict = "fail"

        return RefinementReport(
            total=total,
            succeeded=succeeded,
            failed=failed,
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            p50_latency_ms=p50_latency_ms,
            p90_latency_ms=p90_latency_ms,
            slow_nodes=slow_nodes,
            failed_nodes=failed_nodes,
            recommendations=recommendations,
            rerun_advised=rerun_advised,
            verdict=verdict,
            iterations=iteration,
        )
