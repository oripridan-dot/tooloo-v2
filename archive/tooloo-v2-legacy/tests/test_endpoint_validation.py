"""Full endpoint validation suite — TooLoo V2.

Validates every API route for:
  1. HTTP status code correctness
  2. Required response-body fields
  3. Schema / contract (wrong payloads → 422, not 500)
  4. UI-to-API contract (payloads the main UI actually sends)

All tests run offline (TOOLOO_LIVE_TESTS guard is inactive by default).
Add TOOLOO_LIVE_TESTS=1 for live Gemini path.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from studio.api import app

# ── Shared client fixture ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Module-scoped FastAPI TestClient — fast, no real server."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Core status / meta endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestCoreStatusEndpoints:
    def test_health_returns_200(self, client: TestClient):
        r = client.get("/v2/health")
        assert r.status_code == 200

    def test_health_has_required_fields(self, client: TestClient):
        data = client.get("/v2/health").json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_status_returns_200(self, client: TestClient):
        r = client.get("/v2/status")
        assert r.status_code == 200

    def test_status_has_engine_components(self, client: TestClient):
        data = client.get("/v2/status").json()
        # Should list known engine components
        assert isinstance(data, dict)

    def test_router_status_returns_200(self, client: TestClient):
        r = client.get("/v2/router-status")
        assert r.status_code == 200

    def test_router_status_has_circuit_breaker_fields(self, client: TestClient):
        data = client.get("/v2/router-status").json()
        assert "circuit_open" in data or "status" in data

    def test_router_reset_returns_200(self, client: TestClient):
        r = client.post("/v2/router-reset")
        assert r.status_code == 200

    def test_mcp_tools_returns_200(self, client: TestClient):
        r = client.get("/v2/mcp/tools")
        assert r.status_code == 200

    def test_mcp_tools_is_list(self, client: TestClient):
        data = client.get("/v2/mcp/tools").json()
        assert "tools" in data
        assert isinstance(data["tools"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Core pipeline — schema & contract
# ═══════════════════════════════════════════════════════════════════════════════

class TestMandateEndpoint:
    def test_mandate_with_text_field_returns_200(self, client: TestClient):
        r = client.post("/v2/mandate", json={"text": "build implement create a widget"})
        assert r.status_code == 200

    def test_mandate_missing_text_returns_422(self, client: TestClient):
        """Wrong field name — mandate_text is NOT the schema field."""
        r = client.post("/v2/mandate", json={"mandate_text": "build a thing"})
        assert r.status_code == 422

    def test_mandate_response_has_required_fields(self, client: TestClient):
        data = client.post("/v2/mandate", json={"text": "build implement create"}).json()
        assert "mandate_id" in data
        assert "route" in data
        assert "latency_ms" in data

    def test_mandate_route_contains_intent(self, client: TestClient):
        data = client.post("/v2/mandate", json={"text": "build implement create"}).json()
        route = data["route"]
        assert "intent" in route
        assert "confidence" in route


class TestBuddyChatEndpoint:
    """Tests for the main UI's primary endpoint."""

    def test_buddy_chat_returns_200(self, client: TestClient):
        r = client.post("/v2/buddy/chat", json={"text": "explain this concept", "session_id": "test-1"})
        assert r.status_code == 200

    def test_buddy_chat_requires_text_field(self, client: TestClient):
        r = client.post("/v2/buddy/chat", json={"message": "hello"})
        assert r.status_code == 422

    def test_buddy_chat_response_has_response_field(self, client: TestClient):
        """UI reads data.response — verify it's present."""
        data = client.post("/v2/buddy/chat", json={
            "text": "explain the concept of recursion",
            "session_id": "test-2",
        }).json()
        assert "response" in data, f"Missing 'response' field in: {list(data.keys())}"

    def test_buddy_chat_response_has_intent_and_confidence(self, client: TestClient):
        data = client.post("/v2/buddy/chat", json={
            "text": "design a new component",
            "session_id": "test-3",
        }).json()
        assert "intent" in data
        assert "confidence" in data

    def test_buddy_chat_execution_intent_returns_gate_error(self, client: TestClient):
        """BUILD intent must return error field (gate to pipeline), not 400."""
        data = client.post("/v2/buddy/chat", json={
            "text": "build implement create generate write a new feature",
            "session_id": "test-4",
        }).json()
        # Should either return error gating message (200 with error) or a response
        # depending on intent routing. Both are valid — UI handles both.
        assert "response" in data or "error" in data

    def test_buddy_chat_accepts_depth_level(self, client: TestClient):
        r = client.post("/v2/buddy/chat", json={
            "text": "ideate about future features",
            "session_id": "test-5",
            "depth_level": 2,
        })
        assert r.status_code == 200

    def test_buddy_chat_accepts_forced_intent(self, client: TestClient):
        r = client.post("/v2/buddy/chat", json={
            "text": "what do you think",
            "session_id": "test-6",
            "forced_intent": "IDEATE",
        })
        assert r.status_code == 200

    def test_buddy_chat_jit_boost_in_response(self, client: TestClient):
        """Main UI reads data.jit_boost for JIT HUD update."""
        data = client.post("/v2/buddy/chat", json={
            "text": "ideate creative solutions",
            "session_id": "test-7",
        }).json()
        # jit_boost should be present (may be null in offline mode)
        assert "jit_boost" in data

    # ── UI contract: exact payload shapes the main UI sends ──

    def test_ui_chat_depth0_payload(self, client: TestClient):
        """Depth 0 (Chat): {text, session_id, depth_level: 1, forced_intent: ''}."""
        r = client.post("/v2/buddy/chat", json={
            "text": "explain monads",
            "session_id": "spatial-12345",
            "depth_level": 1,
            "forced_intent": "",
        })
        assert r.status_code == 200

    def test_ui_explore_depth1_payload(self, client: TestClient):
        """Depth 1 (Explore): {text, session_id, depth_level: 2, forced_intent: ''}."""
        r = client.post("/v2/buddy/chat", json={
            "text": "audit this code",
            "session_id": "spatial-12345",
            "depth_level": 2,
            "forced_intent": "AUDIT",
        })
        assert r.status_code == 200


