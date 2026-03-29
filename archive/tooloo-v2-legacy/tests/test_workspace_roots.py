"""
tests/test_workspace_roots.py — Tests for multi-root workspace support.

Covers:
  - engine/config.get_workspace_roots() default (repo root only)
  - engine/config.get_workspace_roots() with WORKSPACE_ROOTS env override
  - GET /v2/workspace/roots API endpoint
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from engine.config import get_workspace_roots, _REPO_ROOT
from studio.api import app

client = TestClient(app)


# ── config helper tests ───────────────────────────────────────────────────────

def test_get_workspace_roots_default():
    """Default roots returns a list of one: the repository root."""
    roots = get_workspace_roots()
    assert isinstance(roots, list)
    assert len(roots) >= 1
    assert all(isinstance(r, Path) for r in roots)
    # The first root should be the repo root
    assert roots[0] == _REPO_ROOT.resolve()


def test_get_workspace_roots_from_env(monkeypatch, tmp_path):
    """WORKSPACE_ROOTS env var is honoured when set to colon-separated paths."""
    root_a = tmp_path / "root_a"
    root_b = tmp_path / "root_b"
    root_a.mkdir()
    root_b.mkdir()

    monkeypatch.setenv("WORKSPACE_ROOTS", f"{root_a}:{root_b}")

    # Import the function fresh so it reads the monkeypatched env
    import importlib
    import engine.config as cfg_module
    importlib.reload(cfg_module)
    roots = cfg_module.get_workspace_roots()

    assert len(roots) == 2
    assert roots[0] == root_a.resolve()
    assert roots[1] == root_b.resolve()

    # Restore module to avoid polluting other tests
    importlib.reload(cfg_module)


def test_get_workspace_roots_skips_empty_segments(monkeypatch):
    """Empty segments in WORKSPACE_ROOTS are ignored."""
    monkeypatch.setenv("WORKSPACE_ROOTS", f"{_REPO_ROOT}::")

    import importlib
    import engine.config as cfg_module
    importlib.reload(cfg_module)
    roots = cfg_module.get_workspace_roots()

    assert all(r != Path("") for r in roots)
    importlib.reload(cfg_module)


# ── API endpoint tests ────────────────────────────────────────────────────────

def test_workspace_roots_endpoint_returns_200():
    """GET /v2/workspace/roots returns HTTP 200."""
    resp = client.get("/v2/workspace/roots")
    assert resp.status_code == 200


def test_workspace_roots_endpoint_schema():
    """GET /v2/workspace/roots returns expected JSON schema."""
    resp = client.get("/v2/workspace/roots")
    data = resp.json()
    assert "roots" in data
    assert "count" in data
    assert isinstance(data["roots"], list)
    assert isinstance(data["count"], int)
    assert data["count"] == len(data["roots"])


def test_workspace_roots_endpoint_contains_repo_root():
    """GET /v2/workspace/roots includes the repository root path."""
    resp = client.get("/v2/workspace/roots")
    roots = resp.json()["roots"]
    assert any(str(_REPO_ROOT) in r for r in roots)
