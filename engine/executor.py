# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T20:00:29.746044+00:00
# Component: executor  Source: engine/executor.py
# Improvement signals from JIT SOTA booster:
#  [1] Instrument engine/executor.py: DORA metrics (deploy frequency, lead time,
#     MTTR, CFR) anchor engineering strategy discussions
#  [2] Instrument engine/executor.py: Two-pizza team + async RFC process
#     (Notion/Linear) is the standard ideation workflow
#  [3] Instrument engine/executor.py: Feature flags (OpenFeature standard) decouple
#     deployment from release, enabling hypothesis testing
# ─────────────────────────────────────────────────────────────────
"""
engine/executor.py — JIT fan-out via pure threading.

No imports from tooloo-core. Uses stdlib ThreadPoolExecutor.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from dataclasses import dataclass, field
from typing import Any, Callable

from engine.config import settings


@dataclass
class DoraMetrics:
    """DORA-aligned engineering metrics for TooLoo mandate execution.

    Maps standard DORA four-key metrics to the executor context:
    - ``throughput``      ≈ Deployment Frequency  (mandates completed)
    - ``lead_time_ms``   ≈ Lead Time for Changes  (p50 execution latency)
    - ``change_failure_rate`` ≈ Change Failure Rate (failed_nodes / total_nodes)
    - ``mttr_ms``        ≈ MTTR (mean latency of *failed* nodes, proxy for time
                          until a retry/heal cycle can begin)
    """

    throughput: int
    lead_time_ms: float | None
    change_failure_rate: float
    mttr_ms: float | None

    def to_dict(self) -> dict:
        return {
            "throughput": self.throughput,
            "lead_time_ms": round(self.lead_time_ms, 2) if self.lead_time_ms is not None else None,
            "change_failure_rate": round(self.change_failure_rate, 4),
            "mttr_ms": round(self.mttr_ms, 2) if self.mttr_ms is not None else None,
        }


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

    _MAX_HIST_ENTRIES = 4096

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers or settings.executor_max_workers
        self._latency_histogram: list[float] = []
        self._failed_latencies: list[float] = []  # DORA: MTTR proxy
        self._total_nodes: int = 0                 # DORA: throughput / CFR
        self._failed_nodes: int = 0                # DORA: change_failure_rate
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

        # Preserve input ordering and record latencies + DORA counters
        ordered = [results[e.mandate_id] for e in envelopes]
        self._record_latencies(r.latency_ms for r in ordered)
        self._record_results(ordered)
        return ordered

    def fan_out_dag(
        self,
        work_fn: Callable[[Envelope], Any],
        envelopes: list[Envelope],
        dependencies: dict[str, list[str]],
        max_workers: int | None = None,
    ) -> list[ExecutionResult]:
        """Execute a dependency DAG without waiting on whole-wave barriers.

        Nodes are submitted the moment *their own* dependencies complete,
        eliminating straggler stalls caused by rigid wave-level synchronisation.
        Results are still returned in the same order as ``envelopes``.
        """
        if not envelopes:
            return []

        env_by_id = {env.mandate_id: env for env in envelopes}
        ordered_ids = [env.mandate_id for env in envelopes]
        dep_map = {
            node_id: list(dependencies.get(node_id, []))
            for node_id in ordered_ids
        }

        missing_nodes = {
            dep
            for deps in dep_map.values()
            for dep in deps
            if dep not in env_by_id
        }
        if missing_nodes:
            raise ValueError(
                f"Unknown dependency node(s): {sorted(missing_nodes)}"
            )

        reverse_deps: dict[str, list[str]] = {
            node_id: [] for node_id in ordered_ids}
        for node_id, deps in dep_map.items():
            for dep in deps:
                reverse_deps.setdefault(dep, []).append(node_id)

        effective_workers = min(
            max_workers or self._max_workers, len(envelopes)) or 1
        unresolved = {node_id: len(deps) for node_id, deps in dep_map.items()}
        failed_parents: dict[str, list[str]] = {
            node_id: [] for node_id in ordered_ids}
        results: dict[str, ExecutionResult] = {}
        ready = [node_id for node_id, remaining in unresolved.items()
                 if remaining == 0]
        running: dict[Any, str] = {}

        def _submit_ready(pool: ThreadPoolExecutor) -> None:
            while ready and len(running) < effective_workers:
                node_id = ready.pop(0)
                if node_id in results:
                    continue
                fut = pool.submit(self._run, work_fn, env_by_id[node_id])
                running[fut] = node_id

        def _finalise_child(node_id: str) -> None:
            if node_id in results or unresolved[node_id] != 0:
                return
            if failed_parents[node_id]:
                blocked_by = ", ".join(sorted(failed_parents[node_id]))
                results[node_id] = ExecutionResult(
                    mandate_id=node_id,
                    success=False,
                    output=None,
                    latency_ms=0.0,
                    error=f"Blocked by failed dependency: {blocked_by}",
                )
                for child_id in reverse_deps.get(node_id, []):
                    failed_parents[child_id].append(node_id)
                    unresolved[child_id] = max(0, unresolved[child_id] - 1)
                    _finalise_child(child_id)
            else:
                ready.append(node_id)

        with ThreadPoolExecutor(max_workers=effective_workers) as pool:
            _submit_ready(pool)

            while running:
                done, _ = wait(running.keys(), return_when=FIRST_COMPLETED)
                for fut in done:
                    node_id = running.pop(fut)
                    result = fut.result()
                    results[node_id] = result

                    for child_id in reverse_deps.get(node_id, []):
                        if not result.success:
                            failed_parents[child_id].append(node_id)
                        unresolved[child_id] = max(0, unresolved[child_id] - 1)
                        _finalise_child(child_id)

                _submit_ready(pool)

        ordered = [results[node_id] for node_id in ordered_ids]
        self._record_latencies(r.latency_ms for r in ordered)
        self._record_results(ordered)
        return ordered

    def latency_p50(self) -> float | None:
        """Return the p50 latency in ms across all completed tasks."""
        return self._latency_percentile(0.50)

    def latency_p90(self) -> float | None:
        """Return the p90 latency in ms across all completed tasks, or None if empty."""
        return self._latency_percentile(0.90)

    def latency_p99(self) -> float | None:
        """Return the p99 latency in ms across all completed tasks."""
        return self._latency_percentile(0.99)

    def dora_metrics(self) -> DoraMetrics:
        """Return DORA-aligned engineering metrics computed from execution history."""
        with self._hist_lock:
            total = self._total_nodes
            failed = self._failed_nodes
            cfr = (failed / total) if total > 0 else 0.0
            lead_time = self._latency_percentile_unsafe(
                self._latency_histogram, 0.50)
            mttr = (
                sum(self._failed_latencies) / len(self._failed_latencies)
                if self._failed_latencies
                else None
            )
        return DoraMetrics(
            throughput=total,
            lead_time_ms=lead_time,
            change_failure_rate=cfr,
            mttr_ms=mttr,
        )

    def reset_histogram(self) -> None:
        """Clear the accumulated latency histogram and DORA counters."""
        with self._hist_lock:
            self._latency_histogram.clear()
            self._failed_latencies.clear()
            self._total_nodes = 0
            self._failed_nodes = 0

    def _latency_percentile(self, percentile: float) -> float | None:
        with self._hist_lock:
            if not self._latency_histogram:
                return None
            sorted_hist = sorted(self._latency_histogram)
            idx = max(0, int(len(sorted_hist) * percentile) - 1)
            return sorted_hist[idx]

    def _record_latencies(self, latencies: Any) -> None:
        with self._hist_lock:
            self._latency_histogram.extend(latencies)
            overflow = len(self._latency_histogram) - self._MAX_HIST_ENTRIES
            if overflow > 0:
                del self._latency_histogram[:overflow]

    def _record_results(self, results: list[ExecutionResult]) -> None:
        """Update DORA counters from a completed fan-out batch."""
        with self._hist_lock:
            self._total_nodes += len(results)
            for r in results:
                if not r.success:
                    self._failed_nodes += 1
                    self._failed_latencies.append(r.latency_ms)

    @staticmethod
    def _latency_percentile_unsafe(hist: list[float], percentile: float) -> float | None:
        """Compute percentile from an already-locked histogram list."""
        if not hist:
            return None
        sorted_hist = sorted(hist)
        idx = max(0, int(len(sorted_hist) * percentile) - 1)
        return sorted_hist[idx]

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
