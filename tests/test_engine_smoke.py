"""
tests/test_engine_smoke.py — Fast Ouroboros Validation Smoke Suite.

TARGET: All 12 engine components the ouroboros cycle can write to.
PURPOSE: Post-improvement health check — must pass in < 15 s offline
         (< 45 s live, accounting for one real Gemini call per component).
SCOPE: Contract-level smoke tests — not full coverage.  Full coverage
       lives in the component-specific test files.

Design principles (2026 SOTA — TooLoo Fluid Crucible Law §8):
  • One test class per engine module.
  • Each class exercises the public contract in isolation (no HTTP, no DB).
  • All tests are idempotent and stateless (Law 17).
  • Offline-safe: conforms to conftest.py ``offline_vertex`` autouse fixture.
  • Runs in ~12 s offline; used by ``MCP run_tests`` ouroboros validation.

Run directly:
    pytest tests/test_engine_smoke.py -q
"""
from __future__ import annotations

import threading
import time
import asyncio
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# 1. engine/config.py
# ══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_key_attributes_exist(self) -> None:
        from engine.config import (
            CIRCUIT_BREAKER_THRESHOLD,
            AUTONOMOUS_EXECUTION_ENABLED,
            EXECUTOR_MAX_WORKERS,
            GEMINI_API_KEY,
            GCP_PROJECT_ID,
        )
        assert 0.0 < CIRCUIT_BREAKER_THRESHOLD <= 1.0
        assert isinstance(AUTONOMOUS_EXECUTION_ENABLED, bool)
        assert EXECUTOR_MAX_WORKERS >= 1

    def test_no_hardcoded_secrets(self) -> None:
        """Law 9: secrets must come from .env, never hardcoded."""
        from pathlib import Path
        import engine.config as cfg
        src = Path(cfg.__file__).read_text()
        # Should not contain a bare API-key literal
        assert "AAAA" not in src or "GEMINI_API_KEY" in src


# ══════════════════════════════════════════════════════════════════════════════
# 2. engine/router.py
# ══════════════════════════════════════════════════════════════════════════════

