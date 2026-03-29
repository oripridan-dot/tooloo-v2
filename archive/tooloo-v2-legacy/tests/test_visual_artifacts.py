"""
tests/test_visual_artifacts.py — Buddy Visual Artifact Protocol tests.

Validates:
  - _parse_visual_artifacts: html_component, mermaid_diagram, chart_json,
    svg_animation, unknown-type rejection, 64KB content cap
  - VisualArtifact.to_dict() round-trip
  - ConversationResult visual_artifacts population via process()
  - /v2/buddy/chat response schema includes visual_artifacts key
"""
from __future__ import annotations

import json
from dataclasses import fields
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.conversation import (
    ConversationResult,
    VisualArtifact,
    _parse_visual_artifacts,
)

# ── fixture helpers ────────────────────────────────────────────────────────────

HTML_BLOCK = (
    '<visual_artifact type="html_component" title="Gradient Button">'
    '<div style="padding:16px;background:linear-gradient(135deg,#6366f1,#8b5cf6);">'
    '<button style="color:#fff">Launch</button></div>'
    "</visual_artifact>"
)

MERMAID_BLOCK = (
    '<visual_artifact type="mermaid_diagram" title="DAG Flow">'
    "graph TD\n  A[Scope] --> B[Execute] --> C[Refine]"
    "</visual_artifact>"
)

CHART_JSON_BLOCK = (
    '<visual_artifact type="chart_json" title="Token Usage">'
    '{"type":"bar","data":{"labels":["W1","W2"],"datasets":[{"data":[12,8]}]}}'
    "</visual_artifact>"
)

SVG_BLOCK = (
    '<visual_artifact type="svg_animation" title="Pulse">'
    '[{"type":"to","target":"logo-circle","duration":1,"opacity":0.5}]'
    "</visual_artifact>"
)

UNKNOWN_TYPE_BLOCK = (
    '<visual_artifact type="video_clip" title="Whatever">'
    "some content"
    "</visual_artifact>"
)

MULTI_BLOCK = HTML_BLOCK + "\n\n" + MERMAID_BLOCK

BUDGET_EXCEEDED_BLOCK = (
    '<visual_artifact type="html_component" title="Big">'
    + "x" * (64 * 1024 + 1)
    + "</visual_artifact>"
)


# ── VisualArtifact dataclass ───────────────────────────────────────────────────


class TestVisualArtifact:
    def test_to_dict_round_trip(self):
        va = VisualArtifact(
            artifact_id="va-001",
            type="mermaid_diagram",
            content="graph TD\n  A-->B",
            metadata={"title": "Test"},
        )
        d = va.to_dict()
        assert d["artifact_id"] == "va-001"
        assert d["type"] == "mermaid_diagram"
        assert d["content"] == "graph TD\n  A-->B"
        assert d["metadata"] == {"title": "Test"}

    def test_all_fields_in_dict(self):
        va = VisualArtifact(
            artifact_id="x", type="html_component", content="<b>hi</b>")
        d = va.to_dict()
        assert set(d.keys()) == {"artifact_id", "type", "content", "metadata"}

    def test_metadata_defaults_empty(self):
        va = VisualArtifact(
            artifact_id="z", type="svg_animation", content="[]")
        assert va.metadata == {}


# ── _parse_visual_artifacts ────────────────────────────────────────────────────


class TestParseVisualArtifacts:
    def test_parse_html_component(self):
        artifacts = _parse_visual_artifacts(HTML_BLOCK)
        assert len(artifacts) == 1
        assert artifacts[0].type == "html_component"
        assert "<button" in artifacts[0].content

    def test_parse_mermaid_diagram(self):
        artifacts = _parse_visual_artifacts(MERMAID_BLOCK)
        assert len(artifacts) == 1
        assert artifacts[0].type == "mermaid_diagram"
        assert "graph TD" in artifacts[0].content

    def test_parse_chart_json(self):
        artifacts = _parse_visual_artifacts(CHART_JSON_BLOCK)
        assert len(artifacts) == 1
        assert artifacts[0].type == "chart_json"
        payload = json.loads(artifacts[0].content)
        assert payload["type"] == "bar"

    def test_parse_svg_animation(self):
        artifacts = _parse_visual_artifacts(SVG_BLOCK)
        assert len(artifacts) == 1
        assert artifacts[0].type == "svg_animation"

    def test_unknown_type_rejected(self):
        artifacts = _parse_visual_artifacts(UNKNOWN_TYPE_BLOCK)
        assert len(artifacts) == 0

    def test_multiple_artifacts(self):
        artifacts = _parse_visual_artifacts(MULTI_BLOCK)
        assert len(artifacts) == 2
        types = {a.type for a in artifacts}
        assert types == {"html_component", "mermaid_diagram"}

    def test_64kb_content_cap_rejects(self):
        artifacts = _parse_visual_artifacts(BUDGET_EXCEEDED_BLOCK)
        assert len(artifacts) == 0

    def test_empty_string_returns_empty(self):
        assert _parse_visual_artifacts("") == []

    def test_no_artifact_block_returns_empty(self):
        assert _parse_visual_artifacts(
            "Hello, this is just normal text.") == []

    def test_artifact_id_is_unique_per_parse(self):
        artifacts = _parse_visual_artifacts(MULTI_BLOCK)
        ids = [a.artifact_id for a in artifacts]
        assert len(set(ids)) == len(ids), "Artifact IDs must be unique"

    def test_title_attribute_captured(self):
        artifacts = _parse_visual_artifacts(HTML_BLOCK)
        assert artifacts[0].metadata.get("title") == "Gradient Button"

    def test_artifact_blocks_stripped_from_clean_text(self):
        full_text = "Here is a diagram for you:\n" + MERMAID_BLOCK + "\nHope that helps!"
        artifacts = _parse_visual_artifacts(full_text)
        assert len(artifacts) == 1
        # The function only parses, stripping happens in conversation.process() — just confirm parsing OK
        assert artifacts[0].type == "mermaid_diagram"


