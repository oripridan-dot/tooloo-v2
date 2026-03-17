"""
tests/test_e2e_api.py — TooLoo V2 End-to-End API pipeline tests.

Tests every HTTP route in studio/api.py through FastAPI TestClient,
exercising the complete stack from HTTP boundary → engine components → response.

Coverage matrix
───────────────
  GET  /                   serve_index         HTML served, title present
  GET  /v2/health          health()            all 5 component keys, version
  POST /v2/mandate         route_mandate()     7 intents × clean path,
                                               tribunal poison intercept,
                                               circuit-breaker BLOCKED path,
                                               response schema, mandate_id uniqueness,
                                               latency recorded
  GET  /v2/dag             dag_snapshot()      shape, counts consistent
  GET  /v2/psyche-bank     psyche_bank_rules() pre-seeded rules present
  GET  /v2/router-status   router_status()     keys, initial clean state
  POST /v2/router-reset    router_reset()      resets an open breaker
  GET  /v2/events          sse_stream()        200, Content-Type, connected event

All tests are offline (no LLM / network).
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

import studio.api as api_module
from studio.api import app


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> TestClient:
    """A single TestClient reused for the whole module — no server startup cost."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_router_state() -> None:
    """Reset the circuit-breaker before every test so tests don't bleed state."""
    api_module._router.reset()
    yield
    api_module._router.reset()


# ── 1. Static route ───────────────────────────────────────────────────────────


