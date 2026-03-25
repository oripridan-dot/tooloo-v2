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
engine/executor.py — JIT fan-out via pure async.

Uses asyncio.TaskGroup for modern Python concurrency.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import asyncio

from engine.config import settings
from prometheus_client import Histogram

logger = logging.getLogger(__name__)

# Control: configurable thresholds for fan-out safety
_MAX_RETRIES = 3          # per-node retry ceiling before circuit-breaker escalation (Thread pool size is configured in settings.py)
_TIMEOUT_THRESHOLD = 30   # seconds — nodes exceeding this trigger remediation

# Prometheus Histogram for mandate execution latency
# FIX 2: Implement asyncio native latency histogram collection.
_MANDATE_EXECUTION_LATENCY_HISTOGRAM = Histogram(
    "jit_executor_mandate_latency_ms", "Latency of individual mandate executions in milliseconds"
)


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
    lead_time_ms: Optional[float]
    change_failure_rate: float
    mttr_ms: Optional[float]

    def to_dict(self) -> dict:
        return {
            "throughput": self.throughput,
            "lead_time_ms": round(self.lead_time_ms, 2) if self.lead_time_ms is not None else None,
            "change_failure_rate": round(self.change_failure_rate, 4),
            "mttr_ms": round(self.mttr_ms, 2) if self.mttr_ms is not None else None,
            "executor_context": settings.executor_context.to_dict() if hasattr(settings, 'executor_context') else {}
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
    error: Optional[str] = None
    node_error: Optional[str] = None  # Added for node-specific error reporting
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        res = {
            "mandate_id": self.mandate_id,
            "success": self.success,
            "output": self.output,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "node_error": self.node_error,  # Included in dict output
        }
        res.update(self.metadata)
        return res


class JITExecutor:
    """Fan-out N envelopes in parallel; collapse to ordered results."""

    _MAX_HIST_ENTRIES = 4096

    def __init__(self, max_workers: Optional[int] = None) -> None:
        # FIX 1: Replace ThreadPoolExecutor with asyncio.TaskGroup for modern Python concurrency.
        # The underlying execution mechanism is now async.
        self._max_workers_config = max_workers
        self._latency_histogram: list[float] = []
        self._failed_latencies: list[float] = []  # DORA: MTTR proxy
        self._total_nodes: int = 0                 # DORA: throughput / CFR
        self._failed_nodes: int = 0                # DORA: change_failure_rate
        self._hist_lock = threading.Lock()
        self.mandates: list[Envelope] = []  # Initialize mandates for adaptive worker count

    async def fan_out(
        self,
        work_fn: Callable[[Envelope], Any],
        envelopes: list[Envelope],
        max_workers: Optional[int] = None,
    ) -> list[ExecutionResult]:
        """Execute `work_fn(envelope)` for each envelope in parallel.

        Returns results in the same order as the input envelopes.
        `max_workers` overrides the instance default for this call only
        (used by ScopeEvaluator to allocate the right thread count).
        """
        self.mandates = envelopes  # Update mandates for adaptive worker count
        effective_workers = max_workers or self._adaptive_worker_count()

        # EXECUTION: fan out and collect results
        tasks = [self._run_async(work_fn, env) for env in envelopes]
        ordered = await asyncio.gather(*tasks)

        self._record_latencies(r.latency_ms for r in ordered if r.latency_ms is not None)
        self._record_results(ordered)
        return ordered

    async def fan_out_dag(
        self,
        work_fn: Callable[[Envelope], Any],
        envelopes: list[Envelope],
        dependencies: dict[str, list[str]],
        max_workers: Optional[int] = None,
    ) -> list[ExecutionResult]:
        """Execute a dependency DAG without waiting on whole-wave barriers.

        Nodes are submitted the moment *their own* dependencies complete,
        eliminating straggler stalls caused by rigid wave-level synchronisation.
        Results are still returned in the same order as ``envelopes``.
        """
        if not envelopes:
            return []

        self.mandates = envelopes  # Update mandates for adaptive worker count
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

        # FIX 1: Using asyncio.TaskGroup, effective_workers can be set for the group.
        effective_workers = min(
            max_workers or self._adaptive_worker_count(), len(envelopes)) or 1
        unresolved = {node_id: len(deps) for node_id, deps in dep_map.items()}
        failed_parents: dict[str, list[str]] = {
            node_id: [] for node_id in ordered_ids}
        results: dict[str, ExecutionResult] = {}
        ready = [node_id for node_id, remaining in unresolved.items()
                 if remaining == 0]
        running: dict[asyncio.Task, str] = {} # Maps task to node_id

        async def _submit_ready(tg: asyncio.TaskGroup) -> None:
            """Submits tasks from the ready queue to the executor if workers are available."""
            while ready and len(running) < effective_workers:
                node_id = ready.pop(0)
                if node_id in results:
                    continue
                if unresolved.get(node_id, 0) == 0 and not failed_parents.get(node_id):
                    # FIX 1: Create tasks using tg.create_task
                    task = tg.create_task(self._run_async(work_fn, env_by_id[node_id]))
                    running[task] = node_id

        async def _finalise_child(node_id: str) -> None:
            """
            Handles the finalization of a child node's status based on its parent's outcome.
            """
            if node_id in results or unresolved.get(node_id, 0) > 0:
                return

            if failed_parents.get(node_id):
                blocked_by = ", ".join(sorted(failed_parents[node_id]))
                results[node_id] = ExecutionResult(
                    mandate_id=node_id,
                    success=False,
                    output=None,
                    latency_ms=0.0,
                    error=f"Blocked by failed dependency: {blocked_by}",
                    node_error=f"Blocked by failed dependency: {blocked_by}",
                )
                for child_id in reverse_deps.get(node_id, []):
                    if node_id not in failed_parents.get(child_id, []):
                        failed_parents.setdefault(child_id, []).append(node_id)
                    unresolved[child_id] = max(0, unresolved.get(child_id, 0) - 1)
                    await _finalise_child(child_id)
            else:
                ready.append(node_id)

        # FIX 1: Using asyncio.TaskGroup for concurrent execution.
        async with asyncio.TaskGroup() as tg:
            await _submit_ready(tg)

            while running:
                # FIX 1: Use asyncio.wait with return_when=asyncio.FIRST_COMPLETED
                done, _ = await asyncio.wait(running.keys(), return_when=asyncio.FIRST_COMPLETED)
                for fut in done:
                    node_id = running.pop(fut)
                    try:
                        result = await fut
                        results[node_id] = result

                        if result.success:
                            for child_id in reverse_deps.get(node_id, []):
                                unresolved[child_id] = max(0, unresolved.get(child_id, 0) - 1)
                                await _finalise_child(child_id)
                        else:
                            for child_id in reverse_deps.get(node_id, []):
                                if node_id not in failed_parents.get(child_id, []):
                                    failed_parents.setdefault(child_id, []).append(node_id)
                                unresolved[child_id] = max(0, unresolved.get(child_id, 0) - 1)
                                await _finalise_child(child_id)
                    except Exception as e:
                        logger.error(f"Unexpected exception getting result for mandate {node_id}: {e}")
                        results[node_id] = ExecutionResult(
                            mandate_id=node_id,
                            success=False,
                            output=None,
                            latency_ms=0.0,
                            error=f"Internal executor error: {e}",
                            node_error=f"Internal executor error: {e}",
                        )
                        for child_id in reverse_deps.get(node_id, []):
                            if node_id not in failed_parents.get(child_id, []):
                                failed_parents.setdefault(child_id, []).append(node_id)
                            unresolved[child_id] = max(0, unresolved.get(child_id, 0) - 1)
                            await _finalise_child(child_id)

                await _submit_ready(tg)

            for node_id in ordered_ids:
                if node_id not in results:
                    if unresolved.get(node_id, 0) > 0:
                        results[node_id] = ExecutionResult(
                            mandate_id=node_id,
                            success=False,
                            output=None,
                            latency_ms=0.0,
                            error="Node never reached executable state.",
                            node_error="Node never reached executable state.",
                        )
                    elif failed_parents.get(node_id):
                        blocked_by = ", ".join(sorted(failed_parents[node_id]))
                        results[node_id] = ExecutionResult(
                            mandate_id=node_id,
                            success=False,
                            output=None,
                            latency_ms=0.0,
                            error=f"Blocked by failed dependency: {blocked_by}",
                            node_error=f"Blocked by failed dependency: {blocked_by}",
                        )
                    else:
                        results[node_id] = ExecutionResult(
                            mandate_id=node_id,
                            success=False,
                            output=None,
                            latency_ms=0.0,
                            error="Node processing failed for unknown reason.",
                            node_error="Node processing failed for unknown reason.",
                        )

        ordered = [results[node_id] for node_id in ordered_ids]
        self._record_latencies(r.latency_ms for r in ordered if r.latency_ms is not None)
        self._record_results(ordered)
        return ordered

    def latency_p50(self) -> Optional[float]:
        """Return the p50 latency in ms across all completed tasks."""
        return self._latency_percentile(0.50)

    def latency_p90(self) -> Optional[float]:
        """Return the p90 latency in ms across all completed tasks, or None if empty."""
        return self._latency_percentile(0.90)

    def latency_p99(self) -> Optional[float]:
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

    def _latency_percentile(self, percentile: float) -> Optional[float]:
        """Computes a percentile from the internal latency histogram."""
        with self._hist_lock:
            if not self._latency_histogram:
                return None
            sorted_hist = sorted(self._latency_histogram)
            idx = int(len(sorted_hist) * percentile)
            if not sorted_hist:
                return None
            if idx >= len(sorted_hist):
                idx = len(sorted_hist) - 1
            return sorted_hist[idx]

    def _record_latencies(self, latencies: Any) -> None:
        """Records latencies, maintaining a limited history and updating Prometheus."""
        with self._hist_lock:
            for latency in latencies:
                if latency is not None:
                    self._latency_histogram.append(latency)
                    # FIX 2: Using the asyncio-native histogram.
                    _MANDATE_EXECUTION_LATENCY_HISTOGRAM.observe(latency)
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
                    if r.latency_ms is not None:
                        self._failed_latencies.append(r.latency_ms)

    @staticmethod
    def _latency_percentile_unsafe(hist: list[float], percentile: float) -> Optional[float]:
        """Compute percentile from an already-locked histogram list."""
        if not hist:
            return None
        sorted_hist = sorted(hist)
        idx = int(len(sorted_hist) * percentile)
        if not sorted_hist:
            return None
        if idx >= len(sorted_hist):
            idx = len(sorted_hist) - 1
        return sorted_hist[idx]

    @staticmethod
    async def _run_async(
        work_fn: Callable[[Envelope], Any],
        env: Envelope,
    ) -> ExecutionResult:
        """Executes a single work function for a given envelope and returns an ExecutionResult."""
        start_time = time.perf_counter()
        try:
            # FIX 4: Handle both synchronous and asynchronous work functions.
            res = work_fn(env)
            if asyncio.iscoroutine(res):
                result = await res
            else:
                result = res

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            # FIX 2: Using the asyncio-native histogram.
            _MANDATE_EXECUTION_LATENCY_HISTOGRAM.observe(latency_ms)
            return ExecutionResult(
                mandate_id=env.mandate_id,
                success=True,
                output=result,
                latency_ms=latency_ms,
                node_error=None,
            )
        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            # FIX 2: Using the asyncio-native histogram.
            _MANDATE_EXECUTION_LATENCY_HISTOGRAM.observe(latency_ms)
            logger.error(f"Mandate {env.mandate_id} failed: {e}", exc_info=True)
            return ExecutionResult(
                mandate_id=env.mandate_id,
                success=False,
                output=None,
                latency_ms=latency_ms,
                error=str(e),
                node_error=str(e),
            )

    def _adaptive_worker_count(self) -> int:
        """
        Determine the number of worker tasks for asyncio.TaskGroup.

        This strategy aims to balance parallelism with resource utilization.
        It bases the number of workers on the "wave width" (number of mandates
        in the current batch), with a minimum of 1 and a maximum capped by
        the globally configured `settings.JIT_MAX_WORKERS`.
        """
        # FIX 3: Introduce adaptive worker-count tuning for asyncio.TaskGroup
        # based on wave width, referencing `settings`.
        current_max_workers = self._max_workers_config if self._max_workers_config is not None else settings.JIT_MAX_WORKERS
        wave_width = len(self.mandates) if hasattr(self, 'mandates') and self.mandates else 0

        # If wave_width is 0, use the default workers from settings.
        # Otherwise, cap the workers by the wave_width and the global max workers.
        max_workers_for_wave = wave_width if wave_width > 0 else settings.DEFAULT_WORKERS
        calculated_workers = min(current_max_workers, max_workers_for_wave)

        return max(1, calculated_workers)