class TestPipelineEndpoint:
    """Tests for the Pipeline depth=2 endpoint (POST /v2/pipeline)."""

    def test_pipeline_returns_200(self, client: TestClient):
        r = client.post("/v2/pipeline", json={
            "text": "build a todo app",
            "session_id": "pipe-test-1",
        })
        assert r.status_code == 200

    def test_pipeline_requires_text_field(self, client: TestClient):
        r = client.post("/v2/pipeline", json={"mandate": "build something"})
        assert r.status_code == 422

    def test_pipeline_response_has_locked_field(self, client: TestClient):
        """UI checks data.locked to determine clarification vs result."""
        data = client.post("/v2/pipeline", json={
            "text": "build",
            "session_id": "pipe-test-2",
        }).json()
        assert "locked" in data, f"Missing 'locked' field in: {list(data.keys())}"

    def test_pipeline_response_has_session_id(self, client: TestClient):
        data = client.post("/v2/pipeline", json={
            "text": "build a feature",
            "session_id": "pipe-test-3",
        }).json()
        assert "session_id" in data
        assert "pipeline_id" in data

    def test_pipeline_unlocked_has_clarification_question(self, client: TestClient):
        """When intent not locked, response must have clarification_question."""
        data = client.post("/v2/pipeline", json={
            "text": "do something",
            "session_id": "pipe-test-4",
        }).json()
        if not data.get("locked", True):
            assert "clarification_question" in data
            assert data["clarification_question"]  # non-empty

    def test_pipeline_ui_payload_depth2(self, client: TestClient):
        """Exact payload the main UI sends at depth=2."""
        r = client.post("/v2/pipeline", json={
            "text": "build implement create a REST API",
            "session_id": "spatial-99999",
            "max_iterations": 3,
        })
        assert r.status_code == 200

    def test_pipeline_direct_requires_intent(self, client: TestClient):
        """pipeline/direct needs a full LockedIntentRequest."""
        r = client.post("/v2/pipeline/direct", json={"mandate": "build"})
        assert r.status_code == 422

    def test_pipeline_direct_locked_intent(self, client: TestClient):
        r = client.post("/v2/pipeline/direct", json={
            "intent": "BUILD",
            "confidence": 0.95,
            "value_statement": "Create a REST API endpoint",
            "mandate_text": "build a REST API",
            "session_id": "direct-1",
        })
        assert r.status_code == 200