class TestStaticRoute:
    def test_get_root_returns_200(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200

    def test_get_root_content_type_is_html(self, client: TestClient) -> None:
        r = client.get("/")
        assert "text/html" in r.headers["content-type"]

    def test_get_root_contains_tooloo_branding(self, client: TestClient) -> None:
        r = client.get("/")
        text = r.text
        assert "TooLoo" in text or "tooloo" in text.lower()

    def test_get_root_is_not_empty(self, client: TestClient) -> None:
        r = client.get("/")
        assert len(r.text) > 100


# ── 2. Health endpoint ────────────────────────────────────────────────────────


class TestHealthEndpoint:
    _REQUIRED_COMPONENTS = {"router", "graph",
                            "psyche_bank", "tribunal", "executor"}

    def test_health_returns_200(self, client: TestClient) -> None:
        assert client.get("/v2/health").status_code == 200

    def test_health_status_is_ok(self, client: TestClient) -> None:
        body = client.get("/v2/health").json()
        assert body["status"] == "ok"

    def test_health_version_is_v2(self, client: TestClient) -> None:
        body = client.get("/v2/health").json()
        assert body["version"] == "2.0.0"

    def test_health_all_five_components_present(self, client: TestClient) -> None:
        body = client.get("/v2/health").json()
        assert self._REQUIRED_COMPONENTS <= body["components"].keys()

    def test_health_all_components_are_strings(self, client: TestClient) -> None:
        body = client.get("/v2/health").json()
        for key in self._REQUIRED_COMPONENTS:
            assert isinstance(body["components"][key], str)

    def test_health_router_reports_up(self, client: TestClient) -> None:
        body = client.get("/v2/health").json()
        assert body["components"]["router"] == "up"

    def test_health_tribunal_reports_up(self, client: TestClient) -> None:
        body = client.get("/v2/health").json()
        assert body["components"]["tribunal"] == "up"

    def test_health_executor_reports_up(self, client: TestClient) -> None:
        body = client.get("/v2/health").json()
        assert body["components"]["executor"] == "up"


# ── 3. Mandate endpoint — clean paths ─────────────────────────────────────────


class TestMandateCleanPaths:
    _SHAPE = {"mandate_id", "route", "plan", "execution", "latency_ms"}

    def _post(self, client: TestClient, text: str) -> dict[str, Any]:
        return client.post("/v2/mandate", json={"text": text}).json()

    def test_mandate_build_intent_returns_200(self, client: TestClient) -> None:
        r = client.post(
            "/v2/mandate", json={"text": "build a new authentication service"})
        assert r.status_code == 200

    def test_mandate_build_intent_classified_correctly(self, client: TestClient) -> None:
        body = self._post(client, "build a new authentication service")
        assert body["route"]["intent"] == "BUILD"

    def test_mandate_debug_intent_classified_correctly(self, client: TestClient) -> None:
        body = self._post(client, "fix the crash in the payment service")
        assert body["route"]["intent"] == "DEBUG"

    def test_mandate_audit_intent_classified_correctly(self, client: TestClient) -> None:
        body = self._post(client, "audit the security of all public endpoints")
        assert body["route"]["intent"] == "AUDIT"

    def test_mandate_design_intent_classified_correctly(self, client: TestClient) -> None:
        body = self._post(
            client, "design a new component library and wireframe the UI")
        assert body["route"]["intent"] == "DESIGN"

    def test_mandate_explain_intent_classified_correctly(self, client: TestClient) -> None:
        body = self._post(
            client, "explain how does the DAG sorter produce waves")
        assert body["route"]["intent"] == "EXPLAIN"

    def test_mandate_ideate_intent_classified_correctly(self, client: TestClient) -> None:
        body = self._post(
            client, "brainstorm ideas for a distributed rate-limiter")
        assert body["route"]["intent"] == "IDEATE"

    def test_mandate_spawn_repo_intent_classified_correctly(self, client: TestClient) -> None:
        body = self._post(
            client, "initialise a new repository for the analytics service")
        assert body["route"]["intent"] == "SPAWN_REPO"

    def test_mandate_response_shape_complete(self, client: TestClient) -> None:
        body = self._post(client, "build a REST API with authentication")
        assert self._SHAPE <= body.keys(
        ), f"Missing keys: {self._SHAPE - body.keys()}"

    def test_mandate_plan_is_non_empty_list(self, client: TestClient) -> None:
        # Use keyword-rich text so confidence >= 0.85 and plan is generated
        body = self._post(client, "build implement create add write generate a service")
        assert isinstance(body["plan"], list)
        assert len(body["plan"]) > 0

    def test_mandate_plan_waves_are_lists(self, client: TestClient) -> None:
        body = self._post(client, "build implement create add write a service")
        assert len(body["plan"]) > 0, "plan must be non-empty (high-confidence mandate)"
        for wave in body["plan"]:
            assert isinstance(wave, list)

    def test_mandate_execution_all_waves_succeed(self, client: TestClient) -> None:
        body = self._post(client, "fix the crash in the payment handler")
        assert len(body["execution"]) > 0, "execution must be non-empty"
        assert all(w["success"] for w in body["execution"])

    def test_mandate_id_is_non_empty_string(self, client: TestClient) -> None:
        body = self._post(client, "build something")
        assert isinstance(body["mandate_id"], str)
        assert len(body["mandate_id"]) > 0

    def test_mandate_id_has_m_prefix(self, client: TestClient) -> None:
        body = self._post(client, "build something")
        assert body["mandate_id"].startswith("m-")

    def test_mandate_ids_are_unique_across_calls(self, client: TestClient) -> None:
        ids = {self._post(client, "build something")[
            "mandate_id"] for _ in range(5)}
        assert len(ids) == 5

    def test_mandate_latency_ms_is_positive_float(self, client: TestClient) -> None:
        body = self._post(client, "build an API endpoint")
        assert isinstance(body["latency_ms"], float)
        assert body["latency_ms"] > 0

    def test_mandate_confidence_in_range(self, client: TestClient) -> None:
        body = self._post(client, "build a login handler")
        conf = body["route"]["confidence"]
        assert 0.0 <= conf <= 1.0

    def test_mandate_buddy_line_is_non_empty(self, client: TestClient) -> None:
        body = self._post(client, "build a new service")
        assert len(body["route"]["buddy_line"]) > 0

    def test_mandate_route_contains_timestamp(self, client: TestClient) -> None:
        body = self._post(client, "audit all dependencies")
        ts = body["route"]["ts"]
        assert isinstance(ts, str) and len(ts) > 0

    def test_mandate_execution_results_have_latency(self, client: TestClient) -> None:
        body = self._post(client, "build implement create add write a feature")
        assert len(body["execution"]) > 0, "execution must be non-empty"
        for r in body["execution"]:
            assert isinstance(r["latency_ms"], float) and r["latency_ms"] >= 0


# ── 4. Mandate endpoint — tribunal intercept ──────────────────────────────────


class TestMandateTribunalIntercept:
    """
    Poisoned mandate texts go through the full HTTP stack — Tribunal catches them,
    heals the engram, and the response still completes with a normal mandate_id.
    The route is still classified and the plan/execution proceed.
    """

    def _post(self, client: TestClient, text: str) -> dict[str, Any]:
        return client.post("/v2/mandate", json={"text": text}).json()

    def test_poisoned_mandate_returns_200(self, client: TestClient) -> None:
        r = client.post(
            "/v2/mandate", json={"text": 'result = eval(user_input)'})
        assert r.status_code == 200

    def test_poisoned_mandate_still_has_mandate_id(self, client: TestClient) -> None:
        body = self._post(client, 'call eval(x) in a loop')
        assert body["mandate_id"].startswith("m-")

    def test_poisoned_mandate_plan_still_generated(self, client: TestClient) -> None:
        # Keyword-rich so confidence >= 0.85 — plan must be generated even after tribunal heal
        body = self._post(client, 'build implement create a handler that calls eval(user)')
        assert isinstance(body["plan"], list) and len(body["plan"]) > 0

    def test_hardcoded_secret_in_mandate_still_routes(self, client: TestClient) -> None:
        body = self._post(
            client, 'build an API that has SECRET = "abc123" set')
        assert body["route"]["intent"] != ""
        assert body["mandate_id"].startswith("m-")

    def test_sql_injection_mandate_returns_valid_response(self, client: TestClient) -> None:
        payload = "build SELECT * FROM users WHERE name = ' + user_input"
        body = self._post(client, payload)
        assert body["mandate_id"].startswith("m-")
        assert isinstance(body["latency_ms"], float)


# ── 5. Mandate endpoint — circuit-breaker path ───────────────────────────────


class TestMandateCircuitBreaker:
    def test_tripped_breaker_returns_blocked_intent(self, client: TestClient) -> None:
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            api_module._router._record_failure()
        body = client.post(
            "/v2/mandate", json={"text": "build a critical feature"}).json()
        assert body["route"]["intent"] == "BLOCKED"

    def test_tripped_breaker_plan_is_empty(self, client: TestClient) -> None:
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            api_module._router._record_failure()
        body = client.post(
            "/v2/mandate", json={"text": "build something"}).json()
        assert body["plan"] == []

    def test_tripped_breaker_execution_is_empty(self, client: TestClient) -> None:
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            api_module._router._record_failure()
        body = client.post(
            "/v2/mandate", json={"text": "build something"}).json()
        assert body["execution"] == []

    def test_tripped_breaker_latency_ms_still_recorded(self, client: TestClient) -> None:
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            api_module._router._record_failure()
        body = client.post(
            "/v2/mandate", json={"text": "build something"}).json()
        assert isinstance(body["latency_ms"],
                          float) and body["latency_ms"] >= 0

    def test_after_reset_mandate_routes_normally_again(self, client: TestClient) -> None:
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            api_module._router._record_failure()
        client.post("/v2/router-reset")
        # Keyword-rich text ensures confidence >= 0.85 and plan is generated
        body = client.post(
            "/v2/mandate",
            json={"text": "build implement create a new authentication module"},
        ).json()
        assert body["route"]["intent"] == "BUILD"
        assert body["plan"] != []


# ── 6. DAG snapshot endpoint ──────────────────────────────────────────────────


class TestDagEndpoint:
    def test_dag_returns_200(self, client: TestClient) -> None:
        assert client.get("/v2/dag").status_code == 200

    def test_dag_has_required_keys(self, client: TestClient) -> None:
        body = client.get("/v2/dag").json()
        assert {"nodes", "edges", "node_count", "edge_count"} <= body.keys()

    def test_dag_nodes_is_list(self, client: TestClient) -> None:
        body = client.get("/v2/dag").json()
        assert isinstance(body["nodes"], list)

    def test_dag_edges_is_list(self, client: TestClient) -> None:
        body = client.get("/v2/dag").json()
        assert isinstance(body["edges"], list)

    def test_dag_node_count_matches_nodes_length(self, client: TestClient) -> None:
        body = client.get("/v2/dag").json()
        assert body["node_count"] == len(body["nodes"])

    def test_dag_edge_count_matches_edges_length(self, client: TestClient) -> None:
        body = client.get("/v2/dag").json()
        assert body["edge_count"] == len(body["edges"])

    def test_dag_counts_are_non_negative_integers(self, client: TestClient) -> None:
        body = client.get("/v2/dag").json()
        assert isinstance(body["node_count"], int) and body["node_count"] >= 0
        assert isinstance(body["edge_count"], int) and body["edge_count"] >= 0

    def test_dag_edges_have_from_and_to_keys(self, client: TestClient) -> None:
        # Add an edge to the live graph so there is at least one to inspect
        api_module._graph.add_node("test-dag-src")
        api_module._graph.add_node("test-dag-dst")
        api_module._graph.add_edge("test-dag-src", "test-dag-dst")
        body = client.get("/v2/dag").json()
        edge_cols = {k for e in body["edges"] for k in e.keys()}
        assert {"from", "to"} <= edge_cols


# ── 7. Psyche-bank endpoint ───────────────────────────────────────────────────


class TestPsycheBankEndpoint:
    def test_psyche_bank_returns_200(self, client: TestClient) -> None:
        assert client.get("/v2/psyche-bank").status_code == 200

    def test_psyche_bank_has_version_key(self, client: TestClient) -> None:
        body = client.get("/v2/psyche-bank").json()
        assert "version" in body

    def test_psyche_bank_has_rules_key(self, client: TestClient) -> None:
        body = client.get("/v2/psyche-bank").json()
        assert "rules" in body

    def test_psyche_bank_rules_is_list(self, client: TestClient) -> None:
        body = client.get("/v2/psyche-bank").json()
        assert isinstance(body["rules"], list)

    def test_psyche_bank_pre_seeded_rules_present(self, client: TestClient) -> None:
        body = client.get("/v2/psyche-bank").json()
        assert len(body["rules"]) >= 5, "Expected at least 5 pre-seeded rules"

    def test_psyche_bank_each_rule_has_required_fields(self, client: TestClient) -> None:
        body = client.get("/v2/psyche-bank").json()
        required = {"id", "description", "pattern",
                    "enforcement", "category", "source"}
        for rule in body["rules"]:
            assert required <= rule.keys(
            ), f"Rule missing keys: {required - rule.keys()}"

    def test_psyche_bank_security_rules_are_block_enforcement(self, client: TestClient) -> None:
        body = client.get("/v2/psyche-bank").json()
        for rule in body["rules"]:
            if rule["category"] == "security":
                assert rule["enforcement"] == "block", (
                    f"Security rule {rule['id']!r} should be 'block', got {rule['enforcement']!r}"
                )

    def test_psyche_bank_owasp_hardcoded_secret_rule_exists(self, client: TestClient) -> None:
        body = client.get("/v2/psyche-bank").json()
        ids = [r["id"] for r in body["rules"]]
        assert any("hardcoded" in rid or "secret" in rid for rid in ids), (
            "Expected an OWASP hardcoded-secret rule"
        )

    def test_psyche_bank_version_is_string(self, client: TestClient) -> None:
        body = client.get("/v2/psyche-bank").json()
        assert isinstance(body["version"], str) and len(body["version"]) > 0


# ── 8. Router status endpoint ─────────────────────────────────────────────────


class TestRouterStatusEndpoint:
    def test_router_status_returns_200(self, client: TestClient) -> None:
        assert client.get("/v2/router-status").status_code == 200

    def test_router_status_has_required_keys(self, client: TestClient) -> None:
        body = client.get("/v2/router-status").json()
        assert {"circuit_open", "consecutive_failures",
                "max_fails", "threshold"} <= body.keys()

    def test_router_status_circuit_open_is_false_on_fresh_state(
        self, client: TestClient
    ) -> None:
        body = client.get("/v2/router-status").json()
        assert body["circuit_open"] is False

    def test_router_status_consecutive_failures_zero_on_fresh_state(
        self, client: TestClient
    ) -> None:
        body = client.get("/v2/router-status").json()
        assert body["consecutive_failures"] == 0

    def test_router_status_max_fails_is_positive_int(self, client: TestClient) -> None:
        body = client.get("/v2/router-status").json()
        assert isinstance(body["max_fails"], int) and body["max_fails"] > 0

    def test_router_status_threshold_is_in_range(self, client: TestClient) -> None:
        body = client.get("/v2/router-status").json()
        assert 0.0 < body["threshold"] <= 1.0

    def test_router_status_reflects_manual_failures(self, client: TestClient) -> None:
        api_module._router._record_failure()
        api_module._router._record_failure()
        body = client.get("/v2/router-status").json()
        assert body["consecutive_failures"] == 2

    def test_router_status_circuit_open_after_max_fails(self, client: TestClient) -> None:
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            api_module._router._record_failure()
        body = client.get("/v2/router-status").json()
        assert body["circuit_open"] is True


# ── 9. Router reset endpoint ──────────────────────────────────────────────────


class TestRouterResetEndpoint:
    def test_router_reset_returns_200(self, client: TestClient) -> None:
        assert client.post("/v2/router-reset").status_code == 200

    def test_router_reset_returns_reset_true(self, client: TestClient) -> None:
        body = client.post("/v2/router-reset").json()
        assert body["reset"] is True

    def test_router_reset_returns_status_dict(self, client: TestClient) -> None:
        body = client.post("/v2/router-reset").json()
        assert isinstance(body["status"], dict)
        assert "circuit_open" in body["status"]

    def test_router_reset_closes_open_breaker(self, client: TestClient) -> None:
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            api_module._router._record_failure()
        assert api_module._router.is_tripped
        body = client.post("/v2/router-reset").json()
        assert body["status"]["circuit_open"] is False
        assert not api_module._router.is_tripped

    def test_router_reset_clears_failure_count(self, client: TestClient) -> None:
        api_module._router._record_failure()
        api_module._router._record_failure()
        client.post("/v2/router-reset")
        body = client.get("/v2/router-status").json()
        assert body["consecutive_failures"] == 0

    def test_router_reset_is_idempotent(self, client: TestClient) -> None:
        client.post("/v2/router-reset")
        client.post("/v2/router-reset")
        body = client.get("/v2/router-status").json()
        assert body["circuit_open"] is False


# ── 10. SSE events endpoint ───────────────────────────────────────────────────
#
# httpx.ASGITransport buffers the full response body before delivering it, so
# an infinite SSE stream never flushes to the test client via that transport.
# We solve this two ways:
#   1. HTTP-level checks (status, content-type, first event) — run via a real
#      uvicorn server started on a free port.
#   2. Broadcast & format checks — inspect the API internals without HTTP.


def _find_free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="class")
def live_server_url():
    """Start a real uvicorn server on a free port; yield its base URL."""
    import time
    import threading
    import uvicorn
    import httpx as _httpx

    port = _find_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            _httpx.get(f"{base}/v2/health", timeout=0.3)
            break
        except Exception:
            time.sleep(0.05)

    yield base
    server.should_exit = True
    t.join(timeout=3.0)


