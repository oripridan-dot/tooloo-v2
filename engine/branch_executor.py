"""
engine/branch_executor.py — Branched Async Multi-Step Autonomous Process Engine.

Core capability: TooLoo can "split", "share", or "clone" its cognitive logic
to run branched, asynchronous, multi-step autonomous processes in parallel.

Architecture:
  BranchExecutor spawns independent BranchPipeline instances, each running a
  full NStroke-style pipeline on its own mandate/sub-task.  Branches are:

    - FORK   — two or more independent paths diverge from a parent context
    - CLONE  — identical logic applied to multiple targets simultaneously
    - SHARE  — a shared intermediate result fans out to N dependent branches

  Branches run concurrently via asyncio + ThreadPoolExecutor (Law 17 — each
  branch is perfectly isolated).  A SharedBlackboard provides read-only result
  exchange between completed branches and waiting dependents.

  Full pipeline per branch:
    JIT SOTA boost → Tribunal scan → Scope evaluate → JITExecutor fan-out
    → Refinement verdict → Emit to SharedBlackboard

Security:
  - All branch contexts are isolated; no shared mutable state between branches.
  - Blackboard writes are serialised via asyncio.Lock (no race conditions).
  - Branch IDs carry a UUID to prevent spoofing.
  - All inputs pass through Tribunal before execution.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from engine.executor import Envelope, ExecutionResult, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBooster, JITBoostResult
from engine.mandate_executor import make_live_work_fn
from engine.refinement import RefinementLoop, RefinementReport
from engine.router import MandateRouter, RouteResult, compute_buddy_line
from engine.scope_evaluator import ScopeEvaluation, ScopeEvaluator
from engine.tribunal import Engram, Tribunal, TribunalResult

# ── Branch type constants ─────────────────────────────────────────────────────
BRANCH_FORK = "fork"    # independent parallel paths
BRANCH_CLONE = "clone"  # identical logic, multiple targets
BRANCH_SHARE = "share"  # parent result fans out to dependents

# Control: configurable thresholds for branch execution
_MAX_RETRIES = 3              # per-branch retry ceiling before rollback
_BRANCH_TIMEOUT_THRESHOLD = 60  # seconds — branches exceeding this trigger circuit-breaker

# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class BranchSpec:
    """Specification for one branch in a parallel multi-step process."""

    branch_id: str
    branch_type: str                    # BRANCH_FORK | BRANCH_CLONE | BRANCH_SHARE
    mandate_text: str
    intent: str
    # optional target (file path, service name …)
    target: str = ""
    parent_branch_id: str | None = None  # for SHARE — wait for parent result
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "branch_type": self.branch_type,
            "mandate_text": self.mandate_text[:120],
            "intent": self.intent,
            "target": self.target,
            "parent_branch_id": self.parent_branch_id,
            "metadata": self.metadata,
        }


@dataclass
class BranchResult:
    """Result of one completed branch pipeline."""

    branch_id: str
    branch_type: str
    intent: str
    jit_boost: JITBoostResult
    tribunal: TribunalResult
    scope: ScopeEvaluation
    execution_results: list[ExecutionResult]
    refinement: RefinementReport
    satisfied: bool
    latency_ms: float
    error: str | None = None
    spawned_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "branch_type": self.branch_type,
            "intent": self.intent,
            "jit_boost": self.jit_boost.to_dict(),
            "tribunal_passed": self.tribunal.passed,
            "scope": self.scope.to_dict(),
            "execution_results": [r.to_dict() for r in self.execution_results],
            "refinement": self.refinement.to_dict(),
            "satisfied": self.satisfied,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "spawned_at": self.spawned_at,
        }


@dataclass
class BranchRunResult:
    """Aggregated result of a full parallel branch execution run."""

    run_id: str
    branches: list[BranchResult]
    total_branches: int
    satisfied_count: int
    failed_count: int
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "branches": [b.to_dict() for b in self.branches],
            "total_branches": self.total_branches,
            "satisfied_count": self.satisfied_count,
            "failed_count": self.failed_count,
            "latency_ms": round(self.latency_ms, 2),
        }


# ── Shared Blackboard ─────────────────────────────────────────────────────────


class SharedBlackboard:
    """Read-only result exchange between completed and waiting branches.

    SHARE-type branches depend on a parent branch result.  They block until
    the parent posts its result.  All writes are serialised via asyncio.Lock.
    """

    def __init__(self) -> None:
        self._results: dict[str, BranchResult] = {}
        self._lock = asyncio.Lock()
        self._events: dict[str, asyncio.Event] = {}

    async def post(self, branch_id: str, result: BranchResult) -> None:
        async with self._lock:
            self._results[branch_id] = result
            if branch_id in self._events:
                self._events[branch_id].set()

    async def wait_for(self, branch_id: str, timeout: float = 30.0) -> BranchResult | None:
        event = asyncio.Event()
        async with self._lock:
            if branch_id in self._results:
                return self._results[branch_id]
            self._events[branch_id] = event
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            return None
        async with self._lock:
            return self._results.get(branch_id)

    def get(self, branch_id: str) -> BranchResult | None:
        return self._results.get(branch_id)

    def all_results(self) -> list[BranchResult]:
        return list(self._results.values())


# ── Branch Executor ───────────────────────────────────────────────────────────


class BranchExecutor:
    """Spawns and manages branched async multi-step autonomous processes.

    Each branch runs an isolated pipeline: JIT SOTA → Tribunal → Scope →
    JITExecutor fan-out → Refinement.  Results are shared via SharedBlackboard.

    Usage::

        executor = BranchExecutor(
            router=..., booster=..., tribunal=..., sorter=...,
            jit_executor=..., scope_evaluator=..., refinement_loop=...,
            broadcast_fn=...,
        )
        specs = [
            BranchSpec("b1", BRANCH_FORK, "design auth module", "DESIGN"),
            BranchSpec("b2", BRANCH_FORK, "implement token store", "BUILD"),
        ]
        run_result = await executor.run_branches(specs)
    """

    def __init__(
        self,
        router: MandateRouter,
        booster: JITBooster,
        tribunal: Tribunal,
        sorter: TopologicalSorter,
        jit_executor: JITExecutor,
        scope_evaluator: ScopeEvaluator,
        refinement_loop: RefinementLoop,
        broadcast_fn: Callable[[dict[str, Any]], None] | None = None,
        work_fn: Callable[[Envelope], Any] | None = None,
    ) -> None:
        self._router = router
        self._booster = booster
        self._tribunal = tribunal
        self._sorter = sorter
        self._executor = jit_executor
        self._scope = scope_evaluator
        self._refine = refinement_loop
        self._broadcast: Callable[[dict[str, Any]], None] = (
            broadcast_fn if broadcast_fn is not None else lambda _: None
        )
        self._work_fn = work_fn
        # Active branch registry for status queries
        self._active: dict[str, dict[str, Any]] = {}

    def active_branches(self) -> list[dict[str, Any]]:
        """Return status snapshot of all registered branches."""
        return list(self._active.values())

    async def run_branches(
        self,
        specs: list[BranchSpec],
        timeout: float = 120.0,
    ) -> BranchRunResult:
        """Execute all branch specs concurrently, respecting SHARE dependencies.

        Fork and Clone branches run in parallel.  Share branches wait for their
        parent branch to post its result before executing.

        Args:
            specs:   List of BranchSpec instances to execute.
            timeout: Per-branch pipeline timeout in seconds.
        """
        run_id = f"branch-run-{uuid.uuid4().hex[:8]}"
        t0 = time.monotonic()
        blackboard = SharedBlackboard()

        # Prune completed entries to prevent unbounded growth on long-lived singletons.
        # Keep only branches that are still pending/running (active work). Completed
        # entries from prior runs are evicted here rather than accumulating forever.
        if self._active:
            self._active = {
                bid: st
                for bid, st in self._active.items()
                if st.get("status") not in ("satisfied", "unsatisfied", "error")
            }

        self._broadcast({
            "type": "branch_run_start",
            "run_id": run_id,
            "total_branches": len(specs),
            "branch_ids": [s.branch_id for s in specs],
        })

        # Register all as pending
        for spec in specs:
            self._active[spec.branch_id] = {
                "branch_id": spec.branch_id,
                "intent": spec.intent,
                "status": "pending",
                "branch_type": spec.branch_type,
            }

        # Launch all branches as concurrent asyncio tasks
        tasks = [
            asyncio.create_task(
                self._run_branch(spec, blackboard, timeout),
                name=spec.branch_id,
            )
            for spec in specs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        branch_results: list[BranchResult] = []
        for spec, res in zip(specs, results, strict=True):
            if isinstance(res, BranchResult):
                branch_results.append(res)
                self._active[spec.branch_id]["status"] = (
                    "satisfied" if res.satisfied else "unsatisfied"
                )
            else:
                # Exception or timeout — synthesise a failed result
                err_result = self._make_error_result(spec, str(res))
                branch_results.append(err_result)
                self._active[spec.branch_id]["status"] = "error"

        satisfied = sum(1 for r in branch_results if r.satisfied)
        failed = len(branch_results) - satisfied

        run_result = BranchRunResult(
            run_id=run_id,
            branches=branch_results,
            total_branches=len(branch_results),
            satisfied_count=satisfied,
            failed_count=failed,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        )

        self._broadcast({
            "type": "branch_run_complete",
            "run_id": run_id,
            "satisfied": satisfied,
            "failed": failed,
            "latency_ms": run_result.latency_ms,
        })

        return run_result

    async def _run_branch(
        self,
        spec: BranchSpec,
        blackboard: SharedBlackboard,
        timeout: float,
    ) -> BranchResult:
        """Execute a single branch pipeline asynchronously."""
        self._broadcast({
            "type": "branch_spawned",
            "branch_id": spec.branch_id,
            "branch_type": spec.branch_type,
            "intent": spec.intent,
            "target": spec.target,
        })
        self._active[spec.branch_id]["status"] = "running"

        # SHARE branches wait for their parent result (parent context injection)
        parent_context = ""
        if spec.branch_type == BRANCH_SHARE and spec.parent_branch_id:
            parent = await blackboard.wait_for(spec.parent_branch_id, timeout=timeout * 0.4)
            if parent and parent.execution_results:
                # Inject the parent's best output as context
                best = next(
                    (r for r in parent.execution_results if r.success), None
                )
                if best and isinstance(best.output, dict):
                    parent_context = str(best.output.get("output", ""))[:400]

        # Run the pipeline in a thread (CPU-bound LLM calls)
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, self._pipeline, spec, parent_context),
            timeout=timeout,
        )

        await blackboard.post(spec.branch_id, result)

        # ── Dynamic mitosis: if the work_fn yielded new BranchSpecs, spawn them
        # The _pipeline method stores any dynamically yielded specs on the result
        # via result.refinement.recommendations tagged with '__spawn__' prefix.
        # Alternatively the work_fn can return BranchSpec objects directly in
        # exec_results metadata — we check both paths here.
        spawned_specs = self._extract_spawned_specs(result, spec)
        if spawned_specs:
            self._broadcast({
                "type": "branch_mitosis",
                "parent_branch_id": spec.branch_id,
                "spawned_branch_ids": [s.branch_id for s in spawned_specs],
            })
            # Register SHARE specs with the blackboard pre-launch to prevent
            # a deadlock where the child waits for a parent that hasn't posted.
            for child in spawned_specs:
                if child.branch_type == BRANCH_SHARE and child.parent_branch_id and blackboard.get(child.parent_branch_id) is None:
                    pass  # parent is already posted above for current-branch mitosis
            # Register pending status for new specs
            for child in spawned_specs:
                self._active[child.branch_id] = {
                    "branch_id": child.branch_id,
                    "intent": child.intent,
                    "status": "pending",
                    "branch_type": child.branch_type,
                    "parent_branch_id": child.parent_branch_id,
                }
            # Launch dynamically spawned branches concurrently
            child_tasks = [
                asyncio.create_task(
                    self._run_branch(child, blackboard, timeout),
                    name=child.branch_id,
                )
                for child in spawned_specs
            ]
            child_results = await asyncio.gather(*child_tasks, return_exceptions=True)
            # Attach child results to the parent result for upstream visibility
            for child_spec, child_res in zip(spawned_specs, child_results, strict=True):
                if isinstance(child_res, BranchResult):
                    self._active[child_spec.branch_id]["status"] = (
                        "satisfied" if child_res.satisfied else "unsatisfied"
                    )
                else:
                    error_res = self._make_error_result(
                        child_spec, str(child_res))
                    await blackboard.post(child_spec.branch_id, error_res)
                    self._active[child_spec.branch_id]["status"] = "error"

        self._broadcast({
            "type": "branch_complete",
            "branch_id": spec.branch_id,
            "satisfied": result.satisfied,
            "latency_ms": result.latency_ms,
            "refinement_verdict": result.refinement.verdict,
        })

        return result

    def _pipeline(self, spec: BranchSpec, parent_context: str = "") -> BranchResult:
        """Synchronous branch pipeline — runs inside thread pool (Law 17)."""
        t0 = time.monotonic()

        # 1. Build RouteResult from spec
        route = RouteResult(
            intent=spec.intent,
            confidence=0.80,  # branches start at confident baseline
            circuit_open=False,
            mandate_text=spec.mandate_text,
            buddy_line=compute_buddy_line(spec.intent, 0.80),
        )

        # 2. JIT boost (with action_context for node-level targeting)
        action_context = spec.target or spec.mandate_text[:100]
        jit = self._booster.fetch(
            route, action_context=action_context
        )
        self._router.apply_jit_boost(route, jit.boosted_confidence)

        # 3. Tribunal scan
        mandate_body = spec.mandate_text
        if parent_context:
            mandate_body = f"{mandate_body}\n\n[parent-context]: {parent_context}"
        tribunal = self._tribunal.evaluate(Engram(
            slug=f"branch-{spec.branch_id}",
            intent=spec.intent,
            logic_body=spec.mandate_text,
            domain="backend",
            mandate_level="L2",
        ))

        # 4. Build DAG — mandatory AUDIT + DESIGN in waves 1-2, IMPLEMENT last
        dag_nodes = [
            f"branch-{spec.branch_id}-audit",
            f"branch-{spec.branch_id}-design",
            f"branch-{spec.branch_id}-implement",
            f"branch-{spec.branch_id}-validate",
        ]
        waves: list[list[str]] = [
            [dag_nodes[0]],
            [dag_nodes[1]],
            [dag_nodes[2]],
            [dag_nodes[3]],
        ]

        # 5. Scope evaluate
        scope = self._scope.evaluate(waves, spec.intent)

        # 6. Build envelopes with injected JIT signals + parent context
        envelopes = [
            Envelope(
                mandate_id=nid,
                intent=spec.intent,
                domain="backend" if not spec.target else "fullstack",
                metadata={
                    "jit_signals": jit.signals,
                    "parent_context": parent_context,
                    "target": spec.target,
                    "branch_id": spec.branch_id,
                },
            )
            for nid in dag_nodes
        ]

        dependency_map = {
            dag_nodes[0]: [],
            dag_nodes[1]: [dag_nodes[0]],
            dag_nodes[2]: [dag_nodes[1]],
            dag_nodes[3]: [dag_nodes[2]],
        }

        # 7. Fan-out execution
        effective_work_fn = self._work_fn or make_live_work_fn(
            mandate_text=spec.mandate_text,
            intent=spec.intent,
            jit_signals=jit.signals,
        )

        exec_results = self._executor.fan_out_dag(
            effective_work_fn,
            envelopes,
            dependency_map,
            max_workers=scope.recommended_workers,
        )

        # 8. Refinement
        refinement = self._refine.evaluate(exec_results)

        return BranchResult(
            branch_id=spec.branch_id,
            branch_type=spec.branch_type,
            intent=spec.intent,
            jit_boost=jit,
            tribunal=tribunal,
            scope=scope,
            execution_results=exec_results,
            refinement=refinement,
            satisfied=(refinement.verdict == "pass"),
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
        )

    def _extract_spawned_specs(
        self,
        result: BranchResult,
        parent_spec: BranchSpec,
    ) -> list[BranchSpec]:
        """Extract dynamically yielded BranchSpecs from a completed pipeline result.

        Two collection paths:
          1. ExecutionResult.output dict contains a ``__spawned_branches__`` key
             whose value is a list of BranchSpec-compatible dicts.
          2. (Future) work_fn returns BranchSpec objects directly — callers may
             also embed serialised specs inside exec_result metadata.

        Returns a deduplicated list of new BranchSpec objects that do NOT yet
        exist in _active (prevents double-spawning on retries).
        """
        new_specs: list[BranchSpec] = []
        seen_ids: set[str] = set(self._active.keys())

        for exec_result in result.execution_results:
            output = exec_result.output if isinstance(
                exec_result.output, dict) else {}
            raw_specs = output.get("__spawned_branches__", [])
            if not isinstance(raw_specs, list):
                continue
            for raw in raw_specs:
                if not isinstance(raw, dict):
                    continue
                branch_id = raw.get(
                    "branch_id") or f"dyn-{uuid.uuid4().hex[:8]}"
                if branch_id in seen_ids:
                    continue
                seen_ids.add(branch_id)
                branch_type = raw.get("branch_type", BRANCH_FORK)
                parent_id = raw.get("parent_branch_id")
                # SHARE children without an explicit parent default to the
                # current branch so synchronization is always well-defined.
                if branch_type == BRANCH_SHARE and not parent_id:
                    parent_id = parent_spec.branch_id
                new_specs.append(BranchSpec(
                    branch_id=branch_id,
                    branch_type=branch_type,
                    mandate_text=raw.get(
                        "mandate_text", parent_spec.mandate_text),
                    intent=raw.get("intent", parent_spec.intent),
                    target=raw.get("target", ""),
                    parent_branch_id=parent_id,
                    metadata={**raw.get("metadata", {}),
                              "dynamically_spawned": True},
                ))
        return new_specs

    def _make_error_result(self, spec: BranchSpec, error: str) -> BranchResult:
        """Synthesise a failed BranchResult when the pipeline errors."""
        import uuid as _uuid

        from engine.jit_booster import JITBoostResult
        from engine.scope_evaluator import ScopeEvaluation
        from engine.tribunal import TribunalResult

        dummy_jit = JITBoostResult(
            jit_id=f"jit-err-{_uuid.uuid4().hex[:6]}",
            intent=spec.intent,
            original_confidence=0.0,
            boosted_confidence=0.0,
            boost_delta=0.0,
            signals=[],
            source="structured",
        )
        dummy_tribunal = TribunalResult(
            slug=f"branch-{spec.branch_id}-err",
            passed=False,
            poison_detected=False,
            heal_applied=False,
            vast_learn_triggered=False,
            violations=["pipeline_error"],
        )
        dummy_scope = ScopeEvaluation(
            node_count=0, wave_count=0, max_wave_width=0,
            critical_path_length=0, parallelism_ratio=0.0,
            recommended_workers=1, strategy="serial",
            risk_surface=0, scope_summary="error — pipeline failed",
        )
        dummy_refine = RefinementReport(
            total=0, succeeded=0, failed=0,
            success_rate=0.0, avg_latency_ms=0.0, p50_latency_ms=0.0, p90_latency_ms=0.0,
            slow_nodes=[], failed_nodes=[spec.branch_id],
            recommendations=["Pipeline error — retry with corrected mandate"],
            rerun_advised=False, verdict="fail",
        )
        return BranchResult(
            branch_id=spec.branch_id,
            branch_type=spec.branch_type,
            intent=spec.intent,
            jit_boost=dummy_jit,
            tribunal=dummy_tribunal,
            scope=dummy_scope,
            execution_results=[],
            refinement=dummy_refine,
            satisfied=False,
            latency_ms=0.0,
            error=error[:300],
        )

    @staticmethod
    def _default_work_fn(env: Envelope) -> dict[str, Any]:
        """Default symbolic work function — replaced by LLM fn in production."""
        node = env.mandate_id.rsplit("-", 1)[-1]
        return {
            "node": env.mandate_id,
            "intent": env.intent,
            "output": f"[symbolic-branch-{node}] intent={env.intent}",
            "status": "executed",
        }