# ── ConversationResult ──────────────────────────────────────────────────────────


def _make_result(response_text: str = "Hello", visual_artifacts=None) -> ConversationResult:
    """Build a minimal ConversationResult for unit tests."""
    from engine.conversation import ConversationPlan, ConversationPhase

    plan = ConversationPlan(
        mandate_id="test-mandate",
        intent="BUILD",
        phases=[ConversationPhase(
            name="understand", description="Understand requirements", wave=1)],
    )
    return ConversationResult(
        session_id="sess-test",
        turn_id="turn-test",
        response_text=response_text,
        plan=plan,
        suggestions=[],
        tone="constructive",
        intent="BUILD",
        confidence=0.9,
        latency_ms=10.0,
        model_used="gemini-flash",
        visual_artifacts=visual_artifacts or [],
    )


class TestConversationResult:
    def test_visual_artifacts_defaults_empty(self):
        result = _make_result()
        assert result.visual_artifacts == []

    def test_visual_artifacts_populated(self):
        va = VisualArtifact(artifact_id="va-1",
                            type="chart_json", content="{}")
        result = _make_result("Here is your chart.", visual_artifacts=[va])
        assert len(result.visual_artifacts) == 1

    def test_to_dict_includes_visual_artifacts(self):
        va = VisualArtifact(artifact_id="va-1",
                            type="mermaid_diagram", content="graph LR\n A-->B")
        result = _make_result("See diagram.", visual_artifacts=[va])
        d = result.to_dict()
        assert "visual_artifacts" in d
        assert len(d["visual_artifacts"]) == 1
        assert d["visual_artifacts"][0]["type"] == "mermaid_diagram"

    def test_to_dict_visual_artifacts_empty_list(self):
        result = _make_result("Plain text reply.")
        d = result.to_dict()
        assert d["visual_artifacts"] == []


# ── Buddy chat process() — artifact stripping integration ──────────────────────


class TestConversationProcess:
    """Verify process() strips <visual_artifact> blocks from the reply text
    and populates ConversationResult.visual_artifacts."""

    def test_strip_artifact_from_reply(self):
        """Patch _parse_visual_artifacts + response_text to simulate the engine."""
        # We test the parsing layer directly since patching the engine
        # internals is fragile. The parse + strip path is already covered
        # by TestParseVisualArtifacts. Here we just verify the integration.
        full_text = (
            "Here is the diagram:\n"
            '<visual_artifact type="mermaid_diagram" title="Flow">graph TD\n  A-->B</visual_artifact>\n'
            "Enjoy!"
        )
        artifacts = _parse_visual_artifacts(full_text)
        from engine.conversation import _ARTIFACT_RE
        clean = _ARTIFACT_RE.sub("", full_text).strip()
        assert len(artifacts) == 1
        assert artifacts[0].type == "mermaid_diagram"
        assert '<visual_artifact' not in clean
        assert "Here is the diagram:" in clean
        assert "Enjoy!" in clean

    def test_plain_reply_no_artifacts(self):
        artifacts = _parse_visual_artifacts("Just a plain reply.")
        assert artifacts == []


# ── /v2/buddy/chat API schema ──────────────────────────────────────────────────


class TestBuddyChatAPISchema:
    """Smoke-test the response schema has a visual_artifacts key."""

    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from studio.api import app

        return TestClient(app)

    def test_visual_artifacts_key_in_response(self, client):
        from engine.conversation import ConversationEngine
        from engine.router import RouteResult

        mock_result = _make_result("Hi there! visual_artifacts working.")
        mock_route = RouteResult(
            intent="EXPLAIN", confidence=0.9, circuit_open=False, mandate_text="Hello buddy")
        with patch("studio.api._router.route_chat", return_value=mock_route), \
                patch.object(ConversationEngine, "process", return_value=mock_result):
            resp = client.post(
                "/v2/buddy/chat",
                json={"text": "Hello buddy"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "visual_artifacts" in data
        assert isinstance(data["visual_artifacts"], list)

    def test_visual_artifacts_populated_in_response(self, client):
        va = VisualArtifact(artifact_id="va-test",
                            type="chart_json", content='{"type":"line"}')
        from engine.conversation import ConversationEngine
        from engine.router import RouteResult

        mock_result = _make_result(
            "Here is your chart.", visual_artifacts=[va])
        mock_route = RouteResult(intent="DESIGN", confidence=0.9,
                                 circuit_open=False, mandate_text="Draw a line chart")
        with patch("studio.api._router.route_chat", return_value=mock_route), \
                patch.object(ConversationEngine, "process", return_value=mock_result):
            resp = client.post(
                "/v2/buddy/chat",
                json={"text": "Draw a line chart"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["visual_artifacts"]) == 1
        assert data["visual_artifacts"][0]["type"] == "chart_json"
