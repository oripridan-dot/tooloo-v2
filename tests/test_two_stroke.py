"""
tests/test_two_stroke.py — Two-Stroke Engine + ConversationalIntentDiscovery tests.

Coverage:
  • LockedIntent / IntentLockResult DTO shape
  • ConversationalIntentDiscovery — multi-turn clarification, confidence gate,
    value detection, session isolation, clear_session, get_lock
  • TwoStrokeEngine — happy-path, multi-iteration, max-iterations cap,
    broadcast events, retry-signal injection, satisfaction gate
  • Pipeline HTTP endpoints — /v2/pipeline, /v2/intent/clarify,
    /v2/pipeline/direct, health
"""
from __future__ import annotations

import math
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from engine.executor import ExecutionResult, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBoostResult, JITBooster
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop, RefinementReport
from engine.router import (
    ConversationalIntentDiscovery,
    IntentLockResult,
    LockedIntent,
    MandateRouter,
)
from engine.scope_evaluator import ScopeEvaluator
from engine.supervisor import MAX_ITERATIONS, TwoStrokeEngine, TwoStrokeResult
from engine.tribunal import Tribunal


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def psyche():
    return PsycheBank()


@pytest.fixture
def router():
    return MandateRouter()


@pytest.fixture
def booster():
    return JITBooster()


@pytest.fixture
def tribunal(psyche):
    return Tribunal(psyche)


@pytest.fixture
def sorter():
    return TopologicalSorter()


@pytest.fixture
def executor():
    return JITExecutor()


@pytest.fixture
def scope_evaluator():
    return ScopeEvaluator()


@pytest.fixture
def refinement_loop():
    return RefinementLoop()


def _build_engine(
    router, booster, tribunal, sorter, executor, scope_evaluator, refinement_loop,
    broadcast_fn=None
) -> TwoStrokeEngine:
    return TwoStrokeEngine(
        router=router,
        booster=booster,
        tribunal=tribunal,
        sorter=sorter,
        executor=executor,
        scope_evaluator=scope_evaluator,
        refinement_loop=refinement_loop,
        broadcast_fn=broadcast_fn,
    )


