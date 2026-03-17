"""
tests/conftest.py — Shared pytest configuration and fixtures.

Offline-by-default policy
──────────────────────────
All tests run offline (no Gemini, no GitHub) unless the environment variable
TOOLOO_LIVE_TESTS=1 is explicitly set.  This keeps `pytest tests/` fast (< 3 s)
and deterministic regardless of API key availability.

  Offline (default):  pytest tests/
  Live integration:   TOOLOO_LIVE_TESTS=1 pytest tests/

The fixture patches `_gemini_client` to None in both engine modules so the
keyword-fallback and structured-catalogue paths are exercised instead of
making real LLM network calls.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest


_LIVE = os.getenv("TOOLOO_LIVE_TESTS", "").lower() in ("1", "true", "yes")


@pytest.fixture(autouse=True, scope="session")
def offline_gemini():
    """Patch Gemini clients to None for the entire test session unless TOOLOO_LIVE_TESTS=1."""
    if _LIVE:
        yield  # do nothing — use real clients
        return

    with (
        patch("engine.conversation._gemini_client", None),
        patch("engine.jit_booster._gemini_client", None),
    ):
        yield
