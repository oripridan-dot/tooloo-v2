"""
tests/conftest.py — Shared pytest configuration and fixtures.

Offline-by-default policy
──────────────────────────
All tests run offline (no Vertex AI, no Gemini, no GitHub) unless the
environment variable TOOLOO_LIVE_TESTS=1 is explicitly set.  This keeps
`pytest tests/` fast (< 3 s) and deterministic regardless of credential
availability.

  Offline (default):  pytest tests/
  Live integration:   TOOLOO_LIVE_TESTS=1 pytest tests/

The fixture nulls out both the Vertex AI model class and the legacy Gemini
direct client in both engine modules so the keyword-fallback and structured-
catalogue paths are exercised instead of making real LLM network calls.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest


_LIVE = os.getenv("TOOLOO_LIVE_TESTS", "").lower() in ("1", "true", "yes")


@pytest.fixture(autouse=True, scope="session")
def offline_vertex():
    """
    Disable all LLM clients for the entire test session unless TOOLOO_LIVE_TESTS=1.

    Patches:
      * engine.conversation._vertex_client    → None  (disables Vertex AI path)
      * engine.jit_booster._vertex_client     → None  (disables Vertex AI path)
      * engine.conversation._gemini_client    → None  (disables legacy Gemini path)
      * engine.jit_booster._gemini_client     → None  (disables legacy Gemini path)

    Both paths being None exercises the keyword-fallback and structured-
    catalogue paths that are designed for exactly this scenario.
    """
    if _LIVE:
        yield  # do nothing — use real clients
        return

    with (
        patch("engine.conversation._vertex_client", None),
        patch("engine.jit_booster._vertex_client", None),
        patch("engine.conversation._gemini_client", None),
        patch("engine.jit_booster._gemini_client", None),
        patch("engine.engram_visual._gemini_client", None),
        patch("engine.self_improvement._vertex_client", None),
        patch("engine.self_improvement._gemini_client", None),
        # ModelGarden — disable both providers so all LLM calls fall through
        # to the structured catalogue (keyword-fallback path).
        patch("engine.model_garden._google_client", None),
        patch("engine.model_garden._gemini_api_client", None),
        patch("engine.model_garden._openai_client", None),
        patch("engine.model_garden._anthropic_client", None),
        patch("engine.model_garden._anthropic_available", False),
        patch("engine.sota_ingestion._vertex_client", None),
        patch("engine.sota_ingestion._gemini_client", None),
    ):
        yield


# Python 3.12 changed asyncio.get_event_loop() to raise RuntimeError when
# there is no current event loop (instead of creating one).  Tests that use
# asyncio.run() clear the current event loop afterwards, which breaks tests
# that rely on asyncio.get_event_loop().run_until_complete().
# This autouse fixture ensures there is always a fresh event loop set.
@pytest.fixture(autouse=True)
def _ensure_event_loop():
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    yield