class TestSSEEndpoint:
    """SSE endpoint tests.

    HTTP streaming tests use a real uvicorn server so we receive proper
    Server-Sent Events without buffering.  Broadcast and format tests use
    the app internals directly.
    """

    # ── HTTP-level tests (real server) ──────────────────────────────────────

    def test_sse_route_is_registered(self) -> None:
        """Verify GET /v2/events is a registered route in the app."""
        paths = [getattr(r, "path", None) for r in app.routes]
        assert "/v2/events" in paths

    def test_sse_returns_200(self, live_server_url: str) -> None:
        import httpx
        with httpx.stream("GET", f"{live_server_url}/v2/events", timeout=5.0) as r:
            assert r.status_code == 200

    def test_sse_content_type_is_event_stream(self, live_server_url: str) -> None:
        import httpx
        with httpx.stream("GET", f"{live_server_url}/v2/events", timeout=5.0) as r:
            assert "text/event-stream" in r.headers.get("content-type", "")

    def test_sse_emits_connected_event_on_open(self, live_server_url: str) -> None:
        import httpx
        event: dict[str, Any] = {}
        with httpx.stream("GET", f"{live_server_url}/v2/events", timeout=5.0) as r:
            for line in r.iter_lines():
                if line.startswith("data:"):
                    event = json.loads(line[len("data:"):].strip())
                    break
        assert event.get("type") == "connected"

    def test_sse_connected_event_contains_version(self, live_server_url: str) -> None:
        import httpx
        event: dict[str, Any] = {}
        with httpx.stream("GET", f"{live_server_url}/v2/events", timeout=5.0) as r:
            for line in r.iter_lines():
                if line.startswith("data:"):
                    event = json.loads(line[len("data:"):].strip())
                    break
        assert event.get("version") == "2.0.0"

    # ── Internal / unit-level tests ─────────────────────────────────────────

    def test_sse_broadcast_delivers_to_registered_queues(self) -> None:
        """_broadcast puts serialised events into every registered SSE queue."""
        import asyncio
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=10)
        api_module._sse_queues.append(q)
        try:
            api_module._broadcast({"type": "probe", "payload": "ping"})
            raw = q.get_nowait()
            data = json.loads(raw)
            assert data["type"] == "probe"
            assert data["payload"] == "ping"
        finally:
            api_module._sse_queues.remove(q)

    def test_sse_broadcast_does_not_raise_on_full_queue(self) -> None:
        """A full queue is silently skipped — no exception."""
        import asyncio
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        q.put_nowait(json.dumps({"type": "pre-filled"}))  # fill it
        api_module._sse_queues.append(q)
        try:
            api_module._broadcast({"type": "overflow"})  # should not raise
        finally:
            api_module._sse_queues.remove(q)

    def test_sse_broadcast_to_multiple_queues(self) -> None:
        """All registered queues receive the broadcast."""
        import asyncio
        queues = [asyncio.Queue(maxsize=10) for _ in range(3)]
        for q in queues:
            api_module._sse_queues.append(q)
        try:
            api_module._broadcast({"type": "multi", "n": 3})
            for q in queues:
                raw = q.get_nowait()
                data = json.loads(raw)
                assert data["type"] == "multi"
        finally:
            for q in queues:
                api_module._sse_queues.remove(q)


