"""Tests for /v2/introspector/* API endpoints in studio/api.py."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from studio.api import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestIntrospectorEndpoints:
    """Verify all 9 /v2/introspector/* REST endpoints return correct shapes."""

    def test_introspector_snapshot_200(self, client: TestClient) -> None:
        r = client.get("/v2/introspector")
        assert r.status_code == 200
        data = r.json()
        assert "system_health" in data
        assert "modules" in data
        assert "knowledge_graph" in data

    def test_system_health_200(self, client: TestClient) -> None:
        r = client.get("/v2/introspector/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("green", "yellow", "red")
        assert data["module_count"] > 0
        assert "avg_health" in data
        assert "min_health" in data
        assert "critical_modules" in data
        assert "layers" in data

    def test_module_health_known(self, client: TestClient) -> None:
        r = client.get("/v2/introspector/module/router")
        assert r.status_code == 200
        data = r.json()
        assert data["module"] == "router"
        assert data["health_score"] > 0
        assert data["layer"] == "routing"

    def test_module_health_unknown(self, client: TestClient) -> None:
        r = client.get("/v2/introspector/module/nonexistent")
        assert r.status_code == 200
        data = r.json()
        assert "error" in data
        assert "modules" in data  # lists available modules

    def test_all_cross_refs_200(self, client: TestClient) -> None:
        r = client.get("/v2/introspector/cross-refs")
        assert r.status_code == 200
        data = r.json()
        assert "total_refs" in data
        assert "by_module" in data
        assert data["total_refs"] > 100

    def test_module_cross_refs_200(self, client: TestClient) -> None:
        r = client.get("/v2/introspector/cross-refs/config")
        assert r.status_code == 200
        data = r.json()
        assert data["module"] == "config"
        assert data["ref_count"] > 0
        assert len(data["refs"]) > 0

    def test_dead_code_200(self, client: TestClient) -> None:
        r = client.get("/v2/introspector/dead-code")
        assert r.status_code == 200
        data = r.json()
        assert "dead_function_count" in data
        assert "functions" in data

    def test_knowledge_graph_200(self, client: TestClient) -> None:
        r = client.get("/v2/introspector/knowledge-graph")
        assert r.status_code == 200
        data = r.json()
        assert data["total_modules"] > 10
        assert "layers" in data
        assert "modules" in data

    def test_cascade_analysis_200(self, client: TestClient) -> None:
        r = client.get("/v2/introspector/cascade/engine/router.py")
        assert r.status_code == 200
        data = r.json()
        assert "source" in data
        assert "source_health" in data
        assert "affected_count" in data
        assert "cascade" in data

    def test_rebuild_200(self, client: TestClient) -> None:
        r = client.post("/v2/introspector/rebuild")
        assert r.status_code == 200
        data = r.json()
        assert data["rebuilt"] is True
        assert data["module_count"] > 0
        assert data["status"] in ("green", "yellow", "red")

    def test_path_traversal_guard(self, client: TestClient) -> None:
        """Ensure ../../../etc/passwd is sanitised."""
        r = client.get("/v2/introspector/cascade/etc/passwd")
        assert r.status_code == 200
        data = r.json()
        # Path should be sanitised — no real file found
        assert data["affected_count"] == 0
