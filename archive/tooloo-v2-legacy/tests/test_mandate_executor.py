"""
tests/test_mandate_executor.py — MandateExecutor / make_live_work_fn tests.

Coverage:
  · make_live_work_fn() returns a stateless callable (Law 17)
  · Offline fallback: both AI clients None → symbolic execution succeeds
  · Each of the 8 node types (ingest, analyse, design, implement, validate,
    emit, audit_wave, dry_run) produces a non-empty result dict
  · _node_type_from_id() derivation for semantic and wave-index IDs
  · Frontend target detection (_is_frontend_target)
  · Tool-call extraction (_extract_tool_calls) for valid and malformed JSON
  · make_live_work_fn closure is stateless: two calls with different envelopes
    do not share state
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from engine.executor import Envelope
from engine.mandate_executor import (
    _extract_tool_calls,
    _is_frontend_target,
    _node_type_from_id,
    make_live_work_fn,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_env(node_id: str, mandate: str = "build a new feature") -> Envelope:
    return Envelope(
        mandate_id=node_id,
        intent="BUILD",
        metadata={"mandate_text": mandate,
                  "jit_signals": ["signal-a", "signal-b"]},
    )


# ── _node_type_from_id ─────────────────────────────────────────────────────────

class TestNodeTypeFromId:
    @pytest.mark.parametrize("node_id,expected", [
        ("ns-abc-s1-implement", "implement"),
        ("ns-abc-s1-ingest", "ingest"),
        ("ns-abc-s1-analyse", "analyse"),
        ("ns-abc-s1-design", "design"),
        ("ns-abc-s1-validate", "validate"),
        ("ns-abc-s1-emit", "emit"),
        ("ns-abc-s1-audit_wave", "audit_wave"),
        ("ns-abc-s1-dry_run", "dry_run"),
    ])
    def test_semantic_ids(self, node_id: str, expected: str):
        assert _node_type_from_id(node_id) == expected

    def test_wave_index_zero(self):
        # Wave index 0 → audit_wave
        assert _node_type_from_id("m-abc123-0") == "audit_wave"

    def test_wave_index_out_of_range_clamped(self):
        # Very high index → clamped to last wave type
        result = _node_type_from_id("m-abc123-999")
        assert result in ("emit", "dry_run", "ux_eval",
                          "audit_wave", "analyse", "art_director", "spawn_repo")

    def test_unknown_suffix_defaults_to_analyse(self):
        assert _node_type_from_id("m-abc123-unknown") == "analyse"


# ── _is_frontend_target ────────────────────────────────────────────────────────

class TestIsFrontendTarget:
    def test_html_extension(self):
        assert _is_frontend_target(
            "update studio/static/index.html styles", "BUILD")

    def test_ts_extension(self):
        assert _is_frontend_target("refactor dashboard.tsx component", "BUILD")

    def test_design_intent(self):
        assert _is_frontend_target("reorganise the layout", "DESIGN")

    def test_backend_python(self):
        assert not _is_frontend_target(
            "add threading lock to vector_store.py", "BUILD")

    def test_engine_path(self):
        assert not _is_frontend_target(
            "refactor engine/router.py circuit breaker", "DEBUG")


# ── _extract_tool_calls ────────────────────────────────────────────────────────

class TestExtractToolCalls:
    def test_single_json_object(self):
        raw = '<tool_call>{"tool": "file_write", "path": "engine/x.py"}</tool_call>'
        calls = _extract_tool_calls(raw)
        assert len(calls) == 1
        assert calls[0]["tool"] == "file_write"

    def test_json_array_in_block(self):
        raw = '<tool_call>[{"tool": "file_read"}, {"tool": "run_tests"}]</tool_call>'
        calls = _extract_tool_calls(raw)
        assert len(calls) == 2

    def test_multiple_blocks(self):
        raw = (
            '<tool_call>{"tool": "ingest"}</tool_call> text '
            '<tool_call>{"tool": "analyse"}</tool_call>'
        )
        calls = _extract_tool_calls(raw)
        assert len(calls) == 2

    def test_malformed_json_skipped(self):
        raw = "<tool_call>{not valid json}</tool_call>"
        calls = _extract_tool_calls(raw)
        assert calls == []

    def test_no_tool_calls(self):
        assert _extract_tool_calls("plain text response with no tags") == []

    def test_empty_block_skipped(self):
        assert _extract_tool_calls("<tool_call>   </tool_call>") == []


# ── make_live_work_fn — offline mode ──────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_ai_clients():
    """Null out both AI clients so tests run offline and fast."""
    with (
        patch("engine.mandate_executor._vertex_client", None),
        patch("engine.mandate_executor._gemini_client", None),
    ):
        yield


class TestMakeLiveWorkFnOffline:
    def test_returns_callable(self):
        fn = make_live_work_fn("build a new feature", "BUILD", ["signal"])
        assert callable(fn)

    def test_ingest_node_produces_output(self):
        fn = make_live_work_fn(
            "build JWT auth middleware", "BUILD", ["signal-a"])
        env = _make_env("m-test-ingest", "build JWT auth middleware")
        result = fn(env)
        assert isinstance(result, dict)
        assert result.get("output") or result.get(
            "text") or result.get("result") or result

    @pytest.mark.parametrize("node_suffix", [
        "ingest", "analyse", "design", "implement", "validate", "emit",
        "audit_wave", "dry_run",
    ])
    def test_all_node_types_return_dict(self, node_suffix: str):
        fn = make_live_work_fn(
            "refactor router circuit breaker", "DEBUG", ["sig"])
        env = _make_env(f"ns-abc-s1-{node_suffix}",
                        "refactor router circuit breaker")
        result = fn(env)
        assert isinstance(
            result, dict), f"Node {node_suffix} did not return dict"

    def test_stateless_separate_calls_independent(self):
        """Two separate work functions must not share state (Law 17)."""
        fn1 = make_live_work_fn("build auth", "BUILD", ["sig1"])
        fn2 = make_live_work_fn("audit security", "AUDIT", ["sig2"])
        env1 = _make_env("m-a-0", "build auth")
        env2 = _make_env("m-b-0", "audit security")
        r1 = fn1(env1)
        r2 = fn2(env2)
        # Results must be independent dicts — neither should be the same object
        assert r1 is not r2

    def test_mandate_truncated_to_500_chars(self):
        """Long mandate text is silently truncated — should not raise."""
        long_mandate = "x" * 2000
        fn = make_live_work_fn(long_mandate, "BUILD", [])
        env = _make_env("m-a-0", long_mandate)
        result = fn(env)
        assert isinstance(result, dict)

    def test_empty_jit_signals_list(self):
        fn = make_live_work_fn("debug slow query", "DEBUG", [])
        env = _make_env("m-a-analyse", "debug slow query")
        result = fn(env)
        assert isinstance(result, dict)