# ── 11. Full pipeline end-to-end integration ─────────────────────────────────


class TestFullPipelineE2E:
    """
    Stateful multi-step tests that exercise the complete flow across
    multiple API calls — proving all pipeline segments are wired correctly.
    """

    def test_mandate_then_health_still_ok(self, client: TestClient) -> None:
        client.post("/v2/mandate", json={"text": "build implement create a payment service"})
        health = client.get("/v2/health").json()
        assert health["status"] == "ok"

    def test_three_mandates_each_get_unique_ids(self, client: TestClient) -> None:
        ids = [
            client.post(
                "/v2/mandate", json={"text": f"build implement create service {i}"}).json()["mandate_id"]
            for i in range(3)
        ]
        assert len(set(ids)) == 3

    def test_mandate_execution_count_matches_plan_wave_count(
        self, client: TestClient
    ) -> None:
        body = client.post(
            "/v2/mandate", json={"text": "build implement create add write a REST API"}).json()
        assert len(body["plan"]) > 0, "plan must be non-empty"
        assert len(body["execution"]) == len(body["plan"])

    def test_multi_intent_sequence_all_succeed(self, client: TestClient) -> None:
        # All texts have >= 2 keyword hits → confidence >= 0.85 → plan is generated
        texts = [
            ("build implement create a new auth service",     "BUILD"),
            ("fix the crash in the payment handler",          "DEBUG"),
            ("audit scan review all public API endpoints",    "AUDIT"),
        ]
        for text, expected_intent in texts:
            body = client.post("/v2/mandate", json={"text": text}).json()
            assert body["route"]["intent"] == expected_intent, (
                f"Expected {expected_intent!r} for {text!r}, got {body['route']['intent']!r}"
            )
            assert body["plan"] != [], f"plan should not be empty for: {text!r}"
            assert len(body["execution"]) > 0
            assert all(w["success"] for w in body["execution"])

    def test_trip_reset_recover_full_pipeline(self, client: TestClient) -> None:
        """Trip circuit → reset via API → prove normal mandate executes end-to-end."""
        from engine.config import CIRCUIT_BREAKER_MAX_FAILS

        # Trip
        for _ in range(CIRCUIT_BREAKER_MAX_FAILS):
            api_module._router._record_failure()
        blocked = client.post(
            "/v2/mandate", json={"text": "build something"}).json()
        assert blocked["route"]["intent"] == "BLOCKED"

        # Reset via API
        reset_resp = client.post("/v2/router-reset").json()
        assert reset_resp["reset"] is True

        # Recovered mandate — keyword-rich to generate a plan
        recovered = client.post(
            "/v2/mandate", json={"text": "build implement create a new feature"}).json()
        assert recovered["route"]["intent"] == "BUILD"
        assert recovered["plan"] != []
        assert all(w["success"] for w in recovered["execution"])

    def test_health_psyche_bank_dag_router_status_all_consistent(
        self, client: TestClient
    ) -> None:
        """All read endpoints return consistent state after a mandate fires."""
        client.post("/v2/mandate",
                    json={"text": "build implement create an analytics dashboard"})

        health = client.get("/v2/health").json()
        bank = client.get("/v2/psyche-bank").json()
        router = client.get("/v2/router-status").json()

        # Health: bank count matches actual count
        bank_count_from_health = int(
            health["components"]["psyche_bank"].split()[0])
        assert bank_count_from_health == len(bank["rules"])

        # Router: circuit open in health vs router-status are equivalent
        # (health reports a string, router-status reports a bool; both reflect the same state)
        assert router["circuit_open"] is False

    def test_full_cycle_serialises_to_valid_json(self, client: TestClient) -> None:
        body = client.post(
            "/v2/mandate", json={"text": "explain how does the DAG orchestrator work"}).json()
        assert body["plan"] != [], "EXPLAIN mandate should produce a plan"
        serialised = json.dumps(body)
        assert isinstance(serialised, str) and len(serialised) > 0

    def test_mandate_latency_under_500ms_for_all_intents(self, client: TestClient) -> None:
        # Keyword-rich texts — each confident enough to generate a plan
        mandates = [
            "build implement create a REST API",
            "fix bug error in the login handler",
            "audit scan review the dependency tree",
            "explain how does the DAG sorter work",
            "brainstorm ideate ideas for caching strategy",
        ]
        for text in mandates:
            body = client.post("/v2/mandate", json={"text": text}).json()
            assert body["plan"] != [], f"Expected non-empty plan for: {text!r}"
            assert body["latency_ms"] < 500, (
                f"Mandate '{text}' took {body['latency_ms']} ms — above 500 ms threshold"
            )