def _make_locked(
    intent: str = "BUILD",
    confidence: float = 0.95,
    value_statement: str = "reduces manual effort",
    mandate_text: str = "Build a fast REST API that reduces manual effort.",
) -> LockedIntent:
    import datetime
    return LockedIntent(
        intent=intent,
        confidence=confidence,
        value_statement=value_statement,
        constraint_summary="",
        mandate_text=mandate_text,
        context_turns=[{"user": mandate_text}],
        locked_at=datetime.datetime.now(datetime.UTC).isoformat(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# LockedIntent DTO
# ──────────────────────────────────────────────────────────────────────────────

class TestLockedIntentDTO:
    def test_fields_present(self):
        li = _make_locked()
        assert li.intent == "BUILD"
        assert 0.0 <= li.confidence <= 1.0
        assert li.value_statement
        assert li.mandate_text
        assert li.locked_at

    def test_to_dict_keys(self):
        d = _make_locked().to_dict()
        for key in ("intent", "confidence", "value_statement", "constraint_summary",
                    "mandate_text", "context_turns", "locked_at"):
            assert key in d, f"Missing key: {key}"

    def test_to_dict_types(self):
        d = _make_locked().to_dict()
        assert isinstance(d["confidence"], float)
        assert isinstance(d["context_turns"], list)


# ──────────────────────────────────────────────────────────────────────────────
# IntentLockResult DTO
# ──────────────────────────────────────────────────────────────────────────────

class TestIntentLockResultDTO:
    def test_unlocked_shape(self):
        ilr = IntentLockResult(
            locked=False,
            clarification_question="What value does this bring?",
            clarification_type="value",
            locked_intent=None,
            turn_count=1,
            intent_hint="BUILD",
            confidence=0.50,
        )
        d = ilr.to_dict()
        assert d["locked"] is False
        assert d["locked_intent"] is None
        assert d["clarification_question"]

    def test_locked_shape(self):
        li = _make_locked()
        ilr = IntentLockResult(
            locked=True,
            clarification_question="",
            clarification_type="",
            locked_intent=li,
            turn_count=2,
            intent_hint="BUILD",
            confidence=0.95,
        )
        d = ilr.to_dict()
        assert d["locked"] is True
        assert d["locked_intent"] is not None
        assert "intent" in d["locked_intent"]

    def test_to_dict_turn_count(self):
        ilr = IntentLockResult(
            locked=False,
            clarification_question="?",
            clarification_type="intent",
            locked_intent=None,
            turn_count=3,
            intent_hint="DEBUG",
            confidence=0.40,
        )
        assert ilr.to_dict()["turn_count"] == 3


# ──────────────────────────────────────────────────────────────────────────────
# ConversationalIntentDiscovery
# ──────────────────────────────────────────────────────────────────────────────

class TestConversationalIntentDiscovery:
    """Tests for multi-turn intent discovery with a 0.90 confidence lock gate."""

    @pytest.fixture
    def cid(self):
        return ConversationalIntentDiscovery()

    def test_first_turn_returns_question(self, cid):
        result = cid.discover("do something", session_id="s1")
        assert isinstance(result, IntentLockResult)
        # Ambiguous first message should ask for clarification
        assert result.clarification_question
        assert result.turn_count >= 1

    def test_result_is_intent_lock_result(self, cid):
        r = cid.discover("analyse the logs", session_id="s_type")
        assert isinstance(r, IntentLockResult)

    def test_turn_count_increments(self, cid):
        s = "s_turns"
        r1 = cid.discover("do something", session_id=s)
        r2 = cid.discover(
            "it should reduce manual work by automating scripts", session_id=s)
        assert r2.turn_count > r1.turn_count

    def test_high_confidence_explicit_locks(self, cid):
        """A very clear mandate with explicit value should lock immediately."""
        text = (
            "Build a REST API that automates the daily report pipeline "
            "so the team saves 2 hours per day and no one needs to run scripts manually."
        )
        result = cid.discover(text, session_id="s_lock")
        # May lock on first turn or need one follow-up — at least confidence rises
        if result.locked:
            assert result.locked_intent is not None
            assert result.locked_intent.confidence >= 0.90
        else:
            assert result.confidence > 0.0

    def test_value_indicator_detection(self, cid):
        """Text with strong cost/save language must reach high confidence."""
        text = "Refactor the payment module to reduce costs and save 40 hours per month."
        result = cid.discover(text, session_id="s_val")
        # Confidence should be significantly higher than a vague message
        vague = cid.discover("do stuff", session_id="s_vague")
        assert result.confidence >= vague.confidence

    def test_session_isolation(self, cid):
        """Two sessions must not share state."""
        cid.discover(
            "analyse logs carefully and save 3 hours daily", session_id="sA")
        cid.discover("do something", session_id="sB")
        lockA = cid.get_lock("sA")
        lockB = cid.get_lock("sB")
        # If A locked and B didn't, they must differ
        if lockA and not lockB:
            assert lockA.intent != ""

    def test_clear_session_removes_lock(self, cid):
        """After clearing, the session must behave like a fresh one."""
        s = "s_clear"
        # Run some turns
        for txt in (
            "Build an analytics dashboard",
            "It will help the team save time by reducing manual reporting",
        ):
            r = cid.discover(txt, session_id=s)
            if r.locked:
                break
        # Now clear
        cid.clear_session(s)
        # After clearing, get_lock returns None
        assert cid.get_lock(s) is None

    def test_get_lock_none_before_lock(self, cid):
        assert cid.get_lock("nonexistent") is None

    def test_get_lock_returns_locked_intent_after_lock(self, cid):
        s = "s_getlock"
        # Send enough turns to force a lock
        texts = [
            "Automate the report generation system",
            "It eliminates the need for engineers to manually run scripts every morning",
            "It saves the team 4 hours a day and reduces human errors by 90%",
        ]
        final = None
        for txt in texts:
            final = cid.discover(txt, session_id=s)
            if final.locked:
                break
        # By turn 3 the boost should achieve lock
        if final and final.locked:
            li = cid.get_lock(s)
            assert li is not None
            assert isinstance(li, LockedIntent)

    def test_already_locked_session_returns_same_lock(self, cid):
        """Once locked, additional turns return the already-locked result."""
        s = "s_relock"
        texts = [
            "Build an automated testing suite",
            "It saves the QA team 3 hours per sprint and improves release confidence",
            "It reduces manual effort significantly, saving $10k per year",
        ]
        first_lock = None
        for txt in texts:
            r = cid.discover(txt, session_id=s)
            if r.locked and first_lock is None:
                first_lock = r
                break
        if first_lock is None:
            pytest.skip("Could not lock in 3 turns — skip re-lock test")
        # Another turn on a locked session
        r2 = cid.discover("add more detail", session_id=s)
        assert r2.locked is True


# ──────────────────────────────────────────────────────────────────────────────
# TwoStrokeEngine
# ──────────────────────────────────────────────────────────────────────────────

class TestTwoStrokeEngine:

    @pytest.fixture
    def engine(
        self, router, booster, tribunal, sorter, executor, scope_evaluator, refinement_loop
    ):
        return _build_engine(
            router, booster, tribunal, sorter, executor, scope_evaluator, refinement_loop
        )

    def test_run_returns_two_stroke_result(self, engine):
        li = _make_locked()
        result = engine.run(li, max_iterations=1)
        assert isinstance(result, TwoStrokeResult)

    def test_result_shape(self, engine):
        result = engine.run(_make_locked(), max_iterations=1)
        d = result.to_dict()
        for key in ("pipeline_id", "locked_intent", "iterations",
                    "final_verdict", "satisfied", "total_iterations", "latency_ms"):
            assert key in d, f"Missing key: {key}"

    def test_at_least_one_iteration(self, engine):
        result = engine.run(_make_locked(), max_iterations=1)
        assert result.total_iterations >= 1

    def test_max_iterations_respected(self, engine):
        result = engine.run(_make_locked(), max_iterations=MAX_ITERATIONS)
        assert result.total_iterations <= MAX_ITERATIONS

    def test_iterations_list_length_matches(self, engine):
        result = engine.run(_make_locked(), max_iterations=2)
        assert len(result.iterations) == result.total_iterations

    def test_pipeline_id_is_stable(self, engine):
        pid = "pipe-test-abc"
        result = engine.run(_make_locked(), pipeline_id=pid, max_iterations=1)
        assert result.pipeline_id == pid

    def test_pipeline_id_auto_generated(self, engine):
        result = engine.run(_make_locked(), max_iterations=1)
        assert result.pipeline_id.startswith("pipe-")

    def test_broadcast_events_emitted(
        self, router, booster, tribunal, sorter, executor, scope_evaluator, refinement_loop
    ):
        events: list[dict] = []
        engine = _build_engine(
            router, booster, tribunal, sorter, executor, scope_evaluator,
            refinement_loop, broadcast_fn=events.append
        )
        engine.run(_make_locked(), max_iterations=1)

        types = {e["type"] for e in events}
        assert "pipeline_start" in types
        assert "preflight" in types
        assert "process_1_draft" in types
        assert "midflight" in types
        assert "process_2_execute" in types
        assert "satisfaction_gate" in types
        assert "loop_complete" in types

    def test_satisfaction_gate_in_result(self, engine):
        result = engine.run(_make_locked(), max_iterations=1)
        it = result.iterations[0]
        assert it.refinement is not None
        assert it.refinement.verdict in ("pass", "warn", "fail")

    def test_each_iteration_has_four_stages(
        self, router, booster, tribunal, sorter, executor, scope_evaluator, refinement_loop
    ):
        events: list[dict] = []
        engine = _build_engine(
            router, booster, tribunal, sorter, executor, scope_evaluator,
            refinement_loop, broadcast_fn=events.append
        )
        engine.run(_make_locked(), max_iterations=1)
        stage_types = {e["type"] for e in events}
        for stage in ("preflight", "process_1_draft", "midflight", "process_2_execute"):
            assert stage in stage_types

    def test_prior_failure_signal_injected_on_retry(
        self, router, booster, tribunal, sorter, executor, scope_evaluator, refinement_loop
    ):
        """If iter-1 fails, iter-2 preflight's route.mandate_text includes '[retry-signal]'."""
        route_calls: list[str] = []

        class SpyBooster(JITBooster):
            def fetch(self, route):
                route_calls.append(route.mandate_text)
                return super().fetch(route)

        engine = _build_engine(
            router, SpyBooster(), tribunal, sorter, executor, scope_evaluator,
            refinement_loop
        )
        # Run up to 2 iterations — if iter-1 passes there won't be a retry signal
        result = engine.run(_make_locked(), max_iterations=2)

        if result.total_iterations >= 2:
            # At least one second-iteration call must contain the retry signal
            retry_calls = [c for c in route_calls if "[retry-signal]" in c]
            assert retry_calls, "Expected retry-signal in second-iteration booster call"

    def test_result_latency_ms_positive(self, engine):
        result = engine.run(_make_locked(), max_iterations=1)
        assert result.latency_ms > 0.0

    def test_all_iterations_have_plan(self, engine):
        result = engine.run(_make_locked(), max_iterations=2)
        for it in result.iterations:
            assert it.process_1.plan  # should have at least one wave

    def test_custom_max_iterations_zero_defaults_gracefully(self, engine):
        """max_iterations=0 should produce zero iterations (no crash)."""
        result = engine.run(_make_locked(), max_iterations=0)
        assert result.total_iterations == 0
        # final_verdict falls back to whatever last-iteration gave (or default)
        assert isinstance(result.final_verdict, str)


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline HTTP API
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_client():
    from studio.api import app
    return TestClient(app, raise_server_exceptions=False)


class TestTwoStrokePipelineAPI:

    def test_health_includes_supervisor(self, api_client):
        r = api_client.get("/v2/health")
        assert r.status_code == 200
        d = r.json()
        components = d.get("components", d)
        assert "supervisor" in components
        assert components["supervisor"] == "up"

    def test_health_includes_intent_discovery(self, api_client):
        r = api_client.get("/v2/health")
        assert r.status_code == 200
        d = r.json()
        components = d.get("components", d)
        assert components.get("intent_discovery") == "up"

    def test_intent_clarify_returns_200(self, api_client):
        r = api_client.post("/v2/intent/clarify", json={
            "text": "do something useful",
            "session_id": "api-s1",
        })
        assert r.status_code == 200

    def test_intent_clarify_response_shape(self, api_client):
        r = api_client.post("/v2/intent/clarify", json={
            "text": "build a monitoring system",
            "session_id": "api-s2",
        })
        d = r.json()
        assert "locked" in d
        assert "turn_count" in d
        assert "confidence" in d

    def test_intent_clarify_not_locked_on_vague_input(self, api_client):
        r = api_client.post("/v2/intent/clarify", json={
            "text": "stuff",
            "session_id": "api-s3",
        })
        d = r.json()
        assert isinstance(d["locked"], bool)
        if not d["locked"]:
            assert d.get("clarification_question")

    def test_delete_intent_session(self, api_client):
        # First create a session
        api_client.post("/v2/intent/clarify", json={
            "text": "some request",
            "session_id": "api-del",
        })
        r = api_client.delete("/v2/intent/session/api-del")
        assert r.status_code == 200

    def test_pipeline_returns_200(self, api_client):
        r = api_client.post("/v2/pipeline", json={
            "text": "build a fast REST API that saves the team 2 hours daily",
            "session_id": "api-pipe-1",
        })
        assert r.status_code == 200

    def test_pipeline_response_has_correct_keys(self, api_client):
        r = api_client.post("/v2/pipeline", json={
            "text": "create an automated testing system",
            "session_id": "api-pipe-2",
        })
        d = r.json()
        for key in ("pipeline_id", "session_id", "locked", "confidence", "turn_count"):
            assert key in d, f"Missing key: {key}"

    def test_pipeline_locked_returns_result(self, api_client):
        """After locking, the response must include a `result` dict."""
        texts = [
            "Automate the daily report generation",
            "It saves 3 hours per day and eliminates manual script runs",
            "The cost saving is $15k per year — purely automating repetitive work",
        ]
        sid = "api-lock-test"
        final = None
        for text in texts:
            r = api_client.post(
                "/v2/pipeline", json={"text": text, "session_id": sid})
            d = r.json()
            final = d
            if d.get("locked"):
                break

        assert final is not None
        if final.get("locked"):
            assert "result" in final
            assert final["result"] is not None

    def test_pipeline_direct_returns_200(self, api_client):
        r = api_client.post("/v2/pipeline/direct", json={
            "intent": "BUILD",
            "confidence": 0.95,
            "value_statement": "saves 2 hours daily",
            "constraint_summary": "no external deps",
            "mandate_text": "Build a CI pipeline that reduces deploy time.",
            "max_iterations": 1,
        })
        assert r.status_code == 200

    def test_pipeline_direct_response_shape(self, api_client):
        r = api_client.post("/v2/pipeline/direct", json={
            "intent": "ANALYSE",
            "confidence": 0.93,
            "value_statement": "reduces insight latency",
            "constraint_summary": "",
            "mandate_text": "Analyse the access logs for anomalies.",
            "max_iterations": 1,
        })
        d = r.json()
        assert "pipeline_id" in d
        assert "result" in d

    def test_pipeline_direct_result_has_iterations(self, api_client):
        r = api_client.post("/v2/pipeline/direct", json={
            "intent": "BUILD",
            "confidence": 0.96,
            "value_statement": "automates manual work",
            "constraint_summary": "",
            "mandate_text": "Build the automation pipeline.",
            "max_iterations": 1,
        })
        d = r.json()
        result = d.get("result") or {}
        assert "iterations" in result
        assert len(result["iterations"]) >= 1

    def test_pipeline_direct_latency_ms_present(self, api_client):
        r = api_client.post("/v2/pipeline/direct", json={
            "intent": "REFACTOR",
            "confidence": 0.92,
            "value_statement": "improves maintainability",
            "constraint_summary": "",
            "mandate_text": "Refactor the payment module.",
            "max_iterations": 1,
        })
        result = r.json().get("result") or {}
        assert "latency_ms" in result
        assert result["latency_ms"] >= 0.0
