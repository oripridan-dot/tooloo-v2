"""
engine/supervisor.py — Two-Stroke Cognitive Engine.

THE singular execution pipeline for all mandates.  Replaces the former
five-wave linear approach with a recursive, self-supervising two-stroke loop:

  [TooLoo Pre-Flight Supervisor]  → JIT SOTA inject + Tribunal scan
        ↓
  [Process 1 — Catalyst]          → Build DAG plan, produce draft
        ↓  (emits ``process_1_draft`` SSE event)
  [TooLoo Mid-Flight Supervisor]  → second JIT pass + scope + tribunal re-scan
        ↓
  [Process 2 — Crucible]          → Execute DAG via JITExecutor
        ↓  (emits ``process_2_execute`` SSE event)
  [Satisfaction Gate]             → RefinementLoop verdict
        ↓  loop if not satisfied (failure injected as priority JIT signal)

The loop terminates when:
  • ``verdict == "pass"``         → satisfied, loop exits cleanly
  • ``iteration > MAX_ITERATIONS`` → exits (unsatisfied, final verdict forwarded)

Emits SSE events via an optional ``broadcast_fn`` at every stage transition.
All iteration state is immutable — each pass starts fresh, enriched only by a
failure signal injected from the previous pass.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from engine.executor import Envelope, ExecutionResult, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBoostResult, JITBooster
from engine.refinement import RefinementLoop, RefinementReport
from engine.router import (
    LockedIntent,
    MandateRouter,
    RouteResult,
    compute_buddy_line,
)
from engine.scope_evaluator import ScopeEvaluation, ScopeEvaluator
from engine.tribunal import Engram, Tribunal, TribunalResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ITERATIONS: int = 3  # safety cap on the satisfaction loop

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass
class ProcessOneDraft:
    """Output of Process 1 (Catalyst) — proposed plan, ready for mid-flight check."""

    plan: list[list[str]]   # wave plan from TopologicalSorter
    scope: ScopeEvaluation
    mandate_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan,
            "scope": self.scope.to_dict(),
            "mandate_id": self.mandate_id,
        }


@dataclass
class TwoStrokeIteration:
    """Full record of one complete two-stroke cycle."""

    iteration: int
    preflight_jit: JITBoostResult
    preflight_tribunal: TribunalResult
    process_1: ProcessOneDraft
    midflight_jit: JITBoostResult
    process_2_results: list[ExecutionResult]
    refinement: RefinementReport
    satisfied: bool
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "preflight_jit": self.preflight_jit.to_dict(),
            "preflight_tribunal": self.preflight_tribunal.to_dict(),
            "process_1": self.process_1.to_dict(),
            "midflight_jit": self.midflight_jit.to_dict(),
            "process_2_results": [r.to_dict() for r in self.process_2_results],
            "refinement": self.refinement.to_dict(),
            "satisfied": self.satisfied,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class TwoStrokeResult:
    """Final result of the complete two-stroke pipeline run."""

    pipeline_id: str
    locked_intent: LockedIntent
    iterations: list[TwoStrokeIteration]
    final_verdict: str      # "pass" | "warn" | "fail"
    satisfied: bool
    total_iterations: int
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "locked_intent": self.locked_intent.to_dict(),
            "iterations": [it.to_dict() for it in self.iterations],
            "final_verdict": self.final_verdict,
            "satisfied": self.satisfied,
            "total_iterations": self.total_iterations,
            "latency_ms": round(self.latency_ms, 2),
        }


# ---------------------------------------------------------------------------
# Two-Stroke Engine
# ---------------------------------------------------------------------------


class TwoStrokeEngine:
    """The singular execution pipeline for TooLoo V2.

    Architecture::

        Pre-Flight Supervisor → Process 1 → Mid-Flight Supervisor →
        Process 2 → Satisfaction Gate → (loop back if needed)

    All former five-wave pipeline logic is channelled through this class.
    Every component is injected via the constructor to enable full test isolation.
    """

    def __init__(
        self,
        router: MandateRouter,
        booster: JITBooster,
        tribunal: Tribunal,
        sorter: TopologicalSorter,
        executor: JITExecutor,
        scope_evaluator: ScopeEvaluator,
        refinement_loop: RefinementLoop,
        broadcast_fn: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._router = router
        self._booster = booster
        self._tribunal = tribunal
        self._sorter = sorter
        self._executor = executor
        self._scope = scope_evaluator
        self._refine = refinement_loop
        self._broadcast: Callable[[dict[str, Any]], None] = (
            broadcast_fn if broadcast_fn is not None else lambda _: None
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        locked_intent: LockedIntent,
        pipeline_id: str | None = None,
        max_iterations: int = MAX_ITERATIONS,
    ) -> TwoStrokeResult:
        """Run the full two-stroke loop until satisfied or max_iterations reached.

        Args:
            locked_intent: A confirmed, fully-understood intent from
                           ``ConversationalIntentDiscovery``.
            pipeline_id:   Optional stable ID for correlating SSE events.
            max_iterations: Override the default ``MAX_ITERATIONS`` cap.

        Returns:
            ``TwoStrokeResult`` with per-iteration records and a final verdict.
        """
        t0 = time.monotonic()
        pipeline_id = pipeline_id or f"pipe-{uuid.uuid4().hex[:8]}"
        iterations: list[TwoStrokeIteration] = []
        prior_failure = ""

        self._broadcast({
            "type": "pipeline_start",
            "pipeline_id": pipeline_id,
            "intent": locked_intent.intent,
            "confidence": locked_intent.confidence,
        })

        for i in range(1, max_iterations + 1):
            iteration_result, satisfied = self._run_iteration(
                locked_intent=locked_intent,
                pipeline_id=pipeline_id,
                iteration=i,
                prior_failure_signal=prior_failure,
            )
            iterations.append(iteration_result)

            self._broadcast({
                "type": "satisfaction_gate",
                "pipeline_id": pipeline_id,
                "iteration": i,
                "satisfied": satisfied,
                "verdict": iteration_result.refinement.verdict,
                "rerun_advised": iteration_result.refinement.rerun_advised,
            })

            if satisfied:
                break

            # Build failure signal to inject into next iteration's pre-flight.
            failed_nodes = iteration_result.refinement.failed_nodes
            prior_failure = (
                f"Iteration {i} failed — {len(failed_nodes)} node(s) errored: "
                f"{', '.join(failed_nodes[:3])}. Retry with corrected approach."
            ) if failed_nodes else (
                f"Iteration {i} verdict='{iteration_result.refinement.verdict}' "
                f"— re-evaluating strategy and retrying."
            )

        last = iterations[-1] if iterations else None
        final_verdict = last.refinement.verdict if last else "fail"
        satisfied = last.satisfied if last else False
        result = TwoStrokeResult(
            pipeline_id=pipeline_id,
            locked_intent=locked_intent,
            iterations=iterations,
            final_verdict=final_verdict,
            satisfied=satisfied,
            total_iterations=len(iterations),
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        )

        self._broadcast({
            "type": "loop_complete",
            "pipeline_id": pipeline_id,
            "satisfied": result.satisfied,
            "final_verdict": result.final_verdict,
            "total_iterations": result.total_iterations,
            "latency_ms": result.latency_ms,
        })

        return result

    # ── Private: single two-stroke iteration ───────────────────────────────────

    def _run_iteration(
        self,
        locked_intent: LockedIntent,
        pipeline_id: str,
        iteration: int,
        prior_failure_signal: str,
    ) -> tuple[TwoStrokeIteration, bool]:
        t0 = time.monotonic()
        mandate_id = f"{pipeline_id}-iter{iteration}"
        intent = locked_intent.intent

        # ── Pre-Flight Supervisor ─────────────────────────────────────────────
        # Synthesise a RouteResult so JIT/Tribunal APIs work without modification.
        route = _route_from_locked(locked_intent)
        if prior_failure_signal:
            # Inject previous-iteration failure as high-priority context.
            route.mandate_text = (
                f"[retry-signal] {prior_failure_signal}\n\n{locked_intent.mandate_text}"
            )

        preflight_jit = self._booster.fetch(route)
        self._router.apply_jit_boost(route, preflight_jit.boosted_confidence)

        preflight_tribunal = self._tribunal.evaluate(Engram(
            slug=f"{mandate_id}-preflight",
            intent=intent,
            logic_body=locked_intent.mandate_text,
            domain="backend",
            mandate_level="L2",
        ))

        self._broadcast({
            "type": "preflight",
            "pipeline_id": pipeline_id,
            "iteration": iteration,
            "jit_boost": preflight_jit.to_dict(),
            "tribunal": preflight_tribunal.to_dict(),
        })

        # ── Process 1 — Catalyst ──────────────────────────────────────────────
        # Build the DAG plan and draft without executing anything yet.
        spec: list[tuple[str, list[str]]] = [
            (f"{mandate_id}-recon",    []),
            (f"{mandate_id}-design",   [f"{mandate_id}-recon"]),
            (f"{mandate_id}-generate", [f"{mandate_id}-design"]),
            (f"{mandate_id}-validate", [f"{mandate_id}-generate"]),
        ]
        plan = self._sorter.sort(spec)
        scope = self._scope.evaluate(plan, intent=intent)

        process_1 = ProcessOneDraft(
            plan=plan,
            scope=scope,
            mandate_id=mandate_id,
        )

        self._broadcast({
            "type": "process_1_draft",
            "pipeline_id": pipeline_id,
            "iteration": iteration,
            "nodes": [n for wave in plan for n in wave],
            "waves": plan,
            "scope": scope.to_dict(),
        })

        # ── Mid-Flight Supervisor ─────────────────────────────────────────────
        # Second JIT pass focused on plan optimisation and security.
        mid_route = _route_from_locked(locked_intent)
        mid_route.mandate_text = (
            f"[mid-flight] intent={intent} "
            f"nodes={scope.node_count} waves={scope.wave_count} "
            f"strategy={scope.strategy}: {locked_intent.mandate_text}"
        )
        midflight_jit = self._booster.fetch(mid_route)

        # Tribunal re-scan on the plan body (cannot have poisoned node labels).
        plan_body = " ".join(n for wave in plan for n in wave)
        self._tribunal.evaluate(Engram(
            slug=f"{mandate_id}-midflight",
            intent=intent,
            logic_body=plan_body,
            domain="backend",
            mandate_level="L2",
        ))

        self._broadcast({
            "type": "midflight",
            "pipeline_id": pipeline_id,
            "iteration": iteration,
            "jit_boost": midflight_jit.to_dict(),
            "scope": scope.to_dict(),
        })

        # ── Process 2 — Crucible ──────────────────────────────────────────────
        # Execute the DAG — the physical materialisation of the plan.
        envelopes = [
            Envelope(
                mandate_id=f"{mandate_id}-{i}",
                intent=intent,
                domain="backend",
                metadata={"wave": i, "nodes": wave, "iteration": iteration},
            )
            for i, wave in enumerate(plan)
        ]

        def _work(env: Envelope) -> str:
            return f"wave-{env.metadata['wave']}-iter{env.metadata['iteration']}-done"

        exec_results = self._executor.fan_out(
            _work, envelopes, max_workers=scope.recommended_workers
        )

        self._broadcast({
            "type": "process_2_execute",
            "pipeline_id": pipeline_id,
            "iteration": iteration,
            "results": [r.to_dict() for r in exec_results],
        })

        # ── Satisfaction Gate ─────────────────────────────────────────────────
        refinement = self._refine.evaluate(exec_results, iteration=iteration)
        satisfied = refinement.verdict == "pass"

        return TwoStrokeIteration(
            iteration=iteration,
            preflight_jit=preflight_jit,
            preflight_tribunal=preflight_tribunal,
            process_1=process_1,
            midflight_jit=midflight_jit,
            process_2_results=exec_results,
            refinement=refinement,
            satisfied=satisfied,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        ), satisfied


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _route_from_locked(locked: LockedIntent) -> RouteResult:
    """Synthesise a RouteResult from a LockedIntent.

    Allows existing JIT, Tribunal, and circuit-breaker APIs to operate on
    locked intents without any code-path modification.
    """
    return RouteResult(
        intent=locked.intent,
        confidence=locked.confidence,
        circuit_open=False,
        mandate_text=locked.mandate_text,
        buddy_line=compute_buddy_line(locked.intent, locked.confidence),
    )
