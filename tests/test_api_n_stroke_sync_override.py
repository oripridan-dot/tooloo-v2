"""
tests/test_api_n_stroke_sync_override.py — Regression guard for Bug #10.

Bug #10 (fixed 2026-03-20): when POST /v2/n-stroke received max_strokes != 7,
the override NStrokeEngine was constructed without async_fluid_executor.
This file ensures the fix holds across future refactors.

Tests:
  test_default_max_strokes_200       — POST /v2/n-stroke default max_strokes=7 → 200
  test_override_max_strokes_200      — max_strokes=1 override → 200 + correct shape
  test_override_respects_max_strokes — total_strokes <= max_strokes
  test_sync_result_no_execution_mode_async — result.execution_mode == "sync"
  test_sync_pipeline_id_prefix       — pipeline_id starts with "ns-" (not "ns-async-")
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


_PAYLOAD_DEFAULT: dict[str, Any] = {
    "intent": "BUILD",
    "confidence": 0.95,
    "value_statement": "Regression guard — default strokes.",
    "constraint_summary": "offline tests",
    "mandate_text": "build implement create add write generate",
}

_PAYLOAD_OVERRIDE: dict[str, Any] = {
    **_PAYLOAD_DEFAULT,
    "max_strokes": 1,
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from studio.api import app
    return TestClient(app)


class TestNStrokeSyncOverride:
    """Guard Bug #10 — async_fluid_executor propagates to override engine instances."""

    def test_default_max_strokes_200(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json=_PAYLOAD_DEFAULT)
        assert resp.status_code == 200, resp.text

    def test_default_response_shape(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json=_PAYLOAD_DEFAULT)
        body = resp.json()
        assert "pipeline_id" in body
        assert "result" in body
        assert "latency_ms" in body

    def test_override_max_strokes_200(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json=_PAYLOAD_OVERRIDE)
        assert resp.status_code == 200, resp.text

    def test_override_respects_max_strokes(self, client: TestClient) -> None:
        payload = {**_PAYLOAD_DEFAULT, "max_strokes": 2}
        resp = client.post("/v2/n-stroke", json=payload)
        body = resp.json()
        assert body["result"]["total_strokes"] <= 2

    def test_sync_result_execution_mode_is_sync(self, client: TestClient) -> None:
        """result.execution_mode must be 'sync' on the sync path (Bug #10 guard)."""
        resp = client.post("/v2/n-stroke", json=_PAYLOAD_OVERRIDE)
        body = resp.json()
        assert body["result"]["execution_mode"] == "sync"

    def test_sync_pipeline_id_prefix(self, client: TestClient) -> None:
        """Sync pipeline IDs start with 'ns-', not 'ns-async-'."""
        resp = client.post("/v2/n-stroke", json=_PAYLOAD_OVERRIDE)
        body = resp.json()
        pid = body["pipeline_id"]
        assert pid.startswith(
            "ns-"), f"Expected sync prefix 'ns-', got: {pid!r}"
        assert not pid.startswith(
            "ns-async-"), f"Sync ID must not use async prefix, got: {pid!r}"

    def test_sync_override_final_verdict_present(self, client: TestClient) -> None:
        resp = client.post("/v2/n-stroke", json=_PAYLOAD_OVERRIDE)
        body = resp.json()
        assert body["result"]["final_verdict"] in ("pass", "warn", "fail")