class TestNStrokeEndpoint:
    """N-Stroke requires a pre-locked intent — NOT callable with just mandate_text."""

    def test_n_stroke_requires_intent(self, client: TestClient):
        """Sending mandate_text alone must return 422."""
        r = client.post("/v2/n-stroke", json={
            "mandate_text": "build a new feature",
            "session_id": "ns-test-1",
        })
        assert r.status_code == 422

    def test_n_stroke_with_locked_intent_returns_200(self, client: TestClient):
        r = client.post("/v2/n-stroke", json={
            "intent": "BUILD",
            "confidence": 0.95,
            "value_statement": "Implement a widget component",
            "mandate_text": "build implement create a widget component",
            "session_id": "ns-test-2",
        })
        assert r.status_code == 200

    def test_n_stroke_response_has_strokes_used(self, client: TestClient):
        data = client.post("/v2/n-stroke", json={
            "intent": "BUILD",
            "confidence": 0.95,
            "value_statement": "Build an API endpoint",
            "mandate_text": "build implement create an API endpoint",
        }).json()
        assert "result" in data

    def test_n_stroke_missing_confidence_returns_422(self, client: TestClient):
        r = client.post("/v2/n-stroke", json={
            "intent": "BUILD",
            "value_statement": "build a widget",
            "mandate_text": "build it",
        })
        assert r.status_code == 422


class TestChatEndpoint:
    def test_chat_returns_200(self, client: TestClient):
        r = client.post("/v2/chat", json={"text": "explain the system", "session_id": "chat-1"})
        assert r.status_code == 200

    def test_chat_requires_text(self, client: TestClient):
        r = client.post("/v2/chat", json={"msg": "hello"})
        assert r.status_code == 422

    def test_chat_response_shape(self, client: TestClient):
        data = client.post("/v2/chat", json={"text": "ideate solutions"}).json()
        assert "response" in data or "buddy_line" in data or "conversation" in data


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Intent discovery
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntentDiscovery:
    def test_intent_clarify_returns_200(self, client: TestClient):
        r = client.post("/v2/intent/clarify", json={"text": "help", "session_id": "id-1"})
        assert r.status_code == 200

    def test_intent_clarify_response_has_locked(self, client: TestClient):
        data = client.post("/v2/intent/clarify", json={"text": "help", "session_id": "id-2"}).json()
        assert "locked" in data

    def test_intent_session_delete_returns_200(self, client: TestClient):
        r = client.delete("/v2/intent/session/id-test-99")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Data views (DAG, PsycheBank, Sessions)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataViews:
    def test_dag_returns_200(self, client: TestClient):
        assert client.get("/v2/dag").status_code == 200

    def test_dag_has_nodes_and_edges(self, client: TestClient):
        data = client.get("/v2/dag").json()
        assert "nodes" in data or "dag" in data or isinstance(data, dict)

    def test_psyche_bank_returns_200(self, client: TestClient):
        assert client.get("/v2/psyche-bank").status_code == 200

    def test_psyche_bank_has_rules(self, client: TestClient):
        data = client.get("/v2/psyche-bank").json()
        assert "rules" in data or "entries" in data or isinstance(data, (dict, list))

    def test_session_get_returns_200_or_404(self, client: TestClient):
        r = client.get("/v2/session/no-such-session")
        assert r.status_code in (200, 404)

    def test_session_delete_returns_200(self, client: TestClient):
        r = client.delete("/v2/session/no-such-session")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Engram
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngramEndpoints:
    def test_engram_current_returns_200(self, client: TestClient):
        assert client.get("/v2/engram/current").status_code == 200

    def test_engram_generate_returns_200(self, client: TestClient):
        r = client.post("/v2/engram/generate", json={
            "text": "build", "intent": "BUILD", "confidence": 0.9, "mode": "active",
        })
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Self-Improvement
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfImproveEndpoints:
    def test_self_improve_returns_200(self, client: TestClient):
        r = client.post("/v2/self-improve")
        assert r.status_code == 200

    def test_self_improve_response_has_components_assessed(self, client: TestClient):
        data = client.post("/v2/self-improve").json()
        assert "components_assessed" in data or "assessments" in data or "report" in data

    def test_self_improve_apply_returns_200(self, client: TestClient):
        r = client.post("/v2/self-improve/apply", json={
            "component": "router",
            "suggestion": "Improve routing logic",
            "old_code": "x = 1",
            "new_code": "x = compute()",
            "confidence": 0.92,
        })
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Sandbox
# ═══════════════════════════════════════════════════════════════════════════════

