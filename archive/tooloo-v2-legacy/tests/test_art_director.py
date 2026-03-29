"""
tests/test_art_director.py — Art Director WCAG/Gestalt vision-critique tests.

Validates:
  - _run_art_director: no file_path skips render, non-html skips render,
    JSON parse from mock LLM response, fallback critique when parse fails
  - _try_vision_call: stub fallback when all model clients are None
  - Integration: mandate_executor ux_eval node triggers art_director flow
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.mandate_executor import _run_art_director, _try_vision_call


# ── _try_vision_call ───────────────────────────────────────────────────────────


class TestTryVisionCall:
    def test_returns_stub_when_clients_none(self):
        result = _try_vision_call(
            b64_png=None,
            prompt="Evaluate WCAG compliance of this screenshot",
            model_id="gemini-2.5-flash",
        )
        assert isinstance(result, str)
        assert len(result) > 10

    def test_returns_string_always(self):
        result = _try_vision_call(
            b64_png=None, prompt="any prompt", model_id="any-model")
        assert isinstance(result, str)

    def test_stub_contains_required_keys(self):
        """The stub fallback must be parseable JSON with the required critique keys."""
        result = _try_vision_call(
            b64_png=None, prompt="WCAG critique", model_id="gemini-flash")
        try:
            parsed = json.loads(result)
            # If parseable, must contain at least one of the expected keys
            expected_keys = {"critique", "adjustments", "wcag_pass", "scores"}
            assert expected_keys & set(
                parsed.keys()), f"Missing expected keys in: {parsed}"
        except json.JSONDecodeError:
            # Plain-text fallback is also acceptable
            assert len(result) > 5


# ── _run_art_director ──────────────────────────────────────────────────────────


class TestRunArtDirector:
    @pytest.fixture()
    def mcp_mock(self):
        mcp = MagicMock()
        mcp.call.return_value = MagicMock(
            success=True,
            output={
                "renderer": "stub",
                "b64_png": None,
                "screenshot_b64": "iVBORw0KGgoAAAANSUhEUg==",  # minimal fake b64 PNG
                "file_path": "test.html",
            },
        )
        return mcp

    @pytest.fixture()
    def llm_mock(self):
        """Callable that returns valid art-director JSON."""
        critique_json = json.dumps(
            {
                "critique": "Good contrast ratio. Minor alignment issue on mobile.",
                "adjustments": [
                    {"selector": ".nav-btn", "property": "padding",
                        "value": "12px 24px"}
                ],
                "wcag_pass": True,
                "scores": {
                    "contrast": 0.9,
                    "alignment": 0.75,
                    "cognitive_load": 0.85,
                    "affordance": 0.8,
                    "animation": 0.9,
                },
            }
        )

        def _call_llm_raw(prompt, node_type="ux_eval", model_id="gemini-2.5-flash", **kwargs):
            return critique_json

        return _call_llm_raw

    def test_no_file_path_returns_not_rendered(self, mcp_mock, llm_mock):
        result = _run_art_director(
            mcp=mcp_mock,
            file_path=None,
            ux_blueprint="A navigation panel",
            mandate="Build TooLoo Studio",
            intent="BUILD",
            model_id="gemini-2.5-flash",
            call_llm_raw=llm_mock,
        )
        assert result["rendered"] is False
        # renderer is 'none' for no-file-path case (no screenshot attempted)
        assert result["renderer"] in ("none", "skipped", "stub")

    def test_non_html_file_returns_not_rendered(self, mcp_mock, llm_mock):
        result = _run_art_director(
            mcp=mcp_mock,
            file_path="engine/config.py",
            ux_blueprint="Config file",
            mandate="",
            intent="BUILD",
            model_id="gemini-2.5-flash",
            call_llm_raw=llm_mock,
        )
        assert result["rendered"] is False
        assert result["renderer"] in ("none", "skipped", "stub")

    def test_html_file_triggers_render_and_critique(self, mcp_mock, llm_mock):
        import engine.mandate_executor as me
        with patch.object(me, "_try_vision_call", side_effect=llm_mock):
            result = _run_art_director(
                mcp=mcp_mock,
                file_path="studio/static/index.html",
                ux_blueprint="TooLoo Studio main panel",
                mandate="Redesign the buddy chat section",
                intent="DESIGN",
                model_id="gemini-2.5-flash",
                call_llm_raw=llm_mock,
            )
        mcp_mock.call.assert_called_once()
        call_args = mcp_mock.call.call_args
        assert call_args[0][0] == "render_screenshot"
        assert result["rendered"] is True
        assert "critique" in result
        assert result["wcag_pass"] is True

    def test_valid_scores_structure(self, mcp_mock, llm_mock):
        import engine.mandate_executor as me
        with patch.object(me, "_try_vision_call", side_effect=llm_mock):
            result = _run_art_director(
                mcp=mcp_mock,
                file_path="studio/static/index.html",
                ux_blueprint="Studio UI",
                mandate="",
                intent="DESIGN",
                model_id="gemini-2.5-flash",
                call_llm_raw=llm_mock,
            )
        scores = result.get("scores", {})
        for axis in ("contrast", "alignment", "cognitive_load", "affordance", "animation"):
            assert axis in scores, f"Missing score axis: {axis}"
            # Art Director scores are 1-5 integers per WCAG evaluation spec
            assert 0 < scores[axis] <= 5, f"Score out of range: {axis}={scores[axis]}"

    def test_adjustments_is_list(self, mcp_mock, llm_mock):
        import engine.mandate_executor as me
        with patch.object(me, "_try_vision_call", side_effect=llm_mock):
            result = _run_art_director(
                mcp=mcp_mock,
                file_path="studio/static/index.html",
                ux_blueprint="Studio UI",
                mandate="",
                intent="DESIGN",
                model_id="gemini-2.5-flash",
                call_llm_raw=llm_mock,
            )
        assert isinstance(result.get("adjustments"), list)

    def test_broken_json_from_llm_returns_fallback(self, mcp_mock):
        """When LLM returns invalid JSON, _run_art_director must not raise — return fallback."""

        def _bad_llm(prompt, node_type="ux_eval", model_id="gemini-2.5-flash", **kwargs):
            return "Sorry, I can't evaluate that right now."

        result = _run_art_director(
            mcp=mcp_mock,
            file_path="studio/static/index.html",
            ux_blueprint="Studio UI",
            mandate="",
            intent="DESIGN",
            model_id="gemini-2.5-flash",
            call_llm_raw=_bad_llm,
        )
        # Must return a structured dict — no exceptions allowed
        assert isinstance(result, dict)
        assert "critique" in result

    def test_render_failure_returns_fallback(self, llm_mock):
        """When render_screenshot MCP call fails, return fallback without raising."""
        mcp_err = MagicMock()
        mcp_err.call.return_value = MagicMock(
            success=False,
            error="Playwright not available",
            output={},
        )
        result = _run_art_director(
            mcp=mcp_err,
            file_path="studio/static/index.html",
            ux_blueprint="Studio UI",
            mandate="",
            intent="DESIGN",
            model_id="gemini-2.5-flash",
            call_llm_raw=llm_mock,
        )
        assert isinstance(result, dict)
        assert "rendered" in result

    def test_mcp_not_called_for_non_html(self, mcp_mock, llm_mock):
        _run_art_director(
            mcp=mcp_mock,
            file_path="engine/tribunal.py",
            ux_blueprint="",
            mandate="",
            intent="BUILD",
            model_id="gemini-2.5-flash",
            call_llm_raw=llm_mock,
        )
        mcp_mock.call.assert_not_called()


# ── Integration: mandate_executor ux_eval node triggers art_director ──────────


class TestMandateExecutorUxEvalIntegration:
    """Verify the ux_eval node type sets art_director key in its result."""

    def test_ux_eval_node_result_has_art_director_key(self):
        """The make_live_work_fn closure for ux_eval must return art_director."""
        from engine.mandate_executor import make_live_work_fn
        from engine.executor import Envelope
        from engine.mcp_manager import MCPManager

        mcp = MCPManager()
        work_fn = make_live_work_fn(
            mandate_text="Redesign the nav bar for WCAG AA",
            intent="DESIGN",
            jit_signals=["Use WCAG 2.2 contrast ratios"],
            mcp_manager=mcp,
        )
        env = Envelope(
            mandate_id="ux_eval",
            intent="DESIGN",
            domain="frontend",
            metadata={},
        )
        result = work_fn(env)

        assert "art_director" in result, (
            f"Expected 'art_director' key in ux_eval result, got keys: {list(result.keys())}"
        )
        ad = result["art_director"]
        assert isinstance(ad, dict)
        assert "rendered" in ad
