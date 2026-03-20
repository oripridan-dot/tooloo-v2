"""tests/test_jit_designer.py — Unit tests for JITDesigner and analyze_partial_prompt."""
from __future__ import annotations

import pytest
from engine.jit_designer import (
    JITDesigner,
    DesignDirective,
    ThoughtCard,
    analyze_partial_prompt,
    _extract_emphasis_words,
    _confidence_tier,
)


# ── _confidence_tier ─────────────────────────────────────────────────────────

class TestConfidenceTier:
    def test_high(self):
        assert _confidence_tier(0.95) == "high"
        assert _confidence_tier(0.85) == "high"

    def test_medium(self):
        assert _confidence_tier(0.80) == "medium"
        assert _confidence_tier(0.55) == "medium"

    def test_low(self):
        assert _confidence_tier(0.54) == "low"
        assert _confidence_tier(0.0) == "low"


# ── _extract_emphasis_words ───────────────────────────────────────────────────

class TestExtractEmphasisWords:
    def test_skips_stop_words(self):
        words = _extract_emphasis_words("the and is of to with")
        assert words == []

    def test_extracts_significant_tokens(self):
        words = _extract_emphasis_words(
            "authentication module security token validation")
        assert "authentication" in words
        assert "security" in words

    def test_max_words_limit(self):
        text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
        assert len(_extract_emphasis_words(text, max_words=4)) <= 4

    def test_deduplicates_across_case(self):
        words = _extract_emphasis_words("Token token TOKEN")
        assert len(words) == 1

    def test_skips_short_tokens(self):
        # min length in regex is 3 chars
        words = _extract_emphasis_words("ab cd ef three four five")
        for w in words:
            assert len(w) >= 3


# ── ThoughtCard ───────────────────────────────────────────────────────────────

class TestThoughtCard:
    def test_to_dict_keys(self):
        card = ThoughtCard(phase="route", icon="✦",
                           title="Intent", detail="Classified", status="done")
        d = card.to_dict()
        assert set(d.keys()) == {"phase", "icon", "title", "detail", "status"}

    def test_to_dict_values(self):
        card = ThoughtCard(phase="jit", icon="⚡", title="SOTA",
                           detail="loaded", status="active")
        d = card.to_dict()
        assert d["phase"] == "jit"
        assert d["status"] == "active"


# ── DesignDirective ───────────────────────────────────────────────────────────

class TestDesignDirective:
    def test_to_dict_includes_all_fields(self):
        dd = DesignDirective(
            component_type="prose",
            palette_key="system_blue",
            animation_style="fade_up",
            layout_hint="single_column",
            emphasis_words=["security"],
            confidence_visual="high",
            thought_cards=[ThoughtCard("route", "✦", "T", "d")],
            hig_rule_applied="HIG:spatial_clarity",
        )
        d = dd.to_dict()
        assert d["component_type"] == "prose"
        assert d["confidence_visual"] == "high"
        assert isinstance(d["thought_cards"], list)
        assert len(d["thought_cards"]) == 1
        assert d["emphasis_words"] == ["security"]


# ── JITDesigner.evaluate ─────────────────────────────────────────────────────