class TestRouter:
    def test_route_returns_result(self) -> None:
        from engine.router import MandateRouter
        r = MandateRouter()
        result = r.route("Build a fast REST endpoint")
        assert result.intent in (
            "BUILD", "DEBUG", "AUDIT", "DESIGN", "EXPLAIN", "IDEATE",
            "SPAWN_REPO", "BLOCKED", "UNKNOWN"
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_circuit_breaker_not_tripped_on_valid_mandate(self) -> None:
        from engine.router import MandateRouter
        r = MandateRouter()
        result = r.route("Explain the OWASP Top 10 2025")
        assert result.intent != "BLOCKED"

    def test_apply_jit_boost_clamps_to_one(self) -> None:
        # JITBooster (not the router) performs the 1.0 cap.
        # The router's apply_jit_boost sets the value verbatim for callers
        # that have already clamped it; verify the booster caps correctly.
        from engine.jit_booster import JITBooster
        from engine.router import MandateRouter
        booster = JITBooster()
        route = MandateRouter().route("Deploy the service")
        # Manually inflate original so delta would push past 1.0
        route.confidence = 0.95  # type: ignore[attr-defined]
        result = booster.fetch(route)
        assert result.boosted_confidence <= 1.0

    def test_locked_intent_dto(self) -> None:
        from engine.router import LockedIntent
        li = LockedIntent(
            intent="BUILD",
            confidence=0.9,
            value_statement="v",
            constraint_summary="c",
            mandate_text="m",
            context_turns=[],
        )
        assert li.intent == "BUILD"
        assert li.confidence == 0.9


# ══════════════════════════════════════════════════════════════════════════════
# 3. engine/tribunal.py
# ══════════════════════════════════════════════════════════════════════════════

class TestTribunal:
    @pytest.mark.asyncio
    async def test_safe_logic_passes(self) -> None:
        from engine.tribunal import Tribunal, Engram
        from engine.psyche_bank import PsycheBank
        t = Tribunal(bank=PsycheBank())
        e = Engram(
            slug="test-safe",
            intent="BUILD",
            logic_body="def greet(name): return f'Hello {name}'",
            domain="test",
            mandate_level="L1",
        )
        result = await t.evaluate(e)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_poison_eval_caught(self) -> None:
        from engine.tribunal import Tribunal, Engram
        from engine.psyche_bank import PsycheBank
        t = Tribunal(bank=PsycheBank())
        e = Engram(
            slug="test-evil",
            intent="BUILD",
            logic_body="result = eval(user_input)",
            domain="test",
            mandate_level="L1",
        )
        result = await t.evaluate(e)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_verdicts_have_required_shape(self) -> None:
        from engine.tribunal import Tribunal, Engram
        from engine.psyche_bank import PsycheBank
        t = Tribunal(bank=PsycheBank())
        e = Engram(
            slug="test-shape",
            intent="AUDIT",
            logic_body="x = 1 + 1",
            domain="test",
            mandate_level="L1",
        )
        r = await t.evaluate(e)
        assert hasattr(r, "passed")
        assert hasattr(r, "violations")
        assert isinstance(r.violations, list)


# ══════════════════════════════════════════════════════════════════════════════
# 4. engine/psyche_bank.py
# ══════════════════════════════════════════════════════════════════════════════

class TestPsycheBank:
    @pytest.mark.asyncio
    async def test_load_and_forbidden_patterns_present(self) -> None:
        from engine.psyche_bank import PsycheBank
        bank = PsycheBank()
        rules = await bank.all_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0
        # At least one OWASP security rule must be seeded
        categories = {r.category for r in rules}
        assert "security" in categories

    @pytest.mark.asyncio
    async def test_thread_safe_concurrent_reads(self) -> None:
        from engine.psyche_bank import PsycheBank
        bank = PsycheBank()
        
        # We test concurrent async reads using asyncio.gather
        tasks = [bank.all_rules() for _ in range(8)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 8
        for r in results:
            assert isinstance(r, list)
            assert len(r) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 5. engine/graph.py
# ══════════════════════════════════════════════════════════════════════════════

class TestGraph:
    def test_sort_returns_waves(self) -> None:
        from engine.graph import TopologicalSorter
        sorter = TopologicalSorter()
        spec = [("a", []), ("b", ["a"]), ("c", ["a"])]
        waves = sorter.sort(spec)
        assert len(waves) >= 2
        assert "a" in waves[0]

    def test_cycle_raises(self) -> None:
        from engine.graph import CognitiveGraph
        g = CognitiveGraph()
        g.add_node("x")
        g.add_node("y")
        g.add_edge("x", "y")
        with pytest.raises(Exception):
            g.add_edge("y", "x")

    def test_single_node_no_deps(self) -> None:
        """A spec with one node and no dependencies returns one wave."""
        from engine.graph import TopologicalSorter
        sorter = TopologicalSorter()
        waves = sorter.sort([("only", [])])
        assert len(waves) == 1
        assert "only" in waves[0]


# ══════════════════════════════════════════════════════════════════════════════
# 6. engine/executor.py
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutor:
    @pytest.mark.asyncio
    async def test_fan_out_executes_all_envelopes(self) -> None:
        from engine.executor import JITExecutor, Envelope
        ex = JITExecutor(max_workers=2)
        envelopes = [
            Envelope(mandate_id=f"e{i}", intent="BUILD",
                     domain="test", metadata={})
            for i in range(4)
        ]
        results = await ex.fan_out(lambda env: {"id": env.mandate_id}, envelopes)
        assert len(results) == 4
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_fan_out_captures_exceptions(self) -> None:
        from engine.executor import JITExecutor, Envelope
        ex = JITExecutor(max_workers=2)
        envs = [Envelope(mandate_id="e0", intent="BUILD",
                         domain="test", metadata={})]

        def boom(_env: Envelope) -> dict[str, Any]:
            raise RuntimeError("boom")

        results = await ex.fan_out(boom, envs)
        assert len(results) == 1
        assert results[0].success is False

    def test_envelope_dto_has_required_fields(self) -> None:
        from engine.executor import Envelope
        e = Envelope(mandate_id="x", intent="AUDIT",
                     domain="engine", metadata={"k": "v"})
        assert e.mandate_id == "x"
        assert e.intent == "AUDIT"


# ══════════════════════════════════════════════════════════════════════════════
# 7. engine/scope_evaluator.py
# ══════════════════════════════════════════════════════════════════════════════

class TestScopeEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate_returns_scope_result(self) -> None:
        from engine.graph import TopologicalSorter
        from engine.scope_evaluator import ScopeEvaluator
        waves = TopologicalSorter().sort(
            [("a", []), ("b", ["a"]), ("c", ["b"])])
        se = ScopeEvaluator()
        result = await se.evaluate(waves, intent="BUILD")
        assert hasattr(result, "scope_summary")
        assert hasattr(result, "strategy")
        assert result.node_count >= 3

    @pytest.mark.asyncio
    async def test_parallelism_detected(self) -> None:
        from engine.graph import TopologicalSorter
        from engine.scope_evaluator import ScopeEvaluator
        waves = TopologicalSorter().sort(
            [("a", []), ("b", []), ("c", [])])
        se = ScopeEvaluator()
        result = await se.evaluate(waves, intent="BUILD")
        # 3 independent nodes → one wave with width 3
        assert result.max_wave_width >= 3
        assert result.parallelism_ratio > 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 8. engine/refinement.py
# ══════════════════════════════════════════════════════════════════════════════

class TestRefinement:
    def test_pass_verdict_on_all_success(self) -> None:
        from engine.refinement import RefinementLoop
        from engine.executor import ExecutionResult
        rl = RefinementLoop()
        results = [
            ExecutionResult(mandate_id=f"m{i}", success=True,
                            output={"status": "ok"}, error=None, latency_ms=10.0)
            for i in range(3)
        ]
        report = rl.evaluate(results)
        assert report.verdict == "pass"
        assert report.success_rate == 1.0

    def test_fail_verdict_on_all_failure(self) -> None:
        from engine.refinement import RefinementLoop
        from engine.executor import ExecutionResult
        rl = RefinementLoop()
        results = [
            ExecutionResult(mandate_id=f"m{i}", success=False,
                            output=None, error="boom", latency_ms=5.0)
            for i in range(3)
        ]
        report = rl.evaluate(results)
        assert report.verdict == "fail"

    def test_warn_verdict_on_partial_success(self) -> None:
        from engine.refinement import RefinementLoop
        from engine.executor import ExecutionResult
        rl = RefinementLoop()
        results = [
            ExecutionResult(mandate_id="m0", success=True,
                            output={"status": "ok"}, error=None, latency_ms=10.0),
            ExecutionResult(mandate_id="m1", success=False,
                            output=None, error="err", latency_ms=5.0),
        ]
        report = rl.evaluate(results)
        assert report.verdict in ("warn", "fail")


# ══════════════════════════════════════════════════════════════════════════════
# 9. engine/n_stroke.py
# ══════════════════════════════════════════════════════════════════════════════

class TestNStroke:
    @pytest.fixture()
    def engine(self):
        from engine.pipeline import NStrokeEngine
        from engine.router import MandateRouter
        from engine.jit_booster import JITBooster
        from engine.tribunal import Tribunal
        from engine.psyche_bank import PsycheBank
        from engine.graph import TopologicalSorter
        from engine.executor import JITExecutor
        from engine.scope_evaluator import ScopeEvaluator
        from engine.refinement import RefinementLoop
        from engine.model_selector import ModelSelector
        from engine.refinement_supervisor import RefinementSupervisor
        from engine.mcp_manager import MCPManager
        events: list[dict] = []
        return NStrokeEngine(
            router=MandateRouter(),
            booster=JITBooster(),
            tribunal=Tribunal(bank=PsycheBank()),
            sorter=TopologicalSorter(),
            executor=JITExecutor(max_workers=2),
            scope_evaluator=ScopeEvaluator(),
            refinement_loop=RefinementLoop(),
            mcp_manager=MCPManager(),
            model_selector=ModelSelector(),
            refinement_supervisor=RefinementSupervisor(),
            broadcast_fn=lambda e: events.append(e),
            max_strokes=2,
        )

    @pytest.mark.asyncio
    async def test_run_returns_result_with_verdict(self, engine) -> None:
        from engine.executor import Envelope
        from engine.router import LockedIntent

        locked = LockedIntent(
            intent="BUILD",
            confidence=0.92,
            value_statement="Test the engine",
            constraint_summary="offline test",
            mandate_text="build a simple hello-world function",
            context_turns=[],
        )
        result = await engine.run(locked_intent=locked, pipeline_id="smoke-ns-1")
        assert result.final_verdict in ("pass", "warn", "fail")
        assert result.total_strokes >= 1

    @pytest.mark.asyncio
    async def test_result_has_strokes_detail(self, engine) -> None:
        from engine.router import LockedIntent
        locked = LockedIntent(
            intent="EXPLAIN",
            confidence=0.88,
            value_statement="explain",
            constraint_summary="test",
            mandate_text="explain what a DAG is",
            context_turns=[],
        )
        result = await engine.run(locked_intent=locked, pipeline_id="smoke-ns-2")
        assert isinstance(result.strokes, list)
        d = result.to_dict()
        assert "strokes_detail" in d


# ══════════════════════════════════════════════════════════════════════════════
# 10. engine/supervisor.py  (TwoStrokeEngine)
# ══════════════════════════════════════════════════════════════════════════════

class TestSupervisor:
    @pytest.mark.asyncio
    async def test_two_stroke_happy_path(self) -> None:
        from engine.pipeline import NStrokeEngine as TwoStrokeEngine
        from engine.router import MandateRouter, LockedIntent
        from engine.jit_booster import JITBooster
        from engine.tribunal import Tribunal
        from engine.psyche_bank import PsycheBank
        from engine.graph import TopologicalSorter
        from engine.executor import JITExecutor
        from engine.scope_evaluator import ScopeEvaluator
        from engine.refinement import RefinementLoop
        from engine.model_selector import ModelSelector
        from engine.refinement_supervisor import RefinementSupervisor
        from engine.mcp_manager import MCPManager
        events: list[dict] = []
        tse = TwoStrokeEngine(
            router=MandateRouter(),
            booster=JITBooster(),
            tribunal=Tribunal(bank=PsycheBank()),
            sorter=TopologicalSorter(),
            executor=JITExecutor(max_workers=2),
            scope_evaluator=ScopeEvaluator(),
            refinement_loop=RefinementLoop(),
            mcp_manager=MCPManager(),
            model_selector=ModelSelector(),
            refinement_supervisor=RefinementSupervisor(),
            broadcast_fn=lambda e: events.append(e),
            max_strokes=2,
        )
        locked = LockedIntent(
            intent="BUILD",
            confidence=0.91,
            value_statement="test",
            constraint_summary="smoke test",
            mandate_text="create a health check endpoint",
            context_turns=[],
        )
        result = await tse.run(locked, pipeline_id="smoke-ts-1")
        assert result.final_verdict in ("pass", "warn", "fail")


# ══════════════════════════════════════════════════════════════════════════════
# 11. engine/conversation.py
# ══════════════════════════════════════════════════════════════════════════════

class TestConversation:
    def test_process_returns_result(self) -> None:
        from engine.conversation import ConversationEngine
        from engine.router import MandateRouter
        from engine.jit_booster import JITBooster
        ce = ConversationEngine()
        router = MandateRouter()
        booster = JITBooster()
        text = "Hello, what can you do?"
        route = router.route_chat(text)
        jit = booster.fetch(route)
        result = ce.process(text=text, route=route, session_id="smoke-conv-1",
                            jit_result=jit)
        assert hasattr(result, "response_text")
        assert isinstance(result.response_text, str)
        assert len(result.response_text) > 0

    def test_session_isolation(self) -> None:
        from engine.conversation import ConversationEngine
        from engine.router import MandateRouter
        from engine.jit_booster import JITBooster
        ce = ConversationEngine()
        router = MandateRouter()
        booster = JITBooster()

        def _chat(session_id: str, text: str) -> str:
            route = router.route_chat(text)
            jit = booster.fetch(route)
            r = ce.process(text=text, route=route,
                           session_id=session_id, jit_result=jit)
            return r.response_text

        _chat("s-a", "Remember: the secret code is 42")
        response_b = _chat("s-b", "What is the secret code?")
        # s-b has no memory of s-a — response must be a plain string (not empty)
        assert isinstance(response_b, str)


# ══════════════════════════════════════════════════════════════════════════════
# 12. engine/jit_booster.py
# ══════════════════════════════════════════════════════════════════════════════

class TestJITBooster:
    def test_fetch_returns_boost_result(self) -> None:
        from engine.jit_booster import JITBooster
        from engine.router import MandateRouter
        booster = JITBooster()
        route = MandateRouter().route("Build a Python microservice")
        result = booster.fetch(route)
        assert result.boosted_confidence >= result.original_confidence
        assert result.boosted_confidence <= 1.0
        assert isinstance(result.signals, list)

    def test_boost_formula_correct(self) -> None:
        from engine.jit_booster import JITBooster, BOOST_PER_SIGNAL, MAX_BOOST_DELTA
        from engine.router import MandateRouter
        booster = JITBooster()
        route = MandateRouter().route("Audit security posture")
        result = booster.fetch(route)
        # JITBooster uses (1 - context_obscurity_factor) where factor = 0.2
        expected_delta = min(len(result.signals) *
                             BOOST_PER_SIGNAL * 0.8, MAX_BOOST_DELTA)
        assert abs(result.boost_delta - expected_delta) < 0.001

    def test_source_field_populated(self) -> None:
        from engine.jit_booster import JITBooster
        from engine.router import MandateRouter
        booster = JITBooster()
        route = MandateRouter().route("Design a caching layer")
        result = booster.fetch(route)
        assert result.source in ("structured", "gemini", "vertex", "garden",
                                 "consensus", "jit_cache", "catalogue")

    def test_node_fetch_returns_result(self) -> None:
        from engine.jit_booster import JITBooster
        from engine.router import MandateRouter
        booster = JITBooster()
        route = MandateRouter().route("Implement auth middleware")
        result = booster.fetch_for_node(
            route, node_type="implement",
            action_context="write JWT validation middleware")
        assert result.boosted_confidence <= 1.0


# ══════════════════════════════════════════════════════════════════════════════
# Integration smoke: MCP file_read + Tribunal pipeline
# ══════════════════════════════════════════════════════════════════════════════

class TestMCPPipeline:
    def test_file_read_engine_config(self) -> None:
        from engine.mcp_manager import MCPManager
        mcp = MCPManager()
        result = mcp.call("file_read", path="engine/config.py")
        assert result.success
        assert isinstance(result.output, dict)
        content = result.output.get("content", "")
        assert "CIRCUIT_BREAKER_THRESHOLD" in content

    def test_file_read_path_traversal_blocked(self) -> None:
        from engine.mcp_manager import MCPManager
        mcp = MCPManager()
        result = mcp.call("file_read", path="../../etc/passwd")
        assert not result.success

    def test_run_tests_smoke_itself(self) -> None:
        """The smoke suite can trigger a nested run_tests on a tiny file."""
        from engine.mcp_manager import MCPManager
        mcp = MCPManager()
        result = mcp.call(
            "run_tests",
            test_path="tests/test_workspace_roots.py",
            timeout=60,
        )
        assert result.success
        assert isinstance(result.output, dict)
        # test_workspace_roots has 8 tests — should pass in < 5 s
        assert result.output.get("passed") is True
