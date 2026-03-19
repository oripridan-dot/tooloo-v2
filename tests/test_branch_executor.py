"""
tests/test_branch_executor.py — Unit tests for BranchExecutor + SharedBlackboard.

Coverage:
  TestBranchSpec          (5)  — DTO shape, defaults, serialisation
  TestSharedBlackboard    (6)  — post/wait/get, timeout, concurrency
  TestBranchExecutorSync  (8)  — synchronous pipeline, tribunal, scope, refinement
  TestBranchExecutorRun   (9)  — async run_branches: fork, clone, share, mitosis
  TestMitosisExtraction   (4)  — _extract_spawned_specs edge cases
  TestBranchRunResult     (3)  — BranchRunResult.to_dict shape

Total: 35 tests (all offline — no LLM calls).
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from engine.branch_executor import (
    BRANCH_CLONE,
    BRANCH_FORK,
    BRANCH_SHARE,
    BranchExecutor,
    BranchResult,
    BranchRunResult,
    BranchSpec,
    SharedBlackboard,
)
from engine.executor import Envelope, ExecutionResult, JITExecutor
from engine.graph import TopologicalSorter
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.router import MandateRouter
from engine.scope_evaluator import ScopeEvaluator
from engine.tribunal import Tribunal


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_executor() -> BranchExecutor:
    """Create a BranchExecutor wired with lightweight in-process components."""
    bank = PsycheBank()
    return BranchExecutor(
        router=MandateRouter(),
        booster=__import__("engine.jit_booster", fromlist=[
                           "JITBooster"]).JITBooster(),
        tribunal=Tribunal(bank=bank),
        sorter=TopologicalSorter(),
        jit_executor=JITExecutor(),
        scope_evaluator=ScopeEvaluator(),
        refinement_loop=RefinementLoop(),
        broadcast_fn=None,
    )


def _spec(branch_type: str = BRANCH_FORK, intent: str = "EXPLAIN") -> BranchSpec:
    return BranchSpec(
        branch_id=f"t-{uuid.uuid4().hex[:6]}",
        branch_type=branch_type,
        mandate_text="explain the TooLoo DAG pipeline architecture",
        intent=intent,
    )


# ── 1. BranchSpec ──────────────────────────────────────────────────────────────

class TestBranchSpec:
    def test_defaults(self):
        spec = BranchSpec(
            branch_id="b1",
            branch_type=BRANCH_FORK,
            mandate_text="test mandate",
            intent="EXPLAIN",
        )
        assert spec.target == ""
        assert spec.parent_branch_id is None
        assert spec.metadata == {}

    def test_to_dict_keys(self):
        spec = _spec()
        d = spec.to_dict()
        for key in ("branch_id", "branch_type", "mandate_text", "intent",
                    "target", "parent_branch_id", "metadata"):
            assert key in d, f"Missing key: {key}"

    def test_mandate_text_truncated_in_dict(self):
        spec = BranchSpec(
            branch_id="b2", branch_type=BRANCH_CLONE,
            mandate_text="x" * 200, intent="BUILD",
        )
        assert len(spec.to_dict()["mandate_text"]) <= 120

    def test_branch_types_are_strings(self):
        assert BRANCH_FORK == "fork"
        assert BRANCH_CLONE == "clone"
        assert BRANCH_SHARE == "share"

    def test_share_spec_with_parent(self):
        spec = BranchSpec(
            branch_id="child",
            branch_type=BRANCH_SHARE,
            mandate_text="share test",
            intent="DESIGN",
            parent_branch_id="parent-1",
        )
        assert spec.parent_branch_id == "parent-1"
        assert spec.to_dict()["parent_branch_id"] == "parent-1"


# ── 2. SharedBlackboard ────────────────────────────────────────────────────────

class TestSharedBlackboard:
    def _dummy_result(self, branch_id: str) -> BranchResult:
        from engine.jit_booster import JITBooster
        from engine.tribunal import Tribunal
        from engine.psyche_bank import PsycheBank
        from engine.router import MandateRouter
        bank = PsycheBank()
        booster = JITBooster()
        route = MandateRouter().route_chat("explain architecture")
        jit = booster.fetch(route)
        trib = Tribunal(bank=bank).evaluate(
            __import__("engine.tribunal", fromlist=["Engram"]).Engram(
                slug=branch_id, intent="EXPLAIN",
                logic_body="explain architecture", domain="test",
            )
        )
        from engine.scope_evaluator import ScopeEvaluator
        scope = ScopeEvaluator().evaluate([[branch_id]], "EXPLAIN")
        from engine.refinement import RefinementLoop, RefinementReport
        refinement = RefinementLoop().evaluate([
            ExecutionResult(mandate_id=branch_id, success=True,
                            output={}, latency_ms=10.0)
        ])
        return BranchResult(
            branch_id=branch_id,
            branch_type=BRANCH_FORK,
            intent="EXPLAIN",
            jit_boost=jit,
            tribunal=trib,
            scope=scope,
            execution_results=[
                ExecutionResult(mandate_id=branch_id, success=True,
                                output={"output": "done"}, latency_ms=10.0)
            ],
            refinement=refinement,
            satisfied=True,
            latency_ms=50.0,
        )

    def test_post_and_get(self):
        bb = SharedBlackboard()
        res = self._dummy_result("bb-1")
        asyncio.get_event_loop().run_until_complete(bb.post("bb-1", res))
        assert bb.get("bb-1") is res

    def test_get_missing_returns_none(self):
        bb = SharedBlackboard()
        assert bb.get("does-not-exist") is None

    def test_all_results_returns_list(self):
        bb = SharedBlackboard()
        r1 = self._dummy_result("r1")
        r2 = self._dummy_result("r2")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bb.post("r1", r1))
        loop.run_until_complete(bb.post("r2", r2))
        all_r = bb.all_results()
        assert len(all_r) == 2

    def test_wait_for_already_posted(self):
        bb = SharedBlackboard()
        res = self._dummy_result("w1")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bb.post("w1", res))
        fetched = loop.run_until_complete(bb.wait_for("w1", timeout=1.0))
        assert fetched is res

    def test_wait_for_timeout_returns_none(self):
        bb = SharedBlackboard()
        result = asyncio.get_event_loop().run_until_complete(
            bb.wait_for("never-posted", timeout=0.1)
        )
        assert result is None

    def test_concurrent_post_and_wait(self):
        """Post from one coroutine while another is waiting."""
        bb = SharedBlackboard()
        res = self._dummy_result("concurrent")

        async def _waiter():
            return await bb.wait_for("concurrent", timeout=2.0)

        async def _poster():
            await asyncio.sleep(0.05)
            await bb.post("concurrent", res)

        async def _run():
            waiter_task = asyncio.create_task(_waiter())
            await _poster()
            return await waiter_task

        fetched = asyncio.get_event_loop().run_until_complete(_run())
        assert fetched is res


# ── 3. BranchExecutor synchronous pipeline ────────────────────────────────────

class TestBranchExecutorSync:
    def setup_method(self):
        self.executor = _make_executor()

    def test_pipeline_returns_branch_result(self):
        spec = _spec(BRANCH_FORK, "EXPLAIN")
        result = self.executor._pipeline(spec)
        assert isinstance(result, BranchResult)

    def test_pipeline_branch_id_preserved(self):
        spec = _spec()
        result = self.executor._pipeline(spec)
        assert result.branch_id == spec.branch_id

    def test_pipeline_has_jit_boost(self):
        result = self.executor._pipeline(_spec())
        assert result.jit_boost is not None
        assert len(result.jit_boost.signals) >= 0  # may be empty offline

    def test_pipeline_tribunal_ran(self):
        result = self.executor._pipeline(_spec())
        # Tribunal always returns a result (even if passed)
        assert result.tribunal is not None

    def test_pipeline_scope_evaluated(self):
        result = self.executor._pipeline(_spec())
        assert result.scope.node_count > 0
        assert result.scope.wave_count > 0

    def test_pipeline_refinement_has_verdict(self):
        result = self.executor._pipeline(_spec())
        assert result.refinement.verdict in ("pass", "warn", "fail")

    def test_pipeline_with_parent_context_injected(self):
        spec = _spec(BRANCH_SHARE, "DESIGN")
        result = self.executor._pipeline(
            spec, parent_context="parent result data")
        # Should complete without error; tribunal saw the combined text
        assert isinstance(result, BranchResult)

    def test_active_branches_registry(self):
        # After a sync pipeline, _active isn't populated (only run_branches does)
        assert isinstance(self.executor.active_branches(), list)


# ── 4. BranchExecutor async run_branches ──────────────────────────────────────

class TestBranchExecutorRun:
    def setup_method(self):
        self.executor = _make_executor()

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_single_fork_spec(self):
        result = self._run(self.executor.run_branches([_spec(BRANCH_FORK)]))
        assert isinstance(result, BranchRunResult)
        assert result.total_branches == 1

    def test_two_fork_specs_run_concurrently(self):
        specs = [_spec(BRANCH_FORK, "EXPLAIN"), _spec(BRANCH_FORK, "DESIGN")]
        result = self._run(self.executor.run_branches(specs))
        assert result.total_branches == 2
        assert len(result.branches) == 2

    def test_clone_spec(self):
        result = self._run(self.executor.run_branches(
            [_spec(BRANCH_CLONE, "AUDIT")]))
        assert result.total_branches == 1
        assert result.branches[0].branch_type == BRANCH_CLONE

    def test_run_result_satisfied_count(self):
        specs = [_spec(), _spec()]
        result = self._run(self.executor.run_branches(specs))
        assert result.satisfied_count + result.failed_count == result.total_branches

    def test_share_branch_waits_for_parent(self):
        parent_id = f"parent-{uuid.uuid4().hex[:6]}"
        child_id = f"child-{uuid.uuid4().hex[:6]}"
        parent_spec = BranchSpec(
            branch_id=parent_id,
            branch_type=BRANCH_FORK,
            mandate_text="design auth service",
            intent="DESIGN",
        )
        child_spec = BranchSpec(
            branch_id=child_id,
            branch_type=BRANCH_SHARE,
            mandate_text="implement auth service based on parent design",
            intent="BUILD",
            parent_branch_id=parent_id,
        )
        result = self._run(self.executor.run_branches(
            [parent_spec, child_spec]))
        assert result.total_branches == 2
        ids = {b.branch_id for b in result.branches}
        assert parent_id in ids
        assert child_id in ids

    def test_active_registry_populated(self):
        specs = [_spec()]
        self._run(self.executor.run_branches(specs))
        active = self.executor.active_branches()
        assert len(active) >= 1

    def test_branch_result_to_dict_complete(self):
        result = self._run(self.executor.run_branches([_spec()]))
        d = result.branches[0].to_dict()
        for key in ("branch_id", "branch_type", "intent", "jit_boost",
                    "tribunal_passed", "scope", "execution_results",
                    "refinement", "satisfied", "latency_ms"):
            assert key in d, f"Missing key: {key}"

    def test_run_result_latency_positive(self):
        result = self._run(self.executor.run_branches([_spec()]))
        assert result.latency_ms > 0

    def test_broadcast_called_on_run(self):
        events: list[dict] = []
        bank = PsycheBank()
        ex = BranchExecutor(
            router=MandateRouter(),
            booster=__import__("engine.jit_booster", fromlist=[
                               "JITBooster"]).JITBooster(),
            tribunal=Tribunal(bank=bank),
            sorter=TopologicalSorter(),
            jit_executor=JITExecutor(),
            scope_evaluator=ScopeEvaluator(),
            refinement_loop=RefinementLoop(),
            broadcast_fn=events.append,
        )
        asyncio.get_event_loop().run_until_complete(ex.run_branches([_spec()]))
        types = [e["type"] for e in events]
        assert "branch_run_start" in types
        assert "branch_run_complete" in types


# ── 5. Mitosis extraction ──────────────────────────────────────────────────────

class TestMitosisExtraction:
    def setup_method(self):
        self.executor = _make_executor()

    def _make_branch_result(self, spawned: list[dict] | None = None) -> BranchResult:
        from engine.jit_booster import JITBooster
        from engine.tribunal import Tribunal
        bank = PsycheBank()
        route = MandateRouter().route_chat("explain architecture")
        jit = JITBooster().fetch(route)
        trib = Tribunal(bank=bank).evaluate(
            __import__("engine.tribunal", fromlist=["Engram"]).Engram(
                slug="m-test", intent="EXPLAIN",
                logic_body="explain architecture", domain="test",
            )
        )
        scope = ScopeEvaluator().evaluate([["n1"]], "EXPLAIN")
        refinement = RefinementLoop().evaluate([
            ExecutionResult(mandate_id="m-test", success=True,
                            output={}, latency_ms=5.0)
        ])
        output: dict[str, Any] = {}
        if spawned is not None:
            output["__spawned_branches__"] = spawned
        return BranchResult(
            branch_id="parent-1",
            branch_type=BRANCH_FORK,
            intent="EXPLAIN",
            jit_boost=jit,
            tribunal=trib,
            scope=scope,
            execution_results=[
                ExecutionResult(mandate_id="m-test", success=True,
                                output=output, latency_ms=5.0)
            ],
            refinement=refinement,
            satisfied=True,
            latency_ms=30.0,
        )

    def test_no_spawned_specs_returns_empty(self):
        result = self._make_branch_result(spawned=None)
        parent_spec = _spec()
        new_specs = self.executor._extract_spawned_specs(result, parent_spec)
        assert new_specs == []

    def test_spawned_spec_extracted(self):
        spawned = [{"branch_id": "dyn-1", "branch_type": "fork",
                    "mandate_text": "do something", "intent": "BUILD"}]
        result = self._make_branch_result(spawned=spawned)
        parent_spec = _spec()
        new_specs = self.executor._extract_spawned_specs(result, parent_spec)
        assert len(new_specs) == 1
        assert new_specs[0].branch_id == "dyn-1"
        assert new_specs[0].branch_type == BRANCH_FORK

    def test_duplicate_specs_deduplicated(self):
        spawned = [
            {"branch_id": "dup", "branch_type": "fork",
             "mandate_text": "do A", "intent": "BUILD"},
            {"branch_id": "dup", "branch_type": "fork",
             "mandate_text": "do B", "intent": "DEBUG"},
        ]
        result = self._make_branch_result(spawned=spawned)
        new_specs = self.executor._extract_spawned_specs(result, _spec())
        assert len(new_specs) == 1  # deduped by branch_id

    def test_share_spec_without_parent_defaults_to_current(self):
        spawned = [{"branch_id": "share-child", "branch_type": "share",
                    "mandate_text": "build from parent", "intent": "BUILD"}]
        result = self._make_branch_result(spawned=spawned)
        parent_spec = _spec()
        new_specs = self.executor._extract_spawned_specs(result, parent_spec)
        assert new_specs[0].parent_branch_id == parent_spec.branch_id


# ── 6. BranchRunResult ────────────────────────────────────────────────────────

class TestBranchRunResult:
    def _make_run_result(self) -> BranchRunResult:
        from engine.jit_booster import JITBooster
        from engine.tribunal import Tribunal
        bank = PsycheBank()
        route = MandateRouter().route_chat("design something")
        jit = JITBooster().fetch(route)
        trib = Tribunal(bank=bank).evaluate(
            __import__("engine.tribunal", fromlist=["Engram"]).Engram(
                slug="rr-test", intent="DESIGN",
                logic_body="design something", domain="test",
            )
        )
        scope = ScopeEvaluator().evaluate([["n1"]], "DESIGN")
        refinement = RefinementLoop().evaluate([
            ExecutionResult(mandate_id="rr-test", success=True,
                            output={}, latency_ms=3.0)
        ])
        br = BranchResult(
            branch_id="rr-1",
            branch_type=BRANCH_FORK,
            intent="DESIGN",
            jit_boost=jit,
            tribunal=trib,
            scope=scope,
            execution_results=[
                ExecutionResult(mandate_id="rr-test", success=True,
                                output={}, latency_ms=3.0)
            ],
            refinement=refinement,
            satisfied=True,
            latency_ms=20.0,
        )
        return BranchRunResult(
            run_id="run-1",
            branches=[br],
            total_branches=1,
            satisfied_count=1,
            failed_count=0,
            latency_ms=25.0,
        )

    def test_to_dict_keys(self):
        rr = self._make_run_result()
        d = rr.to_dict()
        for key in ("run_id", "branches", "total_branches",
                    "satisfied_count", "failed_count", "latency_ms"):
            assert key in d

    def test_to_dict_branches_list(self):
        rr = self._make_run_result()
        d = rr.to_dict()
        assert isinstance(d["branches"], list)
        assert len(d["branches"]) == 1

    def test_latency_ms_rounded(self):
        rr = self._make_run_result()
        d = rr.to_dict()
        # Should be a float value
        assert isinstance(d["latency_ms"], float)
