"""tests/test_async_fluid_executor.py — Unit tests for engine/async_fluid_executor.py.

Covers:
- AsyncFluidExecutor.fan_out_async: empty, single, multi, ordering, concurrency
- AsyncFluidExecutor.fan_out_dag_async: no-deps, linear chain, diamond DAG,
  failure propagation, unknown dependency error
- AsyncEnvelope DTO, AsyncExecutionResult DTO
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from engine.async_fluid_executor import (
    AsyncEnvelope,
    AsyncExecutionResult,
    AsyncFluidExecutor,
)


# ── DTOs ─────────────────────────────────────────────────────────────────────

class TestAsyncEnvelope:
    def test_defaults(self):
        env = AsyncEnvelope(mandate_id="m-1", intent="BUILD")
        assert env.domain == "backend"
        assert env.metadata == {}

    def test_custom_fields(self):
        env = AsyncEnvelope(mandate_id="m-2", intent="DEBUG", domain="frontend",
                            metadata={"stroke": 3})
        assert env.domain == "frontend"
        assert env.metadata["stroke"] == 3


class TestAsyncExecutionResult:
    def test_to_dict_shape(self):
        r = AsyncExecutionResult(
            mandate_id="m-42",
            success=True,
            output={"result": "ok"},
            latency_ms=12.34,
        )
        d = r.to_dict()
        assert d["mandate_id"] == "m-42"
        assert d["success"] is True
        assert d["latency_ms"] == 12.34
        assert d["error"] is None

    def test_to_dict_error_field(self):
        r = AsyncExecutionResult(
            mandate_id="m-err",
            success=False,
            output=None,
            latency_ms=1.0,
            error="timeout",
        )
        d = r.to_dict()
        assert d["error"] == "timeout"
        assert d["success"] is False


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_executor():
    return AsyncFluidExecutor(max_workers=4)


async def simple_work_fn(env: AsyncEnvelope) -> dict[str, Any]:
    """Fast successful work function."""
    return {"mandate_id": env.mandate_id, "done": True}


async def slow_work_fn(env: AsyncEnvelope) -> dict[str, Any]:
    """Simulates real async work."""
    await asyncio.sleep(0.01)
    return {"mandate_id": env.mandate_id, "done": True}


async def failing_work_fn(env: AsyncEnvelope) -> dict[str, Any]:
    raise RuntimeError(f"Forced failure for {env.mandate_id}")


# ── fan_out_async ─────────────────────────────────────────────────────────────

class TestFanOutAsync:
    def test_empty_envelopes_returns_empty(self):
        ex = make_executor()
        results = asyncio.run(ex.fan_out_async(simple_work_fn, []))
        assert results == []

    def test_single_envelope(self):
        ex = make_executor()
        envs = [AsyncEnvelope("m-1", "BUILD")]
        results = asyncio.run(ex.fan_out_async(simple_work_fn, envs))
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].mandate_id == "m-1"

    def test_order_preserved(self):
        ex = make_executor()
        envs = [AsyncEnvelope(f"m-{i}", "BUILD") for i in range(10)]
        results = asyncio.run(ex.fan_out_async(simple_work_fn, envs))
        for i, r in enumerate(results):
            assert r.mandate_id == f"m-{i}"

    def test_latency_recorded(self):
        ex = make_executor()
        envs = [AsyncEnvelope("m-lat", "BUILD")]
        results = asyncio.run(ex.fan_out_async(slow_work_fn, envs))
        assert results[0].latency_ms >= 0

    def test_max_concurrent_respected(self):
        """Verify that at most max_concurrent tasks run at once."""
        ex = make_executor()
        counter = {"peak": 0, "current": 0}

        async def counting_fn(env: AsyncEnvelope) -> dict[str, Any]:
            counter["current"] += 1
            counter["peak"] = max(counter["peak"], counter["current"])
            await asyncio.sleep(0.005)
            counter["current"] -= 1
            return {"done": True}

        envs = [AsyncEnvelope(f"m-{i}", "BUILD") for i in range(8)]
        asyncio.run(ex.fan_out_async(counting_fn, envs, max_concurrent=3))
        assert counter["peak"] <= 3

    def test_work_fn_exception_captured_as_failure(self):
        ex = make_executor()
        envs = [AsyncEnvelope("m-fail", "BUILD")]
        results = asyncio.run(ex.fan_out_async(failing_work_fn, envs))
        assert results[0].success is False
        assert results[0].error is not None
        assert "Forced failure" in results[0].error

    def test_mixed_success_and_failure(self):
        ex = make_executor()

        async def mixed_fn(env: AsyncEnvelope) -> dict[str, Any]:
            if env.mandate_id.endswith("fail"):
                raise RuntimeError("fail")
            return {"ok": True}

        envs = [
            AsyncEnvelope("m-ok", "BUILD"),
            AsyncEnvelope("m-fail", "BUILD"),
            AsyncEnvelope("m-ok2", "BUILD"),
        ]
        results = asyncio.run(ex.fan_out_async(mixed_fn, envs))
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True


# ── fan_out_dag_async ─────────────────────────────────────────────────────────

class TestFanOutDagAsync:
    def test_empty_dag(self):
        ex = make_executor()
        results = asyncio.run(ex.fan_out_dag_async(simple_work_fn, [], {}))
        assert results == []

    def test_no_dependencies(self):
        ex = make_executor()
        envs = [AsyncEnvelope("a", "BUILD"), AsyncEnvelope("b", "BUILD")]
        results = asyncio.run(ex.fan_out_dag_async(simple_work_fn, envs, {}))
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_linear_chain(self):
        """a → b → c: all succeed in dependency order."""
        ex = make_executor()
        order = []

        async def ordered_fn(env: AsyncEnvelope) -> dict[str, Any]:
            order.append(env.mandate_id)
            return {"id": env.mandate_id}

        envs = [AsyncEnvelope("a", "BUILD"),
                AsyncEnvelope("b", "BUILD"),
                AsyncEnvelope("c", "BUILD")]
        deps = {"a": [], "b": ["a"], "c": ["b"]}
        results = asyncio.run(ex.fan_out_dag_async(ordered_fn, envs, deps))
        assert all(r.success for r in results)
        # Order must be a before b before c
        assert order.index("a") < order.index("b") < order.index("c")

    def test_diamond_dag(self):
        """
            a
           / (backslash)
          b   c
           (backslash) /
            d
        b and c run in parallel; d waits for both.
        """
        ex = make_executor()
        completion_times: dict[str, float] = {}

        async def timed_fn(env: AsyncEnvelope) -> dict[str, Any]:
            await asyncio.sleep(0.005)
            completion_times[env.mandate_id] = asyncio.get_event_loop().time()
            return {"id": env.mandate_id}

        envs = [
            AsyncEnvelope("a", "BUILD"),
            AsyncEnvelope("b", "BUILD"),
            AsyncEnvelope("c", "BUILD"),
            AsyncEnvelope("d", "BUILD"),
        ]
        deps = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}
        results = asyncio.run(ex.fan_out_dag_async(timed_fn, envs, deps))
        assert all(r.success for r in results)
        # d must complete after both b and c
        assert completion_times["d"] > completion_times["b"]
        assert completion_times["d"] > completion_times["c"]

    def test_unknown_dependency_raises_value_error(self):
        ex = make_executor()
        envs = [AsyncEnvelope("a", "BUILD")]
        deps = {"a": ["nonexistent"]}
        with pytest.raises(ValueError, match="Unknown dependency"):
            asyncio.run(ex.fan_out_dag_async(simple_work_fn, envs, deps))

    def test_failure_propagates_to_dependents(self):
        """If parent fails, child is marked blocked/failed."""
        ex = make_executor()

        async def partial_fail_fn(env: AsyncEnvelope) -> dict[str, Any]:
            if env.mandate_id == "a":
                raise RuntimeError("parent fail")
            return {"ok": True}

        envs = [AsyncEnvelope("a", "BUILD"), AsyncEnvelope("b", "BUILD")]
        deps = {"a": [], "b": ["a"]}
        results = asyncio.run(ex.fan_out_dag_async(
            partial_fail_fn, envs, deps))
        result_map = {r.mandate_id: r for r in results}
        assert result_map["a"].success is False
        # b should be blocked (failed due to dependency failure)
        assert result_map["b"].success is False
        assert "Blocked" in (result_map["b"].error or "")

    def test_ordering_matches_input_when_no_deps(self):
        ex = make_executor()
        envs = [AsyncEnvelope(f"n-{i}", "BUILD") for i in range(5)]
        results = asyncio.run(ex.fan_out_dag_async(simple_work_fn, envs, {}))
        for i, r in enumerate(results):
            assert r.mandate_id == f"n-{i}"