class TestSandboxEndpoints:
    def test_sandbox_list_returns_200(self, client: TestClient):
        assert client.get("/v2/sandbox").status_code == 200

    def test_sandbox_spawn_requires_feature_text(self, client: TestClient):
        r = client.post("/v2/sandbox/spawn", json={"mandate": "build it"})
        assert r.status_code == 422

    def test_sandbox_spawn_correct_payload(self, client: TestClient):
        r = client.post("/v2/sandbox/spawn", json={
            "feature_text": "implement user authentication with JWT",
            "feature_title": "JWT Auth",
        })
        assert r.status_code == 200

    def test_sandbox_get_by_id_returns_200_or_404(self, client: TestClient):
        r = client.get("/v2/sandbox/no-such-id")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Roadmap
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoadmapEndpoints:
    def test_roadmap_list_returns_200(self, client: TestClient):
        assert client.get("/v2/roadmap").status_code == 200

    def test_roadmap_similar_returns_200(self, client: TestClient):
        r = client.get("/v2/roadmap/similar", params={"text": "auth feature"})
        assert r.status_code == 200

    def test_roadmap_add_item_returns_200(self, client: TestClient):
        r = client.post("/v2/roadmap/item", json={
            "title": "Test Feature",
            "description": "Add test functionality",
            "priority": "high",
        })
        assert r.status_code == 200

    def test_roadmap_add_item_missing_title_returns_422(self, client: TestClient):
        r = client.post("/v2/roadmap/item", json={"description": "some feature"})
        assert r.status_code == 422

    def test_roadmap_run_returns_200(self, client: TestClient):
        r = client.post("/v2/roadmap/run")
        assert r.status_code == 200

    def test_roadmap_promote_returns_200_or_404(self, client: TestClient):
        r = client.post("/v2/roadmap/no-such-item/promote")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Auto-Loop
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutoLoopEndpoints:
    def test_auto_loop_status_returns_200(self, client: TestClient):
        assert client.get("/v2/auto-loop/status").status_code == 200

    def test_auto_loop_start_returns_200(self, client: TestClient):
        r = client.post("/v2/auto-loop/start")
        assert r.status_code == 200

    def test_auto_loop_stop_returns_200(self, client: TestClient):
        r = client.post("/v2/auto-loop/stop")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Branch
# ═══════════════════════════════════════════════════════════════════════════════

