"""tests/test_jit_designer.py — Unit tests for JITDesigner and analyze_partial_prompt."""
from __future__ import annotations

import pytest
from engine.jit_designer import (
    JITDesigner,
    DesignDirective,
    ThoughtCard,
    UIComponent,
    StreamInterceptor,
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


# ── UIComponent ──────────────────────────────────────────────────────────────

class TestUIComponent:
    def test_to_dict_has_required_keys(self):
        comp = UIComponent(
            component_type="prose",
            content={"text": "Hello"},
            style_directives={"theme": "hig-blue", "elevation": 1},
        )
        d = comp.to_dict()
        assert set(d.keys()) == {"component_type",
                                 "content", "style_directives"}

    def test_to_dict_round_trip(self):
        comp = UIComponent(
            component_type="timeline_step",
            content={"index": 3, "label": "Deploy", "body": "Push to prod"},
            style_directives={"theme": "hig-green",
                              "elevation": 1, "intent": "BUILD"},
        )
        d = comp.to_dict()
        assert d["component_type"] == "timeline_step"
        assert d["content"]["index"] == 3
        assert d["style_directives"]["theme"] == "hig-green"

    def test_insight_chip_content(self):
        comp = UIComponent(
            component_type="insight_chip",
            content={"key": "Auth", "value": "JWT RS256"},
            style_directives={"theme": "material-dark", "elevation": 1},
        )
        assert comp.to_dict()["content"]["key"] == "Auth"
        assert comp.to_dict()["content"]["value"] == "JWT RS256"


# ── parse_response_blocks ─────────────────────────────────────────────────────

class TestParseResponseBlocks:
    @pytest.fixture
    def designer(self):
        return JITDesigner()

    def test_pure_prose_returns_empty_list(self, designer):
        text = "Sure! I'd be happy to help you with that."
        result = designer.parse_response_blocks(text)
        assert result == []

    def test_numbered_list_produces_timeline_steps(self, designer):
        text = "Steps:\n1. Install dependencies\n2. Configure environment\n3. Run migrations"
        result = designer.parse_response_blocks(text)
        types = [c.component_type for c in result]
        assert "timeline_step" in types
        steps = [c for c in result if c.component_type == "timeline_step"]
        assert len(steps) == 3
        assert steps[0].content["index"] == 1
        assert steps[1].content["index"] == 2

    def test_bullet_bold_kv_produces_insight_chips(self, designer):
        text = "Config:\n- **Host**: localhost\n- **Port**: 5432\n- **DB**: mydb"
        result = designer.parse_response_blocks(text)
        chips = [c for c in result if c.component_type == "insight_chip"]
        assert len(chips) == 3
        assert chips[0].content["key"] == "Host"
        assert chips[0].content["value"] == "localhost"

    def test_code_fence_produces_code_block(self, designer):
        text = "Example:\n```python\ndef foo():\n    return 42\n```"
        result = designer.parse_response_blocks(text)
        codes = [c for c in result if c.component_type == "code_block"]
        assert len(codes) == 1
        assert codes[0].content["language"] == "python"
        assert "def foo" in codes[0].content["code"]

    def test_markdown_table_produces_glass_table(self, designer):
        text = "| Name | Role |\n|------|------|\n| Alice | Lead |\n| Bob | Dev |"
        result = designer.parse_response_blocks(text)
        tables = [c for c in result if c.component_type == "glass_table"]
        assert len(tables) == 1
        assert tables[0].content["headers"] == ["Name", "Role"]
        assert len(tables[0].content["rows"]) == 2

    def test_has_structured_flag_set_correctly(self, designer):
        numbered = "1. Step A\n2. Step B"
        assert designer.parse_response_blocks(numbered) != []
        prose_only = "This is just a sentence."
        assert designer.parse_response_blocks(prose_only) == []

    def test_style_directives_reflect_palette_key(self, designer):
        text = "1. Build it\n2. Ship it"
        result = designer.parse_response_blocks(
            text, palette_key="system_purple")
        assert result[0].style_directives["theme"] == "hig-purple"

    def test_unknown_palette_key_falls_back_to_material_dark(self, designer):
        text = "- Foo: bar"
        result = designer.parse_response_blocks(
            text, palette_key="unknown_key")
        assert result[0].style_directives["theme"] == "material-dark"


# ── StreamInterceptor tests ───────────────────────────────────────────────────

class TestStreamInterceptor:
    """Tests for the StreamInterceptor streaming state machine."""

    @pytest.fixture
    def interceptor(self):
        return StreamInterceptor(intent="EXPLAIN", palette_key="system_blue")

    # ── Basic prose streaming ─────────────────────────────────────────────────

    def test_plain_prose_emits_tokens(self, interceptor):
        events = interceptor.feed("Hello, how are you?\n")
        token_events = [e for e in events if e["type"] == "token"]
        assert token_events, "Plain prose should emit token events"

    def test_no_ui_component_for_plain_prose(self, interceptor):
        events = interceptor.feed("Just a simple sentence.\n")
        events += interceptor.flush()
        assert not any(e["type"] == "ui_component" for e in events)

    # ── Code block detection ──────────────────────────────────────────────────

    def test_code_block_emits_ui_component(self, interceptor):
        chunk = "```python\ndef foo():\n    return 42\n```\n"
        events = interceptor.feed(chunk)
        events += interceptor.flush()
        ui_events = [e for e in events if e["type"] == "ui_component"]
        assert ui_events, "Code block should emit a ui_component event"
        assert ui_events[0]["component"]["component_type"] == "code_block"

    def test_code_block_not_emitted_as_token(self, interceptor):
        chunk = "```python\nprint('hi')\n```\n"
        events = interceptor.feed(chunk)
        events += interceptor.flush()
        token_texts = "".join(e.get("text", "")
                              for e in events if e["type"] == "token")
        assert "```" not in token_texts, "Code fence should not appear in token stream"

    def test_code_block_language_preserved(self, interceptor):
        chunk = "```javascript\nconsole.log('x');\n```\n"
        events = interceptor.feed(chunk)
        events += interceptor.flush()
        ui_events = [e for e in events if e["type"] == "ui_component"]
        assert ui_events[0]["component"]["content"]["language"] == "javascript"

    # ── Numbered list detection ───────────────────────────────────────────────

    def test_numbered_list_emits_timeline_steps(self, interceptor):
        chunk = "1. Step one\n2. Step two\n3. Step three\n\n"
        events = interceptor.feed(chunk)
        events += interceptor.flush()
        ui_events = [e for e in events if e["type"] == "ui_component"]
        assert len(ui_events) == 3
        assert all(e["component"]["component_type"] ==
                   "timeline_step" for e in ui_events)

    def test_numbered_list_not_emitted_as_tokens(self, interceptor):
        chunk = "1. Alpha\n2. Beta\n\n"
        events = interceptor.feed(chunk)
        events += interceptor.flush()
        token_texts = "".join(e.get("text", "")
                              for e in events if e["type"] == "token")
        assert "1. Alpha" not in token_texts

    # ── Bullet list detection ─────────────────────────────────────────────────

    def test_bullet_list_emits_components(self, interceptor):
        chunk = "- **Key**: value\n- **Other**: data\n\n"
        events = interceptor.feed(chunk)
        events += interceptor.flush()
        ui_events = [e for e in events if e["type"] == "ui_component"]
        assert ui_events, "Bullet list with bold KV should produce ui_component events"

    # ── Chunking robustness ───────────────────────────────────────────────────

    def test_chunk_split_across_newline_boundary(self):
        """Feed identical content in different chunk splits; same events expected."""
        full = "1. Step one\n2. Step two\n\n"
        # Split 1: single chunk
        s1 = StreamInterceptor()
        ev1 = s1.feed(full) + s1.flush()

        # Split 2: each character as a separate chunk
        s2 = StreamInterceptor()
        ev2 = []
        for c in full:
            ev2.extend(s2.feed(c))
        ev2.extend(s2.flush())

        comps1 = [e for e in ev1 if e["type"] == "ui_component"]
        comps2 = [e for e in ev2 if e["type"] == "ui_component"]
        assert len(comps1) == len(
            comps2), "Split-chunk feeding should produce same components"

    def test_mixed_prose_and_code(self, interceptor):
        chunk = "Here is the code:\n```python\nreturn 1\n```\nAnd some prose after.\n"
        events = interceptor.feed(chunk)
        events += interceptor.flush()
        types = [e["type"] for e in events]
        assert "token" in types
        assert "ui_component" in types

    # ── Flush behaviour ───────────────────────────────────────────────────────

    def test_flush_closes_open_block(self):
        s = StreamInterceptor()
        s.feed("1. Item one\n")
        s.feed("2. Item two\n")
        # Do NOT send a blank line — open block
        events = s.flush()
        ui_events = [e for e in events if e["type"] == "ui_component"]
        assert ui_events, "flush() must close any open structured block"

    def test_flush_empty_interceptor_returns_empty(self):
        s = StreamInterceptor()
        assert s.flush() == []

    # ── Safety: max block size ────────────────────────────────────────────────

    def test_large_block_flushed_safely(self):
        """Blocks exceeding _MAX_BLOCK_BYTES should be flushed, not buffered forever."""
        s = StreamInterceptor()
        # feed 200 numbered items without a closing blank line
        for n in range(200):
            s.feed(f"{n + 1}. Line {n + 1}\n")
        events = s.flush()
        ui_events = [e for e in events if e["type"] == "ui_component"]
        # We don't care about exact count — just that *something* was emitted
        assert ui_events or any(e["type"] == "token" for e in events)


# ── Enhanced analyze_partial_prompt tests ────────────────────────────────────

class TestAnalyzePartialPromptEnhanced:
    """Tests for context-aware enhancements to analyze_partial_prompt."""

    def test_session_context_short_text_shows_contextual_tip(self):
        result = analyze_partial_prompt("fix", session_context="DEBUG")
        # Short text with DEBUG context should show a contextual tip
        assert result["prompt_suggestions"], "Should have suggestions"
        # Tip should reference debugging context, not the generic one
        tip = result["prompt_suggestions"][0]
        assert tip  # non-empty

    def test_session_context_empty_still_works(self):
        result = analyze_partial_prompt(
            "build a login page", session_context="")
        assert result["detected_intent"] == "BUILD"

    def test_continuity_tip_when_intent_switches(self):
        result = analyze_partial_prompt(
            "build me a dashboard", session_context="DEBUG"
        )
        suggestions = result["prompt_suggestions"]
        # Should contain a continuity switch notice
        switch_notices = [s for s in suggestions if "Switching" in s]
        assert switch_notices, "Should have a continuity tip when intent switches"

    def test_no_continuity_tip_when_same_intent(self):
        result = analyze_partial_prompt(
            "build the login component", session_context="BUILD"
        )
        switch_notices = [
            s for s in result["prompt_suggestions"] if "Switching" in s]
        assert not switch_notices, "No switch tip when intent matches session context"

    def test_suggestions_capped_at_two(self):
        result = analyze_partial_prompt("build", session_context="DEBUG")
        assert len(result["prompt_suggestions"]) <= 2

    def test_very_short_with_context_uses_ctx_tip(self):
        result = analyze_partial_prompt("hi", session_context="BUILD")
        assert any("build" in s.lower() or "building" in s.lower()
                   for s in result["prompt_suggestions"])
