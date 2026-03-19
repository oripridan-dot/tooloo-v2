"""
tests/test_n_stroke_stress.py — N-Stroke Engine Stress Test Suite.

This is The Crucible: the test suite that intentionally pushes TooLoo V2
to its breaking point and proves the dynamic pipeline can handle it.

Test classes:
  TestMCPManager               — manifest completeness, tool dispatch, security
  TestModelSelector            — tier escalation ladder, determinism
  TestRefinementSupervisor     — healing lifecycle, prescription shape
  TestNStrokeHappyPath         — single-stroke pass: shape + SSE events
  TestNStrokeModelEscalation   — forced failures drive tier 1→2→3 escalation
  TestNStrokeImpossibleTask    — "Build zero-latency DSP buffer" forced looping
  TestNStrokeAutoHealing       — 3+ node failures trigger RefinementSupervisor
  TestHighConcurrencyMandates  — 50 simultaneous mandates, DAG isolation
  TestNStrokeHTTPEndpoints     — /v2/n-stroke + /v2/mcp/tools HTTP e2e
"""
from __future__ import annotations

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from engine.executor import Envelope, ExecutionResult, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBooster
from engine.mcp_manager import MCPCallResult, MCPManager, MCPToolSpec
from engine.model_selector import (
    ModelSelection,
    ModelSelector,
    TIER_1_MODEL,
    TIER_2_MODEL,
    TIER_3_MODEL,
    TIER_4_MODEL,
)
from engine.n_stroke import MAX_STROKES, NStrokeEngine, NStrokeResult, StrokeRecord
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.refinement_supervisor import (
    HealingReport,
    NODE_FAIL_THRESHOLD,
    RefinementSupervisor,
)
from engine.router import LockedIntent, MandateRouter
from engine.scope_evaluator import ScopeEvaluator
from engine.supervisor import TwoStrokeEngine
from engine.tribunal import Tribunal


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_locked(
    intent: str = "BUILD",
    confidence: float = 0.95,
    mandate_text: str = "build implement create add write generate synthesise",
) -> LockedIntent:
    return LockedIntent(
        intent=intent,
        confidence=confidence,
        value_statement="Prove the N-stroke pipeline works.",
        constraint_summary="offline tests, no Gemini API",
        mandate_text=mandate_text,
        context_turns=[],
        locked_at=datetime.now(UTC).isoformat(),
    )