class TestJITDesigner:
    @pytest.fixture(scope="class")
    def designer(self):
        return JITDesigner()

    def test_returns_design_directive(self, designer):
        result = designer.evaluate(
            intent="EXPLAIN",
            emotional_state="neutral",
            confidence=0.90,
            response_text="Here is how authentication works in OAuth2.",
        )
        assert isinstance(result, DesignDirective)

    def test_build_intent_gets_storybook_component(self, designer):
        result = designer.evaluate(
            intent="BUILD",
            emotional_state="neutral",
            confidence=0.92,
            response_text="Building the auth module now with JWT tokens.",
        )
        assert result.component_type == "storybook_cards"

    def test_debug_intent_gets_timeline(self, designer):
        result = designer.evaluate(
            intent="DEBUG",
            emotional_state="neutral",
            confidence=0.80,
            response_text="Tracing the null pointer exception in the pipeline.",
        )
        assert result.component_type == "timeline"

    def test_audit_intent_gets_comparison_table(self, designer):
        result = designer.evaluate(
            intent="AUDIT",
            emotional_state="neutral",
            confidence=0.88,
            response_text="Security audit complete. CVE scan passed.",
        )
        assert result.component_type == "comparison_table"

    def test_design_intent_gets_diagram_embed(self, designer):
        result = designer.evaluate(
            intent="DESIGN",
            emotional_state="excited",
            confidence=0.91,
            response_text="The data flow diagram is ready.",
        )
        assert result.component_type == "diagram_embed"

    def test_explain_intent_gets_prose(self, designer):
        result = designer.evaluate(
            intent="EXPLAIN",
            emotional_state="neutral",
            confidence=0.87,
            response_text="OAuth2 works by delegating authentication to a trusted provider.",
        )
        assert result.component_type == "prose"

    def test_frustrated_eq_maps_red_palette(self, designer):
        result = designer.evaluate(
            intent="EXPLAIN",
            emotional_state="frustrated",
            confidence=0.70,
            response_text="I understand this is difficult.",
        )
        assert result.palette_key == "system_red"

    def test_excited_eq_maps_green_palette(self, designer):
        result = designer.evaluate(
            intent="BUILD",
            emotional_state="excited",
            confidence=0.95,
            response_text="Let's go, building the feature!",
        )
        assert result.palette_key == "system_green"

    def test_unknown_intent_falls_back_gracefully(self, designer):
        result = designer.evaluate(
            intent="UNKNOWN_XYZ",
            emotional_state="neutral",
            confidence=0.60,
            response_text="Some response text here.",
        )
        assert isinstance(result, DesignDirective)
        assert result.component_type == "prose"

    def test_low_confidence_sets_confidence_visual(self, designer):
        result = designer.evaluate(
            intent="BUILD",
            emotional_state="uncertain",
            confidence=0.40,
            response_text="I am not sure about this approach.",
        )
        assert result.confidence_visual == "low"

    def test_high_confidence_sets_confidence_visual(self, designer):
        result = designer.evaluate(
            intent="BUILD",
            emotional_state="neutral",
            confidence=0.96,
            response_text="Generating auth module securely with full OWASP coverage.",
        )
        assert result.confidence_visual == "high"

    def test_thought_cards_always_present(self, designer):
        result = designer.evaluate(
            intent="EXPLAIN",
            emotional_state="neutral",
            confidence=0.88,
            response_text="Here is the explanation.",
        )
        assert isinstance(result.thought_cards, list)
        assert len(result.thought_cards) >= 1

    def test_memory_card_present_when_recalled(self, designer):
        result = designer.evaluate(
            intent="BUILD",
            emotional_state="neutral",
            confidence=0.88,
            response_text="Building on what you told me earlier.",
            memory_recalled=True,
        )
        phases = [c.phase for c in result.thought_cards]
        assert "memory" in phases

    def test_memory_card_absent_when_not_recalled(self, designer):
        result = designer.evaluate(
            intent="BUILD",
            emotional_state="neutral",
            confidence=0.88,
            response_text="Fresh start response.",
            memory_recalled=False,
        )
        phases = [c.phase for c in result.thought_cards]
        assert "memory" not in phases

    def test_emphasis_words_populated_from_response(self, designer):
        result = designer.evaluate(
            intent="EXPLAIN",
            emotional_state="neutral",
            confidence=0.88,
            response_text="The authentication flow uses cryptographic token validation.",
        )
        assert isinstance(result.emphasis_words, list)
        assert len(result.emphasis_words) <= 6

    def test_design_card_present_in_thought_cards(self, designer):
        result = designer.evaluate(
            intent="BUILD",
            emotional_state="neutral",
            confidence=0.88,
            response_text="Building with SOTA patterns.",
        )
        phases = [c.phase for c in result.thought_cards]
        assert "design" in phases

    def test_jit_card_present_with_signals(self, designer):
        result = designer.evaluate(
            intent="BUILD",
            emotional_state="neutral",
            confidence=0.92,
            response_text="Using latest SOTA approach.",
            jit_signal_count=3,
        )
        phases = [c.phase for c in result.thought_cards]
        assert "jit" in phases

    def test_to_dict_is_json_serialisable(self, designer):
        import json
        result = designer.evaluate(
            intent="EXPLAIN",
            emotional_state="neutral",
            confidence=0.90,
            response_text="Testing JSON serialisability of the directive.",
        )
        out = json.dumps(result.to_dict())
        assert '"component_type"' in out


# ── analyze_partial_prompt ────────────────────────────────────────────────────

class TestAnalyzePartialPrompt:
    def test_empty_string(self):
        r = analyze_partial_prompt("")
        assert r["comprehension_level"] == "listening"
        assert r["visual_indicator"] in ("listening", "nodding")

    def test_very_short_text(self):
        r = analyze_partial_prompt("hi")
        assert r["comprehension_level"] in ("listening", "vague")

    def test_clear_build_intent(self):
        r = analyze_partial_prompt(
            "build me a REST API with authentication and JWT tokens")
        assert r["comprehension_level"] in ("clear", "complex")
        assert r["detected_intent"] in (
            "BUILD", "EXPLAIN", "AUDIT", "DEBUG", "DESIGN", "IDEATE")

    def test_vague_text(self):
        r = analyze_partial_prompt("can you help")
        assert r["comprehension_level"] in ("vague", "listening")

    def test_result_has_all_keys(self):
        r = analyze_partial_prompt(
            "explain how OAuth2 works with refresh tokens")
        required_keys = {"comprehension_level", "visual_indicator", "prompt_suggestions",
                         "detected_intent", "word_count"}
        assert required_keys.issubset(r.keys())

    def test_word_count_correct(self):
        text = "build a simple REST API"
        r = analyze_partial_prompt(text)
        assert r["word_count"] == len(text.split())

    def test_prompt_suggestions_is_list(self):
        r = analyze_partial_prompt("fix my code")
        assert isinstance(r["prompt_suggestions"], list)

    def test_long_complex_prompt(self):
        text = ("Design an event-driven microservice architecture using Kafka, FastAPI, "
                "PostgreSQL with CQRS and event sourcing patterns, including health "
                "checks, circuit breakers, and OpenTelemetry tracing.")
        r = analyze_partial_prompt(text)
        assert r["comprehension_level"] in ("complex", "clear")
        assert r["word_count"] > 20

    def test_debug_intent_detection(self):
        r = analyze_partial_prompt(
            "debug the null pointer exception in auth pipeline")
        assert r["detected_intent"] in ("DEBUG", "BUILD", "EXPLAIN")

    def test_visual_indicator_valid_value(self):
        r = analyze_partial_prompt("audit the security of the API endpoints")
        valid = {"nodding", "thinking", "listening", "confused_tilt"}
        assert r["visual_indicator"] in valid
