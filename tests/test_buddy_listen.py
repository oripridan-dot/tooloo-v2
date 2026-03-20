"""tests/test_buddy_listen.py — Tests for the /v2/buddy/listen active-listener endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from studio.api import app

client = TestClient(app)


class TestBuddyListenEndpoint:
    """HTTP contract tests for POST /v2/buddy/listen."""

    def test_returns_200_on_valid_text(self):
        r = client.post("/v2/buddy/listen", json={"text": "build a REST API"})
        assert r.status_code == 200

    def test_response_has_required_keys(self):
        r = client.post("/v2/buddy/listen",
                        json={"text": "explain how OAuth2 works"})
        data = r.json()
        for key in ("comprehension_level", "visual_indicator", "prompt_suggestions",
                    "detected_intent", "word_count"):
            assert key in data, f"Missing key: {key}"

    def test_empty_text_returns_200(self):
        r = client.post("/v2/buddy/listen", json={"text": ""})
        assert r.status_code == 200

    def test_empty_text_is_listening(self):
        r = client.post("/v2/buddy/listen", json={"text": ""})
        data = r.json()
        assert data["comprehension_level"] in ("listening", "vague")

    def test_clear_prompt_comprehension_level(self):
        r = client.post(
            "/v2/buddy/listen",
            json={
                "text": "build me a FastAPI service with JWT authentication and PostgreSQL"},
        )
        data = r.json()
        assert data["comprehension_level"] in ("clear", "complex", "listening")

    def test_prompt_suggestions_is_list(self):
        r = client.post("/v2/buddy/listen", json={"text": "fix my code"})
        assert isinstance(r.json()["prompt_suggestions"], list)

    def test_word_count_matches_input(self):
        text = "explain the authentication flow"
        r = client.post("/v2/buddy/listen", json={"text": text})
        assert r.json()["word_count"] == len(text.split())

    def test_visual_indicator_valid_values(self):
        r = client.post("/v2/buddy/listen",
                        json={"text": "audit the security pipeline"})
        valid = {"nodding", "thinking", "listening", "confused_tilt"}
        assert r.json()["visual_indicator"] in valid

    def test_text_too_long_rejected(self):
        """Max length is 2000 chars — over-limit should return 422."""
        r = client.post("/v2/buddy/listen", json={"text": "x" * 2001})
        assert r.status_code == 422

    def test_missing_text_field_uses_default(self):
        """text has a default of '' so an empty body should be accepted."""
        r = client.post("/v2/buddy/listen", json={})
        assert r.status_code == 200

    def test_non_string_text_rejected(self):
        r = client.post("/v2/buddy/listen", json={"text": 42})
        # FastAPI coerces numbers to string — either 200 or 422 is acceptable
        # but must not 500
        assert r.status_code in (200, 422)

    def test_debug_intent_detectable(self):
        r = client.post(
            "/v2/buddy/listen",
            json={"text": "debug the null exception in authentication module"},
        )
        data = r.json()
        assert data["detected_intent"] in (
            "DEBUG", "BUILD", "EXPLAIN", "AUDIT", "DESIGN", "IDEATE"
        )

    def test_vague_prompt_returns_vague_or_listening(self):
        r = client.post("/v2/buddy/listen", json={"text": "help"})
        data = r.json()
        assert data["comprehension_level"] in ("vague", "listening")

    def test_response_is_pure_json(self):
        r = client.post("/v2/buddy/listen", json={"text": "build an API"})
        assert r.headers["content-type"].startswith("application/json")