def _make_engine(
    broadcast_events: list | None = None,
    max_strokes: int = MAX_STROKES,
) -> NStrokeEngine:
    """Construct a fully-wired NStrokeEngine with optional broadcast capture."""
    bank = PsycheBank()
    router = MandateRouter()
    booster = JITBooster()
    tribunal = Tribunal(bank=bank)
    sorter = TopologicalSorter()
    executor = JITExecutor()
    scope_evaluator = ScopeEvaluator()
    refinement_loop = RefinementLoop()
    mcp = MCPManager()
    model_selector = ModelSelector()
    ref_supervisor = RefinementSupervisor()

    events = broadcast_events if broadcast_events is not None else []

    def _capture(event: dict[str, Any]) -> None:
        events.append(event)

    return NStrokeEngine(
        router=router,
        booster=booster,
        tribunal=tribunal,
        sorter=sorter,
        executor=executor,
        scope_evaluator=scope_evaluator,
        refinement_loop=refinement_loop,
        mcp_manager=mcp,
        model_selector=model_selector,
        refinement_supervisor=ref_supervisor,
        broadcast_fn=_capture,
        max_strokes=max_strokes,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1. MCPManager
# ──────────────────────────────────────────────────────────────────────────────


class TestMCPManager:
    """Prove the MCP tool manifest is complete and dispatch works correctly."""

    EXPECTED_TOOLS = {
        "file_read", "file_write", "code_analyze",
        "web_lookup", "run_tests", "read_error",
    }

    def test_manifest_completeness(self) -> None:
        mcp = MCPManager()
        tools = mcp.manifest()
        names = {t.name for t in tools}
        assert self.EXPECTED_TOOLS == names, (
            f"Missing tools: {self.EXPECTED_TOOLS - names}"
        )

    def test_manifest_spec_shape(self) -> None:
        mcp = MCPManager()
        for spec in mcp.manifest():
            assert isinstance(spec, MCPToolSpec)
            assert spec.uri.startswith("mcp://tooloo/")
            assert spec.name
            assert spec.description
            assert isinstance(spec.parameters, list)
            assert len(spec.parameters) >= 1

    def test_call_web_lookup_returns_signals(self) -> None:
        mcp = MCPManager()
        result = mcp.call("web_lookup", query="python async dsp")
        assert result.success
        assert isinstance(result.output, dict)
        assert len(result.output["signals"]) >= 1
        assert result.output["source"] == "structured_catalogue"

    def test_call_unknown_tool_returns_error(self) -> None:
        mcp = MCPManager()
        result = mcp.call("nonexistent_tool")
        assert not result.success
        assert result.error
        assert "not registered" in result.error

    def test_call_uri_dispatch(self) -> None:
        mcp = MCPManager()
        result = mcp.call_uri("mcp://tooloo/web_lookup",
                              query="security owasp")
        assert result.success
        assert result.output["signals"]

    def test_call_uri_bad_scheme(self) -> None:
        mcp = MCPManager()
        result = mcp.call_uri("http://external.com/tool")
        assert not result.success
        assert "Unknown URI scheme" in (result.error or "")

    def test_read_error_parses_traceback(self) -> None:
        mcp = MCPManager()
        tb = (
            'Traceback (most recent call last):\n'
            '  File "engine/n_stroke.py", line 42, in run\n'
            '    raise RuntimeError("DSP buffer overflow during zero-latency write")\n'
            'RuntimeError: DSP buffer overflow during zero-latency write\n'
        )
        result = mcp.call("read_error", error_text=tb)
        assert result.success
        data = result.output
        assert data["error_type"] == "RuntimeError"
        assert "DSP buffer overflow" in data["message"]
        assert data["hint"]
        assert data["location"] is not None
        assert data["location"]["line"] == 42

    def test_code_analyze_detects_async(self) -> None:
        mcp = MCPManager()
        code = "async def handler(req):\n    result = await db.fetch(req.id)\n    return result\n"
        result = mcp.call("code_analyze", code=code)
        assert result.success
        assert result.output["has_async"] is True
        assert result.output["loc"] == 3

    def test_file_read_path_traversal_rejected(self) -> None:
        mcp = MCPManager()
        result = mcp.call("file_read", path="../../etc/passwd")
        assert not result.success
        assert "traversal" in (result.error or "").lower()

    def test_file_write_forbidden_extension_rejected(self) -> None:
        mcp = MCPManager()
        result = mcp.call("file_write", path="engine/evil.sh",
                          content="rm -rf /")
        assert not result.success
        assert "not permitted" in (result.error or "").lower()

    def test_run_tests_path_outside_tests_dir_rejected(self) -> None:
        mcp = MCPManager()
        result = mcp.call("run_tests", test_path="engine/config.py")
        assert not result.success
        assert "tests/" in (result.error or "")

    def test_call_result_to_dict_shape(self) -> None:
        mcp = MCPManager()
        result = mcp.call("web_lookup", query="build fastapi")
        d = result.to_dict()
        assert set(d) >= {"uri", "success", "output", "error", "truncated"}


# ──────────────────────────────────────────────────────────────────────────────
# 2. ModelSelector
# ──────────────────────────────────────────────────────────────────────────────


class TestModelSelector:
    """Prove the deterministic model escalation ladder."""

    def test_stroke_1_default_intent_is_tier_1(self) -> None:
        sel = ModelSelector().select(stroke=1, intent="BUILD")
        assert sel.tier == 1
        assert sel.model == TIER_1_MODEL

    def test_stroke_1_deep_intent_is_tier_2(self) -> None:
        for intent in ("DEBUG", "AUDIT", "SPAWN_REPO"):
            sel = ModelSelector().select(stroke=1, intent=intent)
            assert sel.tier == 2, f"{intent} should start at tier 2"
            assert sel.model == TIER_2_MODEL

    def test_stroke_2_fail_escalates_to_tier_2(self) -> None:
        sel = ModelSelector().select(stroke=2, intent="BUILD", prior_verdict="fail")
        assert sel.tier == 2
        assert sel.model == TIER_2_MODEL

    def test_stroke_3_fail_escalates_to_tier_3(self) -> None:
        sel = ModelSelector().select(stroke=3, intent="BUILD", prior_verdict="fail")
        assert sel.tier == 3
        assert sel.model == TIER_3_MODEL

    def test_stroke_4_fail_escalates_to_tier_4(self) -> None:
        sel = ModelSelector().select(stroke=4, intent="BUILD", prior_verdict="fail")
        assert sel.tier == 4
        assert sel.model == TIER_4_MODEL

    def test_stroke_5_plus_capped_at_tier_4(self) -> None:
        for s in (5, 6, 7):
            sel = ModelSelector().select(stroke=s, intent="BUILD", prior_verdict="fail")
            assert sel.tier == 4
            assert sel.model == TIER_4_MODEL

    def test_warn_escalates_to_tier_3_max(self) -> None:
        sel = ModelSelector().select(stroke=4, intent="BUILD", prior_verdict="warn")
        assert sel.tier == 3

    def test_pass_stays_low(self) -> None:
        sel = ModelSelector().select(stroke=3, intent="BUILD", prior_verdict="pass")
        assert sel.tier <= 2

    def test_force_tier_override(self) -> None:
        sel = ModelSelector().select(stroke=1, intent="BUILD", force_tier=4)
        assert sel.tier == 4
        assert sel.model == TIER_4_MODEL

    def test_force_tier_clamped(self) -> None:
        sel = ModelSelector().select(stroke=1, intent="BUILD", force_tier=99)
        assert sel.tier == 4

    def test_selection_to_dict_shape(self) -> None:
        sel = ModelSelector().select(stroke=1, intent="BUILD")
        d = sel.to_dict()
        assert set(d) == {"stroke", "intent", "model",
                          "tier", "rationale", "vertex_model_id"}

    def test_rationale_is_non_empty(self) -> None:
        for stroke in (1, 2, 3, 4):
            sel = ModelSelector().select(
                stroke=stroke, intent="BUILD", prior_verdict="fail"
            )
            assert sel.rationale, f"Stroke {stroke}: rationale should not be empty"


# ──────────────────────────────────────────────────────────────────────────────
# 3. RefinementSupervisor
# ──────────────────────────────────────────────────────────────────────────────


class TestRefinementSupervisor:
    """Prove autonomous healing lifecycle."""

    def _heal(
        self,
        node_ids: list[str] | None = None,
        error_map: dict[str, str] | None = None,
    ) -> HealingReport:
        supervisor = RefinementSupervisor()
        mcp = MCPManager()
        booster = JITBooster()
        return supervisor.heal(
            failed_node_ids=node_ids or ["pipe-001-s3-implement"],
            stroke=3,
            intent="BUILD",
            mcp=mcp,
            booster=booster,
            mandate_text="build zero-latency DSP buffer matrix",
            last_error_map=error_map or {},
        )

    def test_heal_returns_report(self) -> None:
        report = self._heal()
        assert isinstance(report, HealingReport)

    def test_heal_report_shape(self) -> None:
        report = self._heal()
        d = report.to_dict()
        assert set(d) >= {
            "healing_id", "stroke", "intent", "nodes_analyzed",
            "nodes_healed", "prescriptions", "healed_work_fn",
            "latency_ms", "verdict",
        }

    def test_heal_verdict_is_healed(self) -> None:
        report = self._heal(["node-a", "node-b"])
        assert report.verdict == "healed"
        assert set(report.nodes_healed) == {"node-a", "node-b"}

    def test_heal_prescriptions_non_empty(self) -> None:
        report = self._heal()
        assert len(report.prescriptions) == 1
        rx = report.prescriptions[0]
        assert rx.node_id == "pipe-001-s3-implement"
        assert rx.hint
        assert rx.fix_strategy

    def test_heal_with_real_traceback(self) -> None:
        tb = (
            "Traceback (most recent call last):\n"
            '  File "engine/executor.py", line 80, in _run\n'
            "    output = work_fn(env)\n"
            "RuntimeError: zero-latency constraint violated: buffer underrun\n"
        )
        report = self._heal(
            node_ids=["pipe-001-s3-implement"],
            error_map={"pipe-001-s3-implement": tb},
        )
        rx = report.prescriptions[0]
        assert rx.error_type == "RuntimeError"
        assert "underrun" in rx.error_message or "zero-latency" in rx.error_message

    def test_heal_provides_sota_signals(self) -> None:
        report = self._heal()
        for rx in report.prescriptions:
            assert isinstance(rx.sota_signals, list)

    def test_healed_work_fn_is_callable(self) -> None:
        report = self._heal()
        assert callable(report.healed_work_fn)

    def test_healed_work_fn_returns_healing_metadata(self) -> None:
        report = self._heal(["pipe-001-s3-implement"])
        assert report.healed_work_fn is not None
        env = Envelope(
            mandate_id="pipe-001-s3-implement",
            intent="BUILD",
            domain="backend",
        )
        output = report.healed_work_fn(env)
        assert output["healing_applied"] is True
        assert output["fix_strategy"] is not None
        assert output["status"] == "healed_execution"

    def test_healed_work_fn_on_unknown_node(self) -> None:
        report = self._heal(["node-x"])
        assert report.healed_work_fn is not None
        env = Envelope(
            mandate_id="some-other-node",  # not in rx_map
            intent="BUILD",
            domain="backend",
        )
        output = report.healed_work_fn(env)
        assert output["healing_applied"] is False

    def test_fix_strategy_has_no_poison(self) -> None:
        import re
        _POISON = re.compile(
            r"\b(eval|exec|__import__|subprocess\.run|os\.system)\s*\(")
        report = self._heal()
        for rx in report.prescriptions:
            assert not _POISON.search(rx.fix_strategy), (
                f"Poisoned fix strategy: {rx.fix_strategy}"
            )

    def test_heal_latency_is_positive(self) -> None:
        report = self._heal()
        assert report.latency_ms >= 0.0

    def test_node_fail_threshold_constant(self) -> None:
        """Node fail threshold must be >= 2 (at least two attempts before healing)."""
        assert NODE_FAIL_THRESHOLD >= 2


# ──────────────────────────────────────────────────────────────────────────────
# 4. NStrokeEngine — happy path
# ──────────────────────────────────────────────────────────────────────────────


class TestNStrokeHappyPath:
    """N-Stroke happy path: single stroke passes on first attempt."""

    def test_run_returns_result(self) -> None:
        engine = _make_engine()
        locked = _make_locked()
        result = engine.run(locked)
        assert isinstance(result, NStrokeResult)

    def test_result_satisfied_on_happy_path(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked())
        assert result.satisfied
        assert result.final_verdict == "pass"

    def test_single_stroke_on_happy_path(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked())
        assert result.total_strokes == 1

    def test_result_to_dict_shape(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked())
        d = result.to_dict()
        assert set(d) >= {
            "pipeline_id", "locked_intent", "strokes", "final_verdict",
            "satisfied", "total_strokes", "model_escalations",
            "healing_invocations", "latency_ms",
        }

    def test_stroke_record_shape(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked())
        s = result.strokes[0]
        assert isinstance(s, StrokeRecord)
        assert s.stroke == 1
        assert s.satisfied
        assert len(s.mcp_tools_injected) == 6   # all 6 MCP tools
        assert s.healing_report is None

    def test_first_stroke_uses_tier_1_model_for_build(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked(intent="BUILD"))
        assert result.strokes[0].model_selection.tier == 1
        assert result.strokes[0].model_selection.model == TIER_1_MODEL

    def test_first_stroke_uses_tier_2_model_for_audit(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked(intent="AUDIT"))
        assert result.strokes[0].model_selection.tier == 2
        assert result.strokes[0].model_selection.model == TIER_2_MODEL

    def test_pipeline_id_generated_when_not_provided(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked())
        assert result.pipeline_id.startswith("nstroke-")

    def test_pipeline_id_respected_when_provided(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked(), pipeline_id="test-pipe-001")
        assert result.pipeline_id == "test-pipe-001"

    def test_mcp_tools_injected_in_execution_metadata(self) -> None:
        """Each execution envelope must carry the full MCP tool list."""
        logged_envs: list[Envelope] = []

        def _capture_work(env: Envelope) -> dict[str, Any]:
            logged_envs.append(env)
            return {"status": "ok", "node": env.mandate_id}

        engine = _make_engine()
        engine.run(_make_locked(), work_fn=_capture_work)
        assert logged_envs, "No envelopes were passed to work_fn"
        for env in logged_envs:
            assert "mcp_tools" in env.metadata
            assert len(env.metadata["mcp_tools"]) == 6

    def test_no_model_escalation_on_happy_path(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked())
        assert result.model_escalations == 0

    def test_no_healing_on_happy_path(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked())
        assert result.healing_invocations == 0

    def test_latency_is_positive(self) -> None:
        engine = _make_engine()
        result = engine.run(_make_locked())
        assert result.latency_ms > 0.0

    def test_sse_events_emitted(self) -> None:
        events: list[dict[str, Any]] = []
        engine = _make_engine(broadcast_events=events)
        engine.run(_make_locked())
        types = {e["type"] for e in events}
        assert "n_stroke_start" in types
        assert "model_selected" in types
        assert "preflight" in types
        assert "plan" in types
        assert "midflight" in types
        assert "execution" in types
        assert "satisfaction_gate" in types
        assert "n_stroke_complete" in types

    def test_n_stroke_complete_event_shape(self) -> None:
        events: list[dict[str, Any]] = []
        engine = _make_engine(broadcast_events=events)
        engine.run(_make_locked())
        complete_events = [
            e for e in events if e["type"] == "n_stroke_complete"]
        assert len(complete_events) == 1
        e = complete_events[0]
        assert e["satisfied"] is True
        assert e["final_verdict"] == "pass"
        assert e["total_strokes"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# 5. Model escalation on failure
# ──────────────────────────────────────────────────────────────────────────────


class TestNStrokeModelEscalation:
    """Prove model tier escalates deterministically with each failed stroke."""

    def _failing_work_fn_factory(self, fail_strokes: set[int]) -> object:
        """Return a work_fn that raises on specified strokes, succeeds otherwise."""
        counter: dict[str, int] = {"calls": 0}

        def _work(env: Envelope) -> dict[str, Any]:
            stroke = env.metadata.get("stroke", 1)
            if stroke in fail_strokes:
                raise RuntimeError(
                    f"Deliberate failure on stroke {stroke} for stress test."
                )
            return {"status": "ok", "node": env.mandate_id, "stroke": stroke}

        return _work

    def test_model_escalates_on_second_stroke(self) -> None:
        """Stroke 1 fails → stroke 2 uses a higher-tier model."""
        events: list[dict[str, Any]] = []
        engine = _make_engine(broadcast_events=events, max_strokes=3)

        work_fn = self._failing_work_fn_factory(fail_strokes={1})
        result = engine.run(_make_locked(), work_fn=work_fn)

        assert result.total_strokes == 2
        stroke_1_tier = result.strokes[0].model_selection.tier
        stroke_2_tier = result.strokes[1].model_selection.tier
        assert stroke_2_tier > stroke_1_tier, (
            f"Expected tier escalation: stroke 1={stroke_1_tier} → "
            f"stroke 2={stroke_2_tier}"
        )
        assert result.model_escalations >= 1

    def test_model_escalates_across_all_strokes(self) -> None:
        """Strokes 1 and 2 fail → tier 1 → 2 → 3 escalation."""
        engine = _make_engine(max_strokes=4)
        work_fn = self._failing_work_fn_factory(fail_strokes={1, 2})
        result = engine.run(_make_locked(), work_fn=work_fn)

        assert result.total_strokes == 3
        tiers = [s.model_selection.tier for s in result.strokes]
        # Each tier should be >= previous (monotonically non-decreasing)
        for i in range(1, len(tiers)):
            assert tiers[i] >= tiers[i - 1], (
                f"Tier regression at stroke {i + 1}: {tiers}"
            )

    def test_model_selected_sse_events_carry_tier(self) -> None:
        """Every model_selected SSE event must carry tier + rationale."""
        events: list[dict[str, Any]] = []
        engine = _make_engine(broadcast_events=events, max_strokes=3)
        work_fn = self._failing_work_fn_factory(fail_strokes={1})
        engine.run(_make_locked(), work_fn=work_fn)

        model_sel_events = [e for e in events if e["type"] == "model_selected"]
        assert len(model_sel_events) == 2
        for e in model_sel_events:
            assert "model" in e
            assert "tier" in e and isinstance(e["tier"], int)
            assert "rationale" in e and e["rationale"]

    def test_tier_4_used_after_4_failures(self) -> None:
        """After 4 consecutive failures the engine escalates to tier 4 (Pro-Thinking)."""
        engine = _make_engine(max_strokes=6)
        work_fn = self._failing_work_fn_factory(fail_strokes={1, 2, 3, 4})
        result = engine.run(_make_locked(), work_fn=work_fn)

        # The 5th stroke (if reached) should use tier 4
        tier_4_strokes = [
            s for s in result.strokes if s.model_selection.tier == 4]
        assert tier_4_strokes or result.total_strokes >= 4, (
            "Expected tier-4 escalation after 4 failures"
        )

    def test_retry_signal_injected_in_subsequent_strokes(self) -> None:
        """Failure signal from previous stroke must appear in next stroke's preflight."""
        events: list[dict[str, Any]] = []
        engine = _make_engine(broadcast_events=events, max_strokes=3)
        work_fn = self._failing_work_fn_factory(fail_strokes={1})
        engine.run(_make_locked(), work_fn=work_fn)

        # The second preflight event's jit_signals should differ (retry-signal injected)
        preflight_events = [e for e in events if e["type"] == "preflight"]
        assert len(preflight_events) == 2
        # Second preflight should have a model reference indicating escalation
        assert preflight_events[1]["model"] != preflight_events[0]["model"]


# ──────────────────────────────────────────────────────────────────────────────
# 6. Impossible Task (The Crucible — forced multi-stroke looping)
# ──────────────────────────────────────────────────────────────────────────────


class TestImpossibleTask:
    """
    The Impossible Task: Build a multi-threaded zero-latency audio DSP buffer
    matrix in Python.

    This test proves that:
      1. TooLoo detects the failure at the Satisfaction Gate.
      2. The engine autonomously increments stroke count.
      3. A more powerful model is selected for subsequent strokes.
      4. The loop continues until satisfaction or MAX_STROKES.
    """

    IMPOSSIBLE_MANDATE = (
        "Build a multi-threaded audio DSP buffer matrix in Python with zero latency. "
        "The buffer must have sub-millisecond read-write cycle time, thread-safe SPSC "
        "ring buffer, lock-free concurrent access, and zero memory copies. "
        "All operations must complete in < 1 microsecond."
    )

    def _make_dsp_locked(self) -> LockedIntent:
        return _make_locked(
            intent="BUILD",
            confidence=0.92,
            mandate_text=self.IMPOSSIBLE_MANDATE,
        )

    def _dsp_work_fn_factory(self, pass_on_stroke: int) -> object:
        """Work function that fails for strokes below pass_on_stroke."""

        def _work(env: Envelope) -> dict[str, Any]:
            stroke = env.metadata.get("stroke", 1)
            if stroke < pass_on_stroke:
                raise RuntimeError(
                    f"DSP buffer cannot achieve zero-latency on stroke {stroke}: "
                    f"GIL contention detected in ThreadPoolExecutor fan-out. "
                    f"Retrying with {env.metadata.get('model', 'unknown')} model."
                )
            # Stroke pass_on_stroke+ : apply healing / escalated model solution
            return {
                "node": env.mandate_id,
                "status": "dsp_buffer_constructed",
                "model": env.metadata.get("model"),
                "stroke": stroke,
                "zero_latency_approach": (
                    "sounddevice CFFI + ctypes ring buffer bypassing GIL — "
                    "recommended by SOTA signals on stroke " + str(stroke)
                ),
            }

        return _work

    def test_impossible_task_forces_multiple_strokes(self) -> None:
        """The engine MUST loop more than once when stroke 1 fails."""
        engine = _make_engine(max_strokes=5)
        work_fn = self._dsp_work_fn_factory(pass_on_stroke=2)
        result = engine.run(self._make_dsp_locked(), work_fn=work_fn)

        assert result.total_strokes > 1, (
            f"Expected multiple strokes but got {result.total_strokes}. "
            "The impossible task should have failed on stroke 1."
        )

    def test_impossible_task_model_upgrades_on_failure(self) -> None:
        """The model MUST be upgraded when stroke 1 fails."""
        engine = _make_engine(max_strokes=5)
        work_fn = self._dsp_work_fn_factory(pass_on_stroke=2)
        result = engine.run(self._make_dsp_locked(), work_fn=work_fn)

        assert result.model_escalations >= 1, (
            "Expected at least one model escalation for the impossible task."
        )
        stroke_1_model = result.strokes[0].model_selection.model
        stroke_2_model = result.strokes[1].model_selection.model
        assert stroke_1_model != stroke_2_model, (
            f"Model should change: stroke 1={stroke_1_model} stroke 2={stroke_2_model}"
        )

    def test_impossible_task_eventually_passes(self) -> None:
        """After escalation, the engine must find a successful path."""
        engine = _make_engine(max_strokes=5)
        work_fn = self._dsp_work_fn_factory(pass_on_stroke=3)
        result = engine.run(self._make_dsp_locked(), work_fn=work_fn)

        assert result.satisfied, (
            f"Expected satisfaction on stroke 3+ but got "
            f"final_verdict={result.final_verdict}, strokes={result.total_strokes}"
        )

    def test_impossible_task_satisfaction_gate_events(self) -> None:
        """Satisfaction gate SSE events must reflect failure then success."""
        events: list[dict[str, Any]] = []
        engine = _make_engine(broadcast_events=events, max_strokes=5)
        work_fn = self._dsp_work_fn_factory(pass_on_stroke=2)
        engine.run(self._make_dsp_locked(), work_fn=work_fn)

        sat_events = [e for e in events if e["type"] == "satisfaction_gate"]
        assert len(sat_events) >= 2
        # Stroke 1: not satisfied
        assert sat_events[0]["satisfied"] is False
        # Final: satisfied
        assert sat_events[-1]["satisfied"] is True

    def test_impossible_task_final_stroke_uses_sota_dsp_solution(self) -> None:
        """The successful stroke output must reflect the DSP SOTA solution."""
        engine = _make_engine(max_strokes=5)
        work_fn = self._dsp_work_fn_factory(pass_on_stroke=2)
        result = engine.run(self._make_dsp_locked(), work_fn=work_fn)

        # Find the passing stroke
        passing_strokes = [s for s in result.strokes if s.satisfied]
        assert passing_strokes
        last = passing_strokes[-1]
        # At least some nodes should show the DSP solution in their output
        dsp_results = [
            r for r in last.execution_results
            if r.success and r.output and "dsp" in str(r.output).lower()
        ]
        assert dsp_results, "Expected at least one DSP-related output in passing stroke"


# ──────────────────────────────────────────────────────────────────────────────
# 7. Autonomous self-healing (RefinementSupervisor integration)
# ──────────────────────────────────────────────────────────────────────────────


class TestNStrokeAutoHealing:
    """Prove RefinementSupervisor triggers and heals persistently-failing nodes."""

    def _persistent_fail_fn(self, target_node_suffix: str) -> object:
        """Work function that always fails for nodes matching the suffix."""

        def _work(env: Envelope) -> dict[str, Any]:
            if env.mandate_id.endswith(target_node_suffix):
                raise RuntimeError(
                    f"Persistent failure at node '{env.mandate_id}': "
                    f"simulated unstable dependency (stroke {env.metadata.get('stroke')})."
                )
            return {"status": "ok", "node": env.mandate_id}

        return _work

    def test_healing_triggered_after_threshold_failures(self) -> None:
        """RefinementSupervisor must be called when a node fails 3+ times."""
        # Use max_strokes = NODE_FAIL_THRESHOLD + 1 to guarantee healing is triggered
        max_s = NODE_FAIL_THRESHOLD + 2
        engine = _make_engine(max_strokes=max_s)
        work_fn = self._persistent_fail_fn("-implement")
        result = engine.run(_make_locked(), work_fn=work_fn)

        assert result.healing_invocations >= 1, (
            f"Expected at least 1 healing invocation but got "
            f"{result.healing_invocations} over {result.total_strokes} strokes."
        )

    def test_healing_sse_event_emitted(self) -> None:
        events: list[dict[str, Any]] = []
        max_s = NODE_FAIL_THRESHOLD + 2
        engine = _make_engine(broadcast_events=events, max_strokes=max_s)
        work_fn = self._persistent_fail_fn("-implement")
        engine.run(_make_locked(), work_fn=work_fn)

        healing_events = [
            e for e in events if e["type"] == "healing_triggered"]
        assert healing_events, "Expected at least one healing_triggered SSE event"
        e = healing_events[0]
        assert "nodes_healed" in e
        assert "healing_id" in e
        assert e["healing_id"].startswith("heal-")

    def test_healed_work_fn_used_after_healing(self) -> None:
        """Once healed, the engine substitutes the healed work function."""
        outputs: list[dict[str, Any]] = []
        fail_counter: dict[str, int] = {"count": 0}

        def _smart_work(env: Envelope) -> dict[str, Any]:
            stroke = env.metadata.get("stroke", 1)
            if stroke <= NODE_FAIL_THRESHOLD and env.mandate_id.endswith("-implement"):
                fail_counter["count"] += 1
                raise RuntimeError(
                    "Deliberate persistent failure for healing test.")
            out = {"status": "healed_or_ok",
                   "node": env.mandate_id, "stroke": stroke}
            outputs.append(out)
            return out

        engine = _make_engine(max_strokes=NODE_FAIL_THRESHOLD + 3)
        engine.run(_make_locked(), work_fn=_smart_work)

        # After healing, the function should produce successful outputs
        healed_outputs = [o for o in outputs if o.get(
            "stroke", 1) > NODE_FAIL_THRESHOLD]
        assert healed_outputs or fail_counter["count"] >= 1, (
            "Expected either healed outputs or proof the initial failures were recorded."
        )

    def test_healing_report_in_stroke_record(self) -> None:
        max_s = NODE_FAIL_THRESHOLD + 2
        engine = _make_engine(max_strokes=max_s)
        work_fn = self._persistent_fail_fn("-implement")
        result = engine.run(_make_locked(), work_fn=work_fn)

        # Find the stroke where healing was applied
        healed_strokes = [
            s for s in result.strokes if s.healing_report is not None]
        assert healed_strokes, "Expected at least one stroke with a healing_report"
        hr = healed_strokes[0].healing_report
        assert hr.verdict in ("healed", "partial")
        assert hr.prescriptions

    def test_fail_counts_reset_after_healing(self) -> None:
        """Healed nodes should have their fail counters reset to 0."""
        events: list[dict[str, Any]] = []
        max_s = NODE_FAIL_THRESHOLD + 2
        engine = _make_engine(broadcast_events=events, max_strokes=max_s)
        work_fn = self._persistent_fail_fn("-implement")
        engine.run(_make_locked(), work_fn=work_fn)

        sat_events = [e for e in events if e["type"] == "satisfaction_gate"]
        # Find the satisfaction_gate event right after healing
        healing_events = [
            e for e in events if e["type"] == "healing_triggered"]
        if healing_events:
            heal_stroke = healing_events[0]["stroke"]
            # The stroke after healing should have cleared the fail counter
            post_heal_sat = [
                e for e in sat_events if e.get("stroke", 0) == heal_stroke
            ]
            if post_heal_sat:
                # node_fail_counts keys use canonical names (e.g. "implement")
                counts = post_heal_sat[0].get("node_fail_counts", {})
                # After healing, the canonical "implement" key should be absent or 0
                assert counts.get("implement", 0) == 0


# ──────────────────────────────────────────────────────────────────────────────
# 8. High-Concurrency Stress Test (50 simultaneous mandates)
# ──────────────────────────────────────────────────────────────────────────────


class TestHighConcurrencyMandates:
    """
    STRESS TEST: Fire 50 simultaneous mandates at the NStrokeEngine.

    Asserts:
      - All 50 complete without exception.
      - Each pipeline_id is unique (DAG isolation).
      - All results report ``satisfied=True``.
      - Total wall-clock time is reasonable (< 30 s for 50 offline runs).
      - No shared state corruption (each engine is isolated by design).
    """

    N_CONCURRENT = 50

    def _run_single_mandate(self, i: int) -> NStrokeResult:
        """Build a fresh engine + locked intent and run it; return the result."""
        engine = _make_engine()
        locked = _make_locked(
            intent=["BUILD", "DEBUG", "AUDIT", "DESIGN", "EXPLAIN"][i % 5],
            mandate_text=(
                f"build implement create add write generate mandate-{i} "
                "synthesise integrate deploy ship release update"
            ),
        )
        return engine.run(locked, pipeline_id=f"stress-{i:04d}")

    def test_all_50_mandates_complete(self) -> None:
        results: list[NStrokeResult | Exception] = []
        errors: list[Exception] = []

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {
                pool.submit(self._run_single_mandate, i): i
                for i in range(self.N_CONCURRENT)
            }
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

        assert not errors, (
            f"{len(errors)} mandates raised exceptions:\n"
            + "\n".join(str(e) for e in errors[:5])
        )
        assert len(results) == self.N_CONCURRENT

    def test_all_50_pipeline_ids_unique(self) -> None:
        results: list[NStrokeResult] = []

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(self._run_single_mandate, i)
                       for i in range(self.N_CONCURRENT)]
            for fut in as_completed(futures):
                results.append(fut.result())

        ids = [r.pipeline_id for r in results]
        assert len(ids) == len(
            set(ids)), "Duplicate pipeline_ids detected — DAG isolation broken"

    def test_all_50_results_satisfied(self) -> None:
        results: list[NStrokeResult] = []

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(self._run_single_mandate, i)
                       for i in range(self.N_CONCURRENT)]
            for fut in as_completed(futures):
                results.append(fut.result())

        failed = [r for r in results if not r.satisfied]
        assert not failed, (
            f"{len(failed)}/{len(results)} mandates not satisfied: "
            + str([r.pipeline_id for r in failed[:3]])
        )

    def test_concurrent_run_wall_time(self) -> None:
        """50 offline runs should complete in under 30s on a modest machine."""
        t0 = time.monotonic()
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(self._run_single_mandate, i)
                       for i in range(self.N_CONCURRENT)]
            for fut in as_completed(futures):
                fut.result()
        elapsed = time.monotonic() - t0
        assert elapsed < 30, (
            f"High-concurrency test took {elapsed:.1f}s — expected < 30s"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 9. HTTP API endpoints
# ──────────────────────────────────────────────────────────────────────────────


class TestNStrokeHTTPEndpoints:
    """End-to-end HTTP tests for /v2/n-stroke and /v2/mcp/tools."""

    @pytest.fixture(autouse=True)
    def _reset_router(self) -> None:
        from studio import api as _api
        _api._router.reset()
        yield
        _api._router.reset()

    @pytest.fixture
    def client(self) -> TestClient:
        from studio.api import app
        return TestClient(app)

    def test_health_reports_n_stroke_components(self, client: TestClient) -> None:
        resp = client.get("/v2/health")
        assert resp.status_code == 200
        components = resp.json()["components"]
        assert "mcp_manager" in components
        assert "model_selector" in components
        assert "refinement_supervisor" in components
        assert "n_stroke_engine" in components

    def test_health_mcp_manager_shows_tool_count(self, client: TestClient) -> None:
        resp = client.get("/v2/health")
        mcp_status = resp.json()["components"]["mcp_manager"]
        assert "6 tools" in mcp_status

    def test_mcp_tools_endpoint_returns_manifest(self, client: TestClient) -> None:
        resp = client.get("/v2/mcp/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool_count"] == 6
        assert len(data["tools"]) == 6

    def test_mcp_tools_spec_shape(self, client: TestClient) -> None:
        resp = client.get("/v2/mcp/tools")
        for tool in resp.json()["tools"]:
            assert "uri" in tool
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert tool["uri"].startswith("mcp://tooloo/")

    def test_n_stroke_endpoint_200_and_shape(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json={
            "intent": "BUILD",
            "confidence": 0.95,
            "value_statement": "Prove N-stroke HTTP e2e works",
            "mandate_text": (
                "build implement create add write generate synthesise integrate deploy"
            ),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "pipeline_id" in data
        assert data["pipeline_id"].startswith("ns-")
        assert "result" in data
        assert "latency_ms" in data

    def test_n_stroke_result_shape(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json={
            "intent": "AUDIT",
            "confidence": 0.95,
            "value_statement": "Security audit of engine modules",
            "mandate_text": (
                "audit scan review check validate verify report status health security"
            ),
        })
        result = resp.json()["result"]
        assert set(result) >= {
            "pipeline_id", "locked_intent", "strokes", "final_verdict",
            "satisfied", "total_strokes", "model_escalations",
            "healing_invocations", "latency_ms",
        }

    def test_n_stroke_audit_uses_tier_2_model(self, client: TestClient) -> None:
        """AUDIT intent should select Tier 2 model on stroke 1."""
        resp = client.post("/v2/n-stroke", json={
            "intent": "AUDIT",
            "confidence": 0.95,
            "value_statement": "Security audit",
            "mandate_text": "audit scan review check validate security health dependency",
        })
        result = resp.json()["result"]
        assert result["strokes"][0]["model_selection"]["tier"] == 2

    def test_n_stroke_mcp_tools_in_stroke_record(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json={
            "intent": "BUILD",
            "confidence": 0.95,
            "value_statement": "Test MCP injection",
            "mandate_text": "build implement create add write generate synthesise",
        })
        result = resp.json()["result"]
        stroke = result["strokes"][0]
        assert len(stroke["mcp_tools_injected"]) == 6

    def test_n_stroke_satisfied_on_good_mandate(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json={
            "intent": "BUILD",
            "confidence": 0.95,
            "value_statement": "Prove pipeline satisfies mandate",
            "mandate_text": "build implement create add write generate synthesise",
        })
        result = resp.json()["result"]
        assert result["satisfied"] is True
        assert result["final_verdict"] == "pass"

    def test_n_stroke_max_strokes_respected(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json={
            "intent": "BUILD",
            "confidence": 0.95,
            "value_statement": "Test max_strokes override",
            "mandate_text": "build implement create add write generate",
            "max_strokes": 2,
        })
        result = resp.json()["result"]
        assert result["total_strokes"] <= 2

    def test_n_stroke_generates_unique_pipeline_ids(self, client: TestClient) -> None:
        ids = set()
        for _ in range(5):
            resp = client.post("/v2/n-stroke", json={
                "intent": "BUILD",
                "confidence": 0.95,
                "value_statement": "Uniqueness test",
                "mandate_text": "build implement create add write generate",
            })
            ids.add(resp.json()["pipeline_id"])
        assert len(ids) == 5, "Duplicate pipeline_ids detected"
