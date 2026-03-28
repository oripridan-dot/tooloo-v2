# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining runtime_metrics.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.934769
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/runtime_metrics.py — Runtime Metrics Collector for 16D Scoring.

Collects REAL runtime signals (latency, cache hits, test pass rate, error
recovery rate) and bridges them into the 16D validator. This replaces the
static code-analysis-only approach that caused all 16 dimensions to plateau
at 0.14 composite with 0.0 learning rate.

The collector maintains a rolling window of measurements per dimension
and exposes them as inputs to ``Validator16D.validate()``.

Used by:
  - SelfImprovementEngine: to get real 16D scores before/after code changes
  - CalibrationEngine: to feed live data instead of static defaults
  - Studio API: to expose runtime health to the dashboard

Architecture note (4D Routing — Macro timeframe):
  This module is the critical link between the Ouroboros self-improvement
  loop and actual system performance. Without it, the 16D scores were
  stuck because the validator was called with code_snippet=None and
  default latency values, producing near-zero scores on 12/16 dimensions.
"""
from __future__ import annotations

import logging
import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class RuntimeSnapshot:
    """A single point-in-time measurement of system health."""
    timestamp: float = 0.0
    # Response latency for recent chat turns (ms)
    response_latencies_ms: list[float] = field(default_factory=list)
    # Cache performance
    cache_hit_rate: float = 0.0
    cache_total_requests: int = 0
    # Test suite
    test_pass_rate: float = 1.0
    test_total: int = 0
    test_passed: int = 0
    # Error recovery
    errors_total: int = 0
    errors_recovered: int = 0
    recovery_rate: float = 1.0
    # Token efficiency
    avg_tokens_per_response: float = 0.0
    # Component-level code quality (from dynamic_scorer)
    avg_code_quality: float = 0.0
    component_count: int = 0


class RuntimeMetricsCollector:
    """Collects and aggregates runtime performance metrics.

    Maintains a rolling window of snapshots. Each snapshot captures
    the system's health at a point in time. When the 16D validator
    needs real data, it calls ``current_snapshot()`` to get the latest
    aggregated measurements.
    """

    _MAX_LATENCIES = 200  # Keep last 200 response latencies

    def __init__(self) -> None:
        self._latencies: deque[float] = deque(maxlen=self._MAX_LATENCIES)
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._errors: int = 0
        self._recoveries: int = 0
        self._test_results: dict[str, bool] = {}  # test_name -> passed

    # ── Recording methods (called by other modules) ──────────────────────

    def record_latency(self, latency_ms: float) -> None:
        """Record a response latency measurement."""
        self._latencies.append(latency_ms)

    def record_cache_hit(self) -> None:
        self._cache_hits += 1

    def record_cache_miss(self) -> None:
        self._cache_misses += 1

    def record_error(self, recovered: bool = False) -> None:
        self._errors += 1
        if recovered:
            self._recoveries += 1

    def record_test_result(self, test_name: str, passed: bool) -> None:
        self._test_results[test_name] = passed

    def bulk_record_tests(self, total: int, passed: int) -> None:
        """Record batch test results (e.g., from pytest run)."""
        self._test_results = {
            f"test_{i}": i < passed for i in range(total)
        }

    # ── Snapshot generation ──────────────────────────────────────────────

    def current_snapshot(self) -> RuntimeSnapshot:
        """Generate a snapshot from all accumulated measurements."""
        latencies = list(self._latencies)
        total_cache = self._cache_hits + self._cache_misses

        # Compute code quality from dynamic_scorer
        avg_quality = 0.0
        component_count = 0
        try:
            from engine.dynamic_scorer import score_all_components
            all_metrics = score_all_components()
            if all_metrics:
                avg_quality = sum(
                    m.composite_quality for m in all_metrics.values()
                ) / len(all_metrics)
                component_count = len(all_metrics)
        except Exception:
            pass

        # Test pass rate
        test_total = len(self._test_results)
        test_passed = sum(1 for v in self._test_results.values() if v)

        return RuntimeSnapshot(
            timestamp=time.time(),
            response_latencies_ms=latencies[-50:],  # Last 50 for the snapshot
            cache_hit_rate=(
                self._cache_hits / total_cache if total_cache > 0 else 0.0
            ),
            cache_total_requests=total_cache,
            test_pass_rate=(
                test_passed / test_total if test_total > 0 else 1.0
            ),
            test_total=test_total,
            test_passed=test_passed,
            errors_total=self._errors,
            errors_recovered=self._recoveries,
            recovery_rate=(
                self._recoveries / self._errors
                if self._errors > 0 else 1.0
            ),
            avg_code_quality=avg_quality,
            component_count=component_count,
        )

    def latency_percentiles(self) -> dict[str, float]:
        """Compute p50 and p90 latency from the rolling window."""
        latencies = sorted(self._latencies)
        if not latencies:
            return {"p50_ms": 500.0, "p90_ms": 1000.0}

        n = len(latencies)
        p50 = latencies[int(n * 0.5)]
        p90 = latencies[int(min(n - 1, n * 0.9))]
        return {"p50_ms": round(p50, 2), "p90_ms": round(p90, 2)}

    # ── 16D Bridge: convert runtime metrics into validator inputs ─────────

    def as_validator_inputs(self) -> dict[str, Any]:
        """Convert runtime metrics into kwargs for Validator16D.validate().

        This is the critical bridge that was missing — it takes real
        runtime measurements and translates them into the parameters
        the 16D validator expects, enabling non-zero score deltas.
        """
        snap = self.current_snapshot()
        percs = self.latency_percentiles()

        # Build a synthetic code snippet from the top-3 engine files
        # so the heuristic validators (Safety, Security, etc.) have
        # real code to analyze instead of None.
        code_sample = self._sample_engine_code()

        return {
            "code_snippet": code_sample,
            "test_pass_rate": snap.test_pass_rate,
            "latency_p50_ms": percs["p50_ms"],
            "latency_p90_ms": percs["p90_ms"],
        }

    def _sample_engine_code(self, max_chars: int = 8000) -> str:
        """Read a representative sample of engine code for validator analysis.

        Samples from core modules that change most frequently to give
        the validator real code patterns to score.
        """
        core_files = [
            "engine/router.py",
            "engine/conversation.py",
            "engine/pipeline.py",
            "engine/self_improvement.py",
            "engine/validator_16d.py",
        ]
        chunks: list[str] = []
        total = 0
        for rel in core_files:
            path = _REPO_ROOT / rel
            if not path.exists():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                # Take first 1600 chars of each to get a representative sample
                chunk = text[:1600]
                chunks.append(f"# --- {rel} ---\n{chunk}")
                total += len(chunk)
                if total >= max_chars:
                    break
            except OSError:
                continue

        return "\n\n".join(chunks) if chunks else ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise for API / dashboard consumption."""
        snap = self.current_snapshot()
        percs = self.latency_percentiles()
        return {
            "latency_p50_ms": percs["p50_ms"],
            "latency_p90_ms": percs["p90_ms"],
            "latency_samples": len(self._latencies),
            "cache_hit_rate": round(snap.cache_hit_rate, 4),
            "cache_total_requests": snap.cache_total_requests,
            "test_pass_rate": round(snap.test_pass_rate, 4),
            "test_total": snap.test_total,
            "error_recovery_rate": round(snap.recovery_rate, 4),
            "errors_total": snap.errors_total,
            "avg_code_quality": round(snap.avg_code_quality, 4),
            "component_count": snap.component_count,
        }


# ── Singleton ────────────────────────────────────────────────────────────────
_collector: RuntimeMetricsCollector | None = None


def get_runtime_metrics() -> RuntimeMetricsCollector:
    """Get the global RuntimeMetricsCollector singleton."""
    global _collector
    if _collector is None:
        _collector = RuntimeMetricsCollector()
    return _collector
