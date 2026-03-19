"""
engine/executor.py — JIT fan-out via pure threading.

No imports from tooloo-core. Uses stdlib ThreadPoolExecutor.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from engine.config import settings


@dataclass
class Envelope:
    """Minimal context bundle passed to each worker clone."""

    mandate_id: str
    intent: str
    domain: str = "backend"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    mandate_id: str
    success: bool
    output: Any
    latency_ms: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandate_id": self.mandate_id,
            "success": self.success,
            "output": self.output,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
        }


class JITExecutor:
    """Fan-out N envelopes in parallel; collapse to ordered results."""

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers or settings.executor_max_workers
        self._latency_histogram: list[float] = []
        self._hist_lock = threading.Lock()

    def fan_out(
        self,
        work_fn: Callable[[Envelope], Any],
        envelopes: list[Envelope],
        max_workers: int | None = None,
    ) -> list[ExecutionResult]:
        """Execute `work_fn(envelope)` for each envelope in parallel.

        Returns results in the same order as the input envelopes.
        `max_workers` overrides the instance default for this call only
        (used by ScopeEvaluator to allocate the right thread count).
        """
        effective_workers = max_workers or self._max_workers
        results: dict[str, ExecutionResult] = {}
        futures = {}

        with ThreadPoolExecutor(max_workers=min(effective_workers, len(envelopes) or 1)) as pool:
            for env in envelopes:
                fut = pool.submit(self._run, work_fn, env)
                futures[fut] = env.mandate_id

            for fut in as_completed(futures):
                mid = futures[fut]
                result = fut.result()
                results[mid] = result

        # Preserve input ordering and record latencies in histogram
        ordered = [results[e.mandate_id] for e in envelopes]
        with self._hist_lock:
            self._latency_histogram.extend(r.latency_ms for r in ordered)
        return ordered

    def latency_p90(self) -> float | None:
        """Return the p90 latency in ms across all completed tasks, or None if empty."""
        with self._hist_lock:
            if not self._latency_histogram:
                return None
            sorted_hist = sorted(self._latency_histogram)
            idx = max(0, int(len(sorted_hist) * 0.9) - 1)
            return sorted_hist[idx]

    def reset_histogram(self) -> None:
        """Clear the accumulated latency histogram."""
        with self._hist_lock:
            self._latency_histogram.clear()

    @staticmethod
    def _run(
        work_fn: Callable[[Envelope], Any],
        env: Envelope,
    ) -> ExecutionResult:
        t0 = time.monotonic()
        try:
            output = work_fn(env)
            return ExecutionResult(
                mandate_id=env.mandate_id,
                success=True,
                output=output,
                latency_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as exc:  # noqa: BLE001
            return ExecutionResult(
                mandate_id=env.mandate_id,
                success=False,
                output=None,
                latency_ms=(time.monotonic() - t0) * 1000,
                error=str(exc),
            )
