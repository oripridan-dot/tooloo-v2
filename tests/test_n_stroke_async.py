"""
tests/test_n_stroke_async.py — Async N-Stroke Path Tests.

Covers:
  TestNStrokeRunAsyncFallback   — run_async() without AsyncFluidExecutor falls
                                  back to loop.run_in_executor(run())
  TestNStrokeRunAsync           — run_async() with a mocked AsyncFluidExecutor
                                  calls fan_out_dag_async, returns NStrokeResult
  TestRunStrokeAsync            — _run_stroke_async() broadcasts execution_mode
                                  "async_fluid" and converts AsyncExecutionResult
                                  → ExecutionResult correctly
  TestNStrokeAsyncHTTPEndpoint  — POST /v2/n-stroke/async returns 200, correct
                                  shape, and "execution_mode": "async_fluid"
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from engine.async_fluid_executor import AsyncEnvelope, AsyncExecutionResult, AsyncFluidExecutor
from engine.executor import Envelope, ExecutionResult, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBooster
from engine.mcp_manager import MCPManager
from engine.model_selector import ModelSelector
from engine.n_stroke import MAX_STROKES, NStrokeEngine, NStrokeResult
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.refinement_supervisor import RefinementSupervisor
from engine.router import LockedIntent, MandateRouter
from engine.scope_evaluator import ScopeEvaluator
from engine.tribunal import Tribunal


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_locked(
    intent: str = "BUILD",
    confidence: float = 0.95,
    mandate_text: str = "build implement create add write generate",
) -> LockedIntent:
    return LockedIntent(
        intent=intent,
        confidence=confidence,
        value_statement="Prove async path works.",
        constraint_summary="offline tests, no Gemini API",
        mandate_text=mandate_text,
        context_turns=[],
        locked_at=datetime.now(UTC).isoformat(),
    )


def _make_engine(
    *,
    broadcast_events: list | None = None,
    max_strokes: int = 1,
    async_fluid_executor: AsyncFluidExecutor | None = None,
) -> NStrokeEngine:
    """Construct a test NStrokeEngine with optional async executor and event capture."""
    bank = PsycheBank()
    events = broadcast_events if broadcast_events is not None else []

    def _capture(event: dict[str, Any]) -> None:
        events.append(event)

    return NStrokeEngine(
        router=MandateRouter(),
        booster=JITBooster(),
        tribunal=Tribunal(bank=bank),
        sorter=TopologicalSorter(),
        executor=JITExecutor(),
        scope_evaluator=ScopeEvaluator(),
        refinement_loop=RefinementLoop(),
        mcp_manager=MCPManager(),
        model_selector=ModelSelector(),
        refinement_supervisor=RefinementSupervisor(),
        broadcast_fn=_capture,
        max_strokes=max_strokes,
        async_fluid_executor=async_fluid_executor,
    )


def _make_async_results(node_ids: list[str], *, success: bool = True) -> list[AsyncExecutionResult]:
    """Produce synthetic AsyncExecutionResults for the given node IDs."""
    return [
        AsyncExecutionResult(
            mandate_id=nid,
            success=success,
            output={"output": f"[synthetic-{nid}]", "role": "assistant"},
            latency_ms=5.0,
        )
        for nid in node_ids
    ]


# ──────────────────────────────────────────────────────────────────────────────
# 1. Fallback path — no AsyncFluidExecutor injected
# ──────────────────────────────────────────────────────────────────────────────


class TestNStrokeRunAsyncFallback:
    """When NStrokeEngine has no AsyncFluidExecutor, run_async() wraps run()."""

    def test_fallback_returns_n_stroke_result(self) -> None:
        engine = _make_engine(max_strokes=1)
        assert engine._async_fluid_executor is None

        locked = _make_locked()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(locked, pipeline_id="fallback-test-001")
        )

        assert isinstance(result, NStrokeResult)
        assert result.pipeline_id == "fallback-test-001"

    def test_fallback_result_has_strokes(self) -> None:
        engine = _make_engine(max_strokes=1)
        locked = _make_locked()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(locked)
        )
        assert result.total_strokes >= 1
        assert len(result.strokes) == result.total_strokes

    def test_fallback_broadcasts_n_stroke_start(self) -> None:
        events: list[dict] = []
        engine = _make_engine(broadcast_events=events, max_strokes=1)
        locked = _make_locked()
        asyncio.get_event_loop().run_until_complete(engine.run_async(locked))

        types = [e["type"] for e in events]
        assert "n_stroke_start" in types
        assert "n_stroke_complete" in types

    def test_fallback_broadcasts_n_stroke_complete(self) -> None:
        events: list[dict] = []
        engine = _make_engine(broadcast_events=events, max_strokes=1)
        locked = _make_locked()
        asyncio.get_event_loop().run_until_complete(engine.run_async(locked))

        complete = [e for e in events if e["type"] == "n_stroke_complete"]
        assert len(complete) == 1
        assert complete[0]["final_verdict"] in ("pass", "warn", "fail")


# ──────────────────────────────────────────────────────────────────────────────
# 2. Async path — mocked AsyncFluidExecutor
# ──────────────────────────────────────────────────────────────────────────────


class TestNStrokeRunAsync:
    """run_async() delegates Process 2 execution to fan_out_dag_async."""

    def _make_mock_executor(self, node_ids: list[str] | None = None) -> AsyncFluidExecutor:
        """Return an AsyncFluidExecutor whose fan_out_dag_async is mocked."""
        mock_executor = MagicMock(spec=AsyncFluidExecutor)

        async def _fake_fan_out(work_fn, envelopes, dep_map, **kwargs):
            ids = [e.mandate_id for e in envelopes]
            return _make_async_results(ids, success=True)

        mock_executor.fan_out_dag_async = _fake_fan_out
        return mock_executor

    def test_run_async_returns_n_stroke_result(self) -> None:
        mock_exec = self._make_mock_executor()
        engine = _make_engine(max_strokes=1, async_fluid_executor=mock_exec)

        locked = _make_locked()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(locked, pipeline_id="async-test-001")
        )

        assert isinstance(result, NStrokeResult)
        assert result.pipeline_id == "async-test-001"

    def test_run_async_result_fields(self) -> None:
        mock_exec = self._make_mock_executor()
        engine = _make_engine(max_strokes=1, async_fluid_executor=mock_exec)

        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked())
        )

        assert result.final_verdict in ("pass", "warn", "fail")
        assert result.total_strokes >= 1
        assert result.model_escalations >= 0
        assert result.healing_invocations >= 0
        assert result.latency_ms >= 0.0

    def test_run_async_to_dict_shape(self) -> None:
        mock_exec = self._make_mock_executor()
        engine = _make_engine(max_strokes=1, async_fluid_executor=mock_exec)

        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked())
        )
        d = result.to_dict()

        expected_keys = {
            "pipeline_id", "locked_intent", "strokes", "final_verdict",
            "satisfied", "total_strokes", "model_escalations",
            "healing_invocations", "latency_ms", "crisis", "execution_mode",
        }
        assert expected_keys.issubset(d.keys())

    def test_fan_out_dag_async_is_called(self) -> None:
        """fan_out_dag_async must be invoked (not the sync fan_out_dag)."""
        call_log: list[str] = []

        async def _tracked_fan_out(work_fn, envelopes, dep_map, **kwargs):
            call_log.append("fan_out_dag_async")
            return _make_async_results([e.mandate_id for e in envelopes])

        mock_exec = MagicMock(spec=AsyncFluidExecutor)
        mock_exec.fan_out_dag_async = _tracked_fan_out

        engine = _make_engine(max_strokes=1, async_fluid_executor=mock_exec)
        asyncio.get_event_loop().run_until_complete(engine.run_async(_make_locked()))

        assert "fan_out_dag_async" in call_log

    def test_run_async_execution_mode_is_async_fluid(self) -> None:
        """run_async() result.execution_mode must equal 'async_fluid'."""
        mock_exec = self._make_mock_executor()
        engine = _make_engine(max_strokes=1, async_fluid_executor=mock_exec)
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked())
        )
        assert result.execution_mode == "async_fluid"
        assert result.to_dict()["execution_mode"] == "async_fluid"

    def test_run_sync_execution_mode_is_sync(self) -> None:
        """run() (sync path) result.execution_mode must equal 'sync'."""
        engine = _make_engine(max_strokes=1)
        locked = _make_locked()
        result = engine.run(locked)
        assert result.execution_mode == "sync"
        assert result.to_dict()["execution_mode"] == "sync"

    def test_run_async_broadcasts_n_stroke_start_with_mode(self) -> None:
        events: list[dict] = []

        async def _fake_fan_out(work_fn, envelopes, dep_map, **kwargs):
            return _make_async_results([e.mandate_id for e in envelopes])

        mock_exec = MagicMock(spec=AsyncFluidExecutor)
        mock_exec.fan_out_dag_async = _fake_fan_out

        engine = _make_engine(broadcast_events=events,
                              max_strokes=1, async_fluid_executor=mock_exec)
        asyncio.get_event_loop().run_until_complete(engine.run_async(_make_locked()))

        start_events = [e for e in events if e["type"] == "n_stroke_start"]
        assert len(start_events) == 1
        assert start_events[0].get("mode") == "async_fluid"

    def test_run_async_broadcasts_execution_with_async_mode(self) -> None:
        events: list[dict] = []

        async def _fake_fan_out(work_fn, envelopes, dep_map, **kwargs):
            return _make_async_results([e.mandate_id for e in envelopes])

        mock_exec = MagicMock(spec=AsyncFluidExecutor)
        mock_exec.fan_out_dag_async = _fake_fan_out

        engine = _make_engine(broadcast_events=events,
                              max_strokes=1, async_fluid_executor=mock_exec)
        asyncio.get_event_loop().run_until_complete(engine.run_async(_make_locked()))

        exec_events = [e for e in events if e["type"] == "execution"]
        assert any(e.get("execution_mode") == "async_fluid" for e in exec_events), (
            "Expected at least one 'execution' event with execution_mode='async_fluid'"
        )

    def test_run_async_broadcasts_n_stroke_complete(self) -> None:
        events: list[dict] = []

        async def _fake_fan_out(work_fn, envelopes, dep_map, **kwargs):
            return _make_async_results([e.mandate_id for e in envelopes])

        mock_exec = MagicMock(spec=AsyncFluidExecutor)
        mock_exec.fan_out_dag_async = _fake_fan_out

        engine = _make_engine(broadcast_events=events,
                              max_strokes=1, async_fluid_executor=mock_exec)
        asyncio.get_event_loop().run_until_complete(engine.run_async(_make_locked()))

        complete = [e for e in events if e["type"] == "n_stroke_complete"]
        assert len(complete) == 1
        c = complete[0]
        assert "satisfied" in c
        assert "final_verdict" in c
        assert "total_strokes" in c
        assert "latency_ms" in c


# ──────────────────────────────────────────────────────────────────────────────
# 3. _run_stroke_async internals
# ──────────────────────────────────────────────────────────────────────────────


class TestRunStrokeAsync:
    """_run_stroke_async converts AsyncExecutionResult → ExecutionResult correctly."""

    def _make_engine_with_capture(self) -> tuple[NStrokeEngine, list[dict], AsyncFluidExecutor]:
        events: list[dict] = []

        async def _fake_fan_out(work_fn, envelopes, dep_map, **kwargs):
            return _make_async_results([e.mandate_id for e in envelopes])

        mock_exec = MagicMock(spec=AsyncFluidExecutor)
        mock_exec.fan_out_dag_async = _fake_fan_out

        engine = _make_engine(
            broadcast_events=events,
            max_strokes=1,
            async_fluid_executor=mock_exec,
        )
        return engine, events, mock_exec

    def test_execution_results_are_execution_result_instances(self) -> None:
        engine, events, _ = self._make_engine_with_capture()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked())
        )
        stroke = result.strokes[0]
        for r in stroke.execution_results:
            assert isinstance(r, ExecutionResult), (
                f"Expected ExecutionResult, got {type(r)}"
            )

    def test_execution_results_have_correct_fields(self) -> None:
        engine, events, _ = self._make_engine_with_capture()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked())
        )
        stroke = result.strokes[0]
        for r in stroke.execution_results:
            assert isinstance(r.mandate_id, str) and r.mandate_id
            assert isinstance(r.success, bool)
            assert r.latency_ms >= 0.0

    def test_stroke_record_fields_populated(self) -> None:
        engine, events, _ = self._make_engine_with_capture()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked())
        )
        stroke = result.strokes[0]
        assert stroke.stroke == 1
        assert stroke.plan is not None
        assert stroke.scope is not None
        assert stroke.refinement is not None
        assert stroke.mcp_tools_injected

    def test_stroke_record_to_dict_shape(self) -> None:
        engine, events, _ = self._make_engine_with_capture()
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked())
        )
        d = result.strokes[0].to_dict()
        expected_keys = {
            "stroke", "model_selection", "preflight_jit", "preflight_tribunal",
            "plan", "scope", "mcp_tools_injected", "midflight_jit",
            "execution_results", "refinement", "healing_report",
            "satisfied", "latency_ms",
        }
        assert expected_keys.issubset(d.keys())

    def test_async_work_fn_wraps_sync_in_executor(self) -> None:
        """Verify sync work_fn is callable from the async path without errors."""
        call_log: list[str] = []

        def _sync_work_fn(env: Envelope) -> dict:
            call_log.append(env.mandate_id)
            return {"output": "[sync-result]", "role": "assistant"}

        async def _fake_fan_out(work_fn, envelopes, dep_map, **kwargs):
            # Call work_fn via asyncio just like the real executor would
            loop = asyncio.get_event_loop()
            results = []
            for env in envelopes:
                sync_env = Envelope(
                    mandate_id=env.mandate_id,
                    intent=env.intent,
                    domain=env.domain,
                    metadata=env.metadata,
                )
                output = await loop.run_in_executor(None, _sync_work_fn, sync_env)
                results.append(AsyncExecutionResult(
                    mandate_id=env.mandate_id,
                    success=True,
                    output=output,
                    latency_ms=1.0,
                ))
            return results

        mock_exec = MagicMock(spec=AsyncFluidExecutor)
        mock_exec.fan_out_dag_async = _fake_fan_out

        engine = _make_engine(max_strokes=1, async_fluid_executor=mock_exec)
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked(), work_fn=_sync_work_fn)
        )
        # work_fn was invoked for at least one node
        assert len(call_log) >= 1

    def test_failing_async_results_propagate_to_stroke(self) -> None:
        """AsyncExecutionResult with success=False must map to failed ExecutionResult."""

        async def _fail_fan_out(work_fn, envelopes, dep_map, **kwargs):
            return [
                AsyncExecutionResult(
                    mandate_id=e.mandate_id,
                    success=False,
                    output=None,
                    latency_ms=1.0,
                    error="synthetic-failure",
                )
                for e in envelopes
            ]

        mock_exec = MagicMock(spec=AsyncFluidExecutor)
        mock_exec.fan_out_dag_async = _fail_fan_out

        engine = _make_engine(max_strokes=1, async_fluid_executor=mock_exec)
        result = asyncio.get_event_loop().run_until_complete(
            engine.run_async(_make_locked())
        )
        stroke = result.strokes[0]
        assert any(not r.success for r in stroke.execution_results), (
            "Expected at least one failed ExecutionResult from the failing async path"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 4. HTTP endpoint — POST /v2/n-stroke/async
# ──────────────────────────────────────────────────────────────────────────────


class TestNStrokeAsyncHTTPEndpoint:
    """POST /v2/n-stroke/async: 200, correct shape, execution_mode: async_fluid."""

    @pytest.fixture(scope="class")
    def client(self) -> TestClient:
        from studio.api import app
        return TestClient(app)

    _PAYLOAD: dict[str, Any] = {
        "intent": "BUILD",
        "confidence": 0.95,
        "value_statement": "Prove async HTTP endpoint works.",
        "constraint_summary": "offline tests",
        "mandate_text": "build implement create add write generate",
        "max_strokes": 1,
    }

    def test_status_200(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        assert resp.status_code == 200, resp.text

    def test_response_shape(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert "pipeline_id" in body
        assert "result" in body
        assert "execution_mode" in body
        assert "latency_ms" in body

    def test_execution_mode_is_async_fluid(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert body["execution_mode"] == "async_fluid"

    def test_result_contains_pipeline_id(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert body["result"]["pipeline_id"] == body["pipeline_id"]

    def test_result_final_verdict_present(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        verdict = body["result"]["final_verdict"]
        assert verdict in ("pass", "warn", "fail")

    def test_result_strokes_present(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert isinstance(body["result"]["strokes"], list)
        assert len(body["result"]["strokes"]) >= 1

    def test_result_execution_mode_is_async_fluid(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert body["result"]["execution_mode"] == "async_fluid"

    def test_pipeline_id_has_async_prefix(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert body["pipeline_id"].startswith("ns-async-")

    def test_latency_ms_is_positive(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert body["latency_ms"] >= 0.0

    def test_custom_max_strokes_respected(self, client: TestClient) -> None:
        payload = {**self._PAYLOAD, "max_strokes": 2}
        resp = client.post("/v2/n-stroke/async", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        # Should complete within 2 strokes
        assert body["result"]["total_strokes"] <= 2

    # Wave B — execution_mode field propagation
    def test_result_to_dict_has_execution_mode_async_fluid(self, client: TestClient) -> None:
        """NStrokeResult.to_dict() must include execution_mode=async_fluid for async path."""
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert body["result"]["execution_mode"] == "async_fluid"

    # Wave D — strokes_detail field
    def test_result_has_strokes_detail(self, client: TestClient) -> None:
        """NStrokeResult.to_dict() must include strokes_detail list."""
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        assert "strokes_detail" in body["result"]
        assert isinstance(body["result"]["strokes_detail"], list)
        assert len(body["result"]["strokes_detail"]) >= 1

    def test_strokes_detail_fields(self, client: TestClient) -> None:
        """Each strokes_detail entry must have stroke_num, latency_ms, node_count, execution_mode."""
        resp = client.post("/v2/n-stroke/async", json=self._PAYLOAD)
        body = resp.json()
        for detail in body["result"]["strokes_detail"]:
            assert "stroke_num" in detail
            assert "latency_ms" in detail
            assert "node_count" in detail
            assert detail["execution_mode"] == "async_fluid"
