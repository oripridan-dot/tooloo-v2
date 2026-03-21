"""
tests/test_speculative_healing.py — Speculative Healing & Differential Micro-Mitosis tests.

Validates:
  - patch_apply MCP tool: exact match, fuzzy match, path traversal guard
  - render_screenshot MCP tool: HTML file, non-HTML rejection, stub fallback
  - SpeculativeHealingEngine: ghost branch spawning, wait_for_first_success logic,
    deterministic fallback when model unavailable
  - RefinementSupervisor: unchanged sequential path still works
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from engine.mcp_manager import MCPManager, _tool_patch_apply, _tool_render_screenshot
from engine.refinement_supervisor import (
    NODE_FAIL_THRESHOLD,
    N_SPECULATIVE_BRANCHES,
    SPECULATIVE_GHOST_TIMEOUT,
    RefinementSupervisor,
    SpeculativeHealingEngine,
    SpeculativeHealingResult,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace_html(tmp_path, monkeypatch):
    """Create a minimal HTML file inside the workspace root and monkeypatch WORKSPACE_ROOT."""
    import engine.mcp_manager as mcp_mod

    monkeypatch.setattr(mcp_mod, "_WORKSPACE_ROOT", tmp_path)
    html_file = tmp_path / "test_ui.html"
    html_file.write_text(
        "<!DOCTYPE html><html><body><h1>Hello TooLoo</h1></body></html>",
        encoding="utf-8",
    )
    return html_file, tmp_path


@pytest.fixture()
def workspace_py(tmp_path, monkeypatch):
    """Create a minimal Python file inside the workspace root."""
    import engine.mcp_manager as mcp_mod

    monkeypatch.setattr(mcp_mod, "_WORKSPACE_ROOT", tmp_path)
    py_file = tmp_path / "broken.py"
    py_file.write_text(
        "def compute(result):\n    for k, v in result.items():\n        print(k, v)\n",
        encoding="utf-8",
    )
    return py_file, tmp_path


# ── patch_apply tests ──────────────────────────────────────────────────────────


class TestPatchApply:
    def test_exact_match(self, workspace_py):
        py_file, tmp_path = workspace_py
        result = _tool_patch_apply(
            file_path="broken.py",
            search_block="    for k, v in result.items():\n        print(k, v)",
            replace_block="    for k, v in (result or {}).items():\n        print(k, v)",
        )
        assert result["patched"] is True
        assert result["delta_lines"] == 0
        content = py_file.read_text()
        assert "(result or {})" in content

    def test_fuzzy_match(self, workspace_py):
        py_file, tmp_path = workspace_py
        # Slightly misaligned whitespace in search block — fuzzy should handle it
        result = _tool_patch_apply(
            file_path="broken.py",
            search_block="for k, v in result.items():\n print(k, v)",
            replace_block="for k, v in (result or {}).items():\n    print(k, v)",
            fuzzy=True,
        )
        assert result["patched"] is True

    def test_search_block_not_found_raises(self, workspace_py):
        _, tmp_path = workspace_py
        with pytest.raises(ValueError, match="not found verbatim"):
            _tool_patch_apply(
                file_path="broken.py",
                search_block="THIS_DOESNT_EXIST_IN_FILE",
                replace_block="anything",
            )

    def test_path_traversal_rejected(self, workspace_py):
        _, tmp_path = workspace_py
        with pytest.raises(ValueError, match="Path traversal"):
            _tool_patch_apply(
                file_path="../etc/passwd",
                search_block="root",
                replace_block="nobody",
            )

    def test_mcp_manager_patch_apply(self, workspace_py):
        """Test through MCPManager.call() dispatch."""
        py_file, tmp_path = workspace_py
        mcp = MCPManager()
        result = mcp.call(
            "patch_apply",
            file_path="broken.py",
            search_block="    for k, v in result.items():",
            replace_block="    for k, v in (result or {}).items():",
        )
        assert result.success is True
        assert result.output["patched"] is True

    def test_patch_apply_in_manifest(self):
        mcp = MCPManager()
        uris = [t.uri for t in mcp.manifest()]
        assert "mcp://tooloo/patch_apply" in uris

    def test_lines_delta_on_expansion(self, workspace_py):
        py_file, tmp_path = workspace_py
        result = _tool_patch_apply(
            file_path="broken.py",
            search_block="def compute(result):",
            replace_block="def compute(result: dict) -> None:\n    # HEALED: added type annotation",
        )
        assert result["delta_lines"] == 1


# ── render_screenshot tests ────────────────────────────────────────────────────


class TestRenderScreenshot:
    def test_non_html_rejected(self, workspace_py):
        _, tmp_path = workspace_py
        with pytest.raises(ValueError, match=r"only supports \.html"):
            _tool_render_screenshot(file_path="broken.py")

    def test_missing_file_raises(self, workspace_html):
        html_file, tmp_path = workspace_html
        with pytest.raises(FileNotFoundError):
            _tool_render_screenshot(file_path="nonexistent.html")

    def test_playwright_stub_fallback(self, workspace_html):
        """When playwright is not installed, the tool returns a structured stub."""
        html_file, tmp_path = workspace_html
        result = _tool_render_screenshot(file_path="test_ui.html")
        # Either succeeds with Playwright or returns a stub — never raises
        assert isinstance(result, dict)
        assert "renderer" in result
        assert result["renderer"] in ("playwright", "stub", "error")
        assert "file_path" in result

    def test_render_screenshot_in_manifest(self):
        mcp = MCPManager()
        uris = [t.uri for t in mcp.manifest()]
        assert "mcp://tooloo/render_screenshot" in uris

    def test_path_traversal_rejected(self, workspace_html):
        _, tmp_path = workspace_html
        with pytest.raises(ValueError, match="Path traversal"):
            _tool_render_screenshot(file_path="../etc/evil.html")

    def test_mcp_manager_render_screenshot_stub(self, workspace_html):
        html_file, tmp_path = workspace_html
        mcp = MCPManager()
        result = mcp.call("render_screenshot", file_path="test_ui.html")
        assert result.success is True
        assert result.output["renderer"] in ("playwright", "stub", "error")


# ── SpeculativeHealingEngine tests ─────────────────────────────────────────────


class TestSpeculativeHealingEngine:
    def test_constants_sane(self):
        assert N_SPECULATIVE_BRANCHES >= 2
        assert SPECULATIVE_GHOST_TIMEOUT > 0

    def test_result_dataclass_serialises(self):
        r = SpeculativeHealingResult(
            healing_id="spec-abc",
            node_id="validate",
            winner_ghost_id="spec-abc-g1",
            winning_patch={"file_path": "x.py",
                           "search_block": "a", "replace_block": "b"},
            ghosts_spawned=3,
            ghosts_succeeded=1,
            latency_ms=123.4,
            verdict="won",
        )
        d = r.to_dict()
        assert d["verdict"] == "won"
        assert d["winner_ghost_id"] == "spec-abc-g1"
        assert isinstance(d["latency_ms"], float)

    @pytest.mark.asyncio
    async def test_speculate_all_failed_no_model(self):
        """Without a model garden, ghosts fall back to MCP read_error hints."""
        mcp = MCPManager()
        engine = SpeculativeHealingEngine(mcp=mcp)
        result = await engine.speculate(
            node_id="implement",
            error_text="AttributeError: 'NoneType' object has no attribute 'items'",
            file_path="engine/config.py",
            broken_snippet="for k, v in result.items():",
            intent="BUILD",
            mandate_text="Build a DSP buffer manager",
            n_branches=2,
            timeout=5.0,
        )
        assert isinstance(result, SpeculativeHealingResult)
        assert result.ghosts_spawned == 2
        assert result.verdict in ("won", "all_failed")
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_speculate_returns_before_timeout(self):
        """Ensure speculate completes well within the timeout."""
        import time

        mcp = MCPManager()
        engine = SpeculativeHealingEngine(mcp=mcp)
        t0 = time.monotonic()
        result = await engine.speculate(
            node_id="validate",
            error_text="ZeroDivisionError: division by zero",
            file_path="engine/n_stroke.py",
            broken_snippet="rate = total / count",
            intent="DEBUG",
            mandate_text="Fix division error in N-Stroke",
            n_branches=2,
            timeout=10.0,
        )
        elapsed = time.monotonic() - t0
        assert elapsed < 12.0, f"Speculate took too long: {elapsed:.1f}s"
        assert result.healing_id.startswith("spec-")

    def test_ghost_branch_specs_built_correctly(self):
        """Verify the strategy strings and tier assignments are correct."""
        from engine.refinement_supervisor import SpeculativeHealingEngine

        mcp = MCPManager()
        engine = SpeculativeHealingEngine(mcp=mcp)
        specs = [
            engine._STRATEGIES[i]
            for i in range(min(N_SPECULATIVE_BRANCHES, len(engine._STRATEGIES)))
        ]
        tiers = [s[1] for s in specs]
        # All ghost branches must route to Tier 0 or 1 — never Tier 2+
        assert all(
            t <= 1 for t in tiers), f"Ghost tiers contain heavy models: {tiers}"


# ── RefinementSupervisor sequential path (regression) ─────────────────────────


class TestRefinementSupervisorRegression:
    def test_heal_returns_report(self):
        sup = RefinementSupervisor()
        mcp = MCPManager()

        class _FakeBooster:
            def fetch_for_node(self, *a, **kw):
                from engine.jit_booster import JITBoostResult
                return JITBoostResult(
                    boosted_confidence=0.9,
                    signals=["Use Python 3.12 sub-interpreters for parallelism"],
                    source="catalogue",
                    boost_delta=0.05,
                )

        report = sup.heal(
            failed_node_ids=["test-node-1"],
            stroke=4,
            intent="BUILD",
            mcp=mcp,
            booster=_FakeBooster(),
            mandate_text="Build a zero-latency DSP buffer",
            last_error_map={
                "test-node-1": "AttributeError: 'NoneType' has no attr 'start'"},
        )
        assert report.verdict in ("healed", "partial", "unable")
        assert report.stroke == 4
        assert "test-node-1" in report.nodes_analyzed
        assert len(report.prescriptions) == 1

    def test_node_fail_threshold_constant(self):
        # Production default is 3; dev mode previously raised this to 6.
        assert NODE_FAIL_THRESHOLD == 3

    def test_heal_builds_work_fn(self):
        from engine.executor import Envelope

        sup = RefinementSupervisor()
        mcp = MCPManager()

        class _FakeBooster:
            def fetch_for_node(self, *a, **kw):
                from engine.jit_booster import JITBoostResult
                return JITBoostResult(
                    boosted_confidence=0.88, signals=[], source="catalogue", boost_delta=0.0
                )

        report = sup.heal(
            failed_node_ids=["implement"],
            stroke=7,
            intent="DEBUG",
            mcp=mcp,
            booster=_FakeBooster(),
            mandate_text="Fix the import error",
        )
        if report.healed_work_fn:
            env = Envelope(
                mandate_id="implement",
                intent="DEBUG",
                domain="backend",
                metadata={"stroke": 7, "model": "gemini-2.5-flash"},
            )
            result = report.healed_work_fn(env)
            assert result["status"] == "healed_execution"
            assert result["healing_applied"] is True