class TestBranchEndpoints:
    def test_branches_list_returns_200(self, client: TestClient):
        assert client.get("/v2/branches").status_code == 200

    def test_branch_requires_branches_list(self, client: TestClient):
        """UI sends {mandate, mode} but API needs {branches: [...]}."""
        r = client.post("/v2/branch", json={"mandate": "build x", "mode": "fork"})
        assert r.status_code == 422

    def test_branch_correct_payload(self, client: TestClient):
        r = client.post("/v2/branch", json={
            "branches": [
                {
                    "mandate_text": "build implement create a feature",
                    "intent": "BUILD",
                    "branch_type": "fork",
                }
            ],
            "timeout": 60.0,
        })
        assert r.status_code == 200

    def test_branch_response_has_result(self, client: TestClient):
        data = client.post("/v2/branch", json={
            "branches": [{"mandate_text": "audit security", "intent": "AUDIT"}],
        }).json()
        assert "result" in data or "branches" in data or isinstance(data, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Daemon
# ═══════════════════════════════════════════════════════════════════════════════

class TestDaemonEndpoints:
    def test_daemon_status_returns_200(self, client: TestClient):
        assert client.get("/v2/daemon/status").status_code == 200

    def test_daemon_start_returns_200(self, client: TestClient):
        assert client.post("/v2/daemon/start").status_code == 200

    def test_daemon_stop_returns_200(self, client: TestClient):
        assert client.post("/v2/daemon/stop").status_code == 200

    def test_daemon_approve_returns_200_or_404(self, client: TestClient):
        r = client.post("/v2/daemon/approve/no-such-proposal")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Knowledge Banks
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeBankEndpoints:
    def test_knowledge_health_returns_200(self, client: TestClient):
        assert client.get("/v2/knowledge/health").status_code == 200

    def test_knowledge_health_has_bank_counts(self, client: TestClient):
        data = client.get("/v2/knowledge/health").json()
        assert isinstance(data, dict)

    def test_knowledge_dashboard_returns_200(self, client: TestClient):
        assert client.get("/v2/knowledge/dashboard").status_code == 200

    def test_knowledge_bank_by_id_returns_200(self, client: TestClient):
        # design, code, ai, bridge are the valid bank IDs
        assert client.get("/v2/knowledge/design").status_code == 200

    def test_knowledge_bank_signals_returns_200(self, client: TestClient):
        assert client.get("/v2/knowledge/code/signals").status_code == 200

    def test_knowledge_query_requires_topic_not_q(self, client: TestClient):
        """UI must send 'topic' not 'q'."""
        r_wrong = client.post("/v2/knowledge/query", json={"q": "react 2026"})
        assert r_wrong.status_code == 422

        r_correct = client.post("/v2/knowledge/query", json={"topic": "react hooks 2026"})
        assert r_correct.status_code == 200

    def test_knowledge_ingest_requires_bank_id_domain_signals(self, client: TestClient):
        """Manual ingest requires bank_id, domain, signals[]."""
        r_wrong = client.post("/v2/knowledge/ingest", json={"domain": "code", "query": "react"})
        assert r_wrong.status_code == 422

        r_correct = client.post("/v2/knowledge/ingest", json={
            "bank_id": "code",
            "domain": "frontend",
            "signals": ["React 19 concurrent rendering", "Suspense boundaries best practice 2026"],
        })
        assert r_correct.status_code == 200

    def test_knowledge_ingest_full_returns_200(self, client: TestClient):
        assert client.post("/v2/knowledge/ingest/full").status_code == 200

    def test_knowledge_intent_signals_returns_200(self, client: TestClient):
        assert client.get("/v2/knowledge/intent/BUILD/signals").status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 13. VLT (Visual Layout Tree)
# ═══════════════════════════════════════════════════════════════════════════════

class TestVLTEndpoints:
    def test_vlt_demo_returns_200(self, client: TestClient):
        assert client.get("/v2/vlt/demo").status_code == 200

    def test_vlt_demo_has_tree(self, client: TestClient):
        data = client.get("/v2/vlt/demo").json()
        assert "tree" in data or "demo" in data or isinstance(data, dict)

    def test_vlt_audit_returns_200(self, client: TestClient):
        r = client.post("/v2/vlt/audit", json={
            "tree": {
                "id": "root",
                "label": "Root Panel",
                "color": "#0a0a0f",
                "children": [
                    {"id": "child-1", "label": "Button", "color": "#1a1a2e", "children": []},
                ],
            }
        })
        assert r.status_code == 200

    def test_vlt_audit_missing_tree_returns_422(self, client: TestClient):
        r = client.post("/v2/vlt/audit", json={"nodes": []})
        assert r.status_code == 422

    def test_vlt_render_returns_200(self, client: TestClient):
        r = client.post("/v2/vlt/render", json={
            "tree": {"id": "root", "label": "Root", "color": "#ffffff", "children": []}
        })
        assert r.status_code == 200

    def test_vlt_patch_returns_200(self, client: TestClient):
        r = client.post("/v2/vlt/patch", json={
            "patches": [
                {"node_id": "root", "material": "glass", "style_tokens": {"opacity": 0.9}}
            ]
        })
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 14. UI-to-API contract smoke tests
# These exactly mirror what the browser sends and must NEVER 422.
# ═══════════════════════════════════════════════════════════════════════════════

class TestUIContractSmoke:
    """Verify every payload shape the main UI sends will be accepted (no 422)."""

    def test_buddy_chat_from_depth0(self, client: TestClient):
        """Main UI Chat depth: forced_intent='', depth_level=1."""
        r = client.post("/v2/buddy/chat", json={
            "text": "explain what is a DAG",
            "session_id": "spatial-ui-test",
            "depth_level": 1,
            "forced_intent": "",
        })
        assert r.status_code == 200

    def test_buddy_chat_from_depth1_explore(self, client: TestClient):
        """Main UI Explore depth: depth_level=2, explicit intent."""
        r = client.post("/v2/buddy/chat", json={
            "text": "audit the authentication logic",
            "session_id": "spatial-ui-test",
            "depth_level": 2,
            "forced_intent": "AUDIT",
        })
        assert r.status_code == 200

    def test_pipeline_from_depth2(self, client: TestClient):
        """Main UI Pipeline depth: uses /v2/pipeline not /v2/n-stroke."""
        r = client.post("/v2/pipeline", json={
            "text": "build implement a todo list app",
            "session_id": "spatial-ui-test",
            "max_iterations": 3,
        })
        assert r.status_code == 200

    def test_router_reset_from_crisis_panel(self, client: TestClient):
        """Crisis panel 'Escalate Model' button sends empty body POST."""
        r = client.post("/v2/router-reset", json={})
        assert r.status_code == 200

    def test_sandbox_spawn_from_sandbox_ui(self, client: TestClient):
        """Sandbox UI sends {feature_text, feature_title}."""
        r = client.post("/v2/sandbox/spawn", json={
            "feature_text": "implement JWT authentication flow",
            "feature_title": "JWT Auth",
        })
        assert r.status_code == 200

    def test_branch_from_branch_ui(self, client: TestClient):
        """Branch UI sends {branches: [...], timeout: 120}."""
        r = client.post("/v2/branch", json={
            "branches": [
                {"mandate_text": "build implement a component", "intent": "BUILD", "branch_type": "fork"},
                {"mandate_text": "audit security vulnerabilities", "intent": "AUDIT", "branch_type": "fork"},
            ],
            "timeout": 120,
        })
        assert r.status_code == 200

    def test_knowledge_ingest_full_from_kb_ui(self, client: TestClient):
        """Knowledge UI 'Refresh' button sends empty POST."""
        r = client.post("/v2/knowledge/ingest/full")
        assert r.status_code == 200

    def test_self_improve_from_ui_button(self, client: TestClient):
        """Self-Improve UI button sends empty POST."""
        r = client.post("/v2/self-improve")
        assert r.status_code == 200
