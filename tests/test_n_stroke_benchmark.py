"""tests/test_n_stroke_benchmark.py — Wave C: GET /v2/n-stroke/benchmark tests.

Validates the benchmark endpoint that compares sync vs async N-Stroke latency.
All tests use the offline fast-path (no TOOLOO_LIVE_TESTS required).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client() -> TestClient:
    from studio.api import app
    return TestClient(app)


class TestNStrokeBenchmark:
    """Tests for GET /v2/n-stroke/benchmark."""

    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/v2/n-stroke/benchmark")
        assert resp.status_code == 200

    def test_response_has_required_keys(self, client: TestClient) -> None:
        body = client.get("/v2/n-stroke/benchmark").json()
        for key in ("sync_ms", "async_ms", "delta_ms", "faster"):
            assert key in body, f"Missing key: {key}"

    def test_latencies_are_non_negative(self, client: TestClient) -> None:
        body = client.get("/v2/n-stroke/benchmark").json()
        assert body["sync_ms"] >= 0.0
        assert body["async_ms"] >= 0.0

    def test_delta_ms_is_consistent(self, client: TestClient) -> None:
        """delta_ms should equal sync_ms - async_ms (within float rounding)."""
        body = client.get("/v2/n-stroke/benchmark").json()
        assert abs(body["delta_ms"] -
                   round(body["sync_ms"] - body["async_ms"], 2)) < 0.1

    def test_faster_is_valid_value(self, client: TestClient) -> None:
        body = client.get("/v2/n-stroke/benchmark").json()
        assert body["faster"] in ("sync", "async_fluid")

    def test_verdict_fields_present(self, client: TestClient) -> None:
        """Benchmark response should also include verdicts for both strokes."""
        body = client.get("/v2/n-stroke/benchmark").json()
        assert "sync_verdict" in body
        assert "async_verdict" in body
        assert body["sync_verdict"] in ("pass", "warn", "fail")
        assert body["async_verdict"] in ("pass", "warn", "fail")
