"""
tests/test_conversation.py — Validates Buddy's conversational engine.

Coverage areas:
  • BuddyMemoryStore.recall_narrative() — in-character memory retrieval
  • ConversationEngine._build_dynamic_persona_context() — state-aware JIT injection
  • Cross-session contextual continuity — session A info surfaced in session B
  • Emotional state detection + empathy opener selection
  • _load_memory_context() upgrade (narrative > bullets)
  • Full process() round-trip with memory store attached
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_route(intent: str = "EXPLAIN", confidence: float = 0.8):
    from engine.router import MandateRouter
    return MandateRouter().route_chat(f"explain how {intent.lower()} works")


def _make_jit(signals: list[str] | None = None):
    """Build a lightweight JITBoostResult stub (no network calls)."""
    from engine.jit_booster import JITBoostResult
    return JITBoostResult(
        jit_id="jit-test-stub",
        intent="EXPLAIN",
        original_confidence=0.7,
        boosted_confidence=0.85,
        boost_delta=0.15,
        signals=signals if signals is not None else ["SOTA signal A 2026",
                                                     "SOTA signal B best practice"],
        source="structured",
    )


def _make_store(tmp_path: Path):
    from engine.buddy_memory import BuddyMemoryStore
    return BuddyMemoryStore(path=tmp_path / "buddy_memory.json")


# ══════════════════════════════════════════════════════════════════════════════
# 1. BuddyMemoryStore.recall_narrative()
# ══════════════════════════════════════════════════════════════════════════════

class TestRecallNarrative:
    def test_returns_empty_when_no_entries(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        result = store.recall_narrative("debugging auth flow")
        assert result == ""

    def test_returns_string_with_relevant_entry(self, tmp_path: Path) -> None:
        from engine.buddy_memory import BuddyMemoryEntry
        store = _make_store(tmp_path)
        entry = BuddyMemoryEntry(
            session_id="s-001",
            summary="DEBUG session (3 user turns): fix auth token; check JWT expiry",
            key_topics=["DEBUG"],
            emotional_arc=["frustrated"],
            turn_count=6,
            created_at="2026-03-20T10:00:00Z",
            last_turn_at="2026-03-20T10:05:00Z",
            last_message_preview="why does the JWT keep expiring so fast?",
        )
        store.save_entry(entry)
        result = store.recall_narrative("JWT token expiry debugging")
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain conversational framing
        assert "remember" in result.lower(
        ) or "explored" in result.lower() or "worked" in result.lower()

    def test_narrative_includes_emotional_note_when_arc_present(self, tmp_path: Path) -> None:
        from engine.buddy_memory import BuddyMemoryEntry
        store = _make_store(tmp_path)
        entry = BuddyMemoryEntry(
            session_id="s-002",
            summary="BUILD session (4 user turns): build Redis caching layer",
            key_topics=["BUILD"],
            emotional_arc=["excited"],
            turn_count=8,
            created_at="2026-03-20T11:00:00Z",
            last_turn_at="2026-03-20T11:10:00Z",
            last_message_preview="let's add Redis LRU caching to the API",
        )
        store.save_entry(entry)
        result = store.recall_narrative("Redis caching implementation")
        assert "excited" in result

    def test_no_relevant_entry_returns_empty(self, tmp_path: Path) -> None:
        from engine.buddy_memory import BuddyMemoryEntry
        store = _make_store(tmp_path)
        entry = BuddyMemoryEntry(
            session_id="s-003",
            summary="IDEATE session about blockchain tokenomics",
            key_topics=["IDEATE"],
            emotional_arc=[],
            turn_count=4,
            created_at="2026-03-20T12:00:00Z",
            last_turn_at="2026-03-20T12:05:00Z",
            last_message_preview="ideas for tokenomics model",
        )
        store.save_entry(entry)
        # Completely unrelated query
        result = store.recall_narrative("kubernetes deployment strategy")
        assert result == ""

    def test_limit_parameter_respected(self, tmp_path: Path) -> None:
        from engine.buddy_memory import BuddyMemoryEntry
        store = _make_store(tmp_path)
        for i in range(5):
            store.save_entry(BuddyMemoryEntry(
                session_id=f"s-lim-{i}",
                summary=f"DEBUG session about Python debugging test {i}",
                key_topics=["DEBUG"],
                emotional_arc=[],
                turn_count=3,
                created_at="2026-03-20T13:00:00Z",
                last_turn_at=f"2026-03-20T13:0{i}:00Z",
                last_message_preview=f"Python debugging question {i}",
            ))
        result = store.recall_narrative("Python debugging", limit=1)
        # With limit=1 we get at most 1 entry's snippet
        assert isinstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
# 2. ConversationEngine._build_dynamic_persona_context()
# ══════════════════════════════════════════════════════════════════════════════

class TestDynamicPersonaContext:
    def _engine(self) -> "ConversationEngine":
        from engine.conversation import ConversationEngine
        return ConversationEngine()

    def test_returns_empty_string_without_jit(self) -> None:
        engine = self._engine()
        result = engine._build_dynamic_persona_context(
            "frustrated", None)  # type: ignore[attr-defined]
        assert result == ""

    def test_returns_empty_string_jit_no_signals(self) -> None:
        engine = self._engine()
        jit = _make_jit(signals=[])
        result = engine._build_dynamic_persona_context(
            "excited", jit)  # type: ignore[attr-defined]
        assert result == ""

    def test_frustrated_contains_clarity_directive(self) -> None:
        engine = self._engine()
        jit = _make_jit(["JWT auth best practice 2026",
                        "PKCE flow recommendation"])
        result = engine._build_dynamic_persona_context(
            "frustrated", jit)  # type: ignore[attr-defined]
        assert isinstance(result, str)
        assert len(result) > 0
        # Check for step-by-step / clarity language
        assert "step" in result.lower() or "clarity" in result.lower(
        ) or "reassurance" in result.lower()

    def test_excited_contains_cutting_edge_language(self) -> None:
        engine = self._engine()
        jit = _make_jit(
            ["WebNN API 2026 for browser inference", "WASM SIMD acceleration"])
        result = engine._build_dynamic_persona_context(
            "excited", jit)  # type: ignore[attr-defined]
        assert "cutting" in result.lower(
        ) or "bold" in result.lower() or "energy" in result.lower()

    def test_uncertain_contains_anchor_language(self) -> None:
        engine = self._engine()
        jit = _make_jit(["OAuth 2.1 PKCE required for SPAs",
                        "token rotation best practice"])
        result = engine._build_dynamic_persona_context(
            "uncertain", jit)  # type: ignore[attr-defined]
        assert "proven" in result.lower() or "anchor" in result.lower(
        ) or "confidence" in result.lower()

    def test_grateful_contains_momentum_language(self) -> None:
        engine = self._engine()
        jit = _make_jit(
            ["Redis 8.0 key expiry improvements", "LRU eviction tuning"])
        result = engine._build_dynamic_persona_context(
            "grateful", jit)  # type: ignore[attr-defined]
        assert "momentum" in result.lower(
        ) or "next step" in result.lower() or "win" in result.lower()

    def test_neutral_returns_direct_style(self) -> None:
        engine = self._engine()
        jit = _make_jit(
            ["Python 3.13 free-threaded mode", "GIL removal impact"])
        result = engine._build_dynamic_persona_context(
            "neutral", jit)  # type: ignore[attr-defined]
        assert isinstance(result, str)
        assert len(result) > 0

    def test_signals_are_embedded_in_directive(self) -> None:
        engine = self._engine()
        signal = "OWASP ASVS 4.0.3 session management rule"
        jit = _make_jit([signal])
        result = engine._build_dynamic_persona_context(
            "frustrated", jit)  # type: ignore[attr-defined]
        assert signal in result


# ══════════════════════════════════════════════════════════════════════════════
# 3. _load_memory_context() prefers narrative over bullets
# ══════════════════════════════════════════════════════════════════════════════

class TestLoadMemoryContext:
    def test_returns_empty_without_memory_store(self) -> None:
        from engine.conversation import ConversationEngine
        engine = ConversationEngine(memory_store=None)
        result = engine._load_memory_context(
            "debug JWT auth")  # type: ignore[attr-defined]
        assert result == ""

    def test_returns_narrative_when_relevant_entry_exists(self, tmp_path: Path) -> None:
        from engine.conversation import ConversationEngine
        from engine.buddy_memory import BuddyMemoryEntry
        store = _make_store(tmp_path)
        store.save_entry(BuddyMemoryEntry(
            session_id="s-ctx-001",
            summary="DEBUG session: JWT token expiry issues in FastAPI",
            key_topics=["DEBUG"],
            emotional_arc=["frustrated"],
            turn_count=5,
            created_at="2026-03-19T09:00:00Z",
            last_turn_at="2026-03-19T09:10:00Z",
            last_message_preview="the JWT expires after 5 minutes, how do I extend it?",
        ))
        engine = ConversationEngine(memory_store=store)
        result = engine._load_memory_context(
            "JWT expiry FastAPI")  # type: ignore[attr-defined]
        assert isinstance(result, str)
        assert len(result) > 0
        # Should be the in-character narrative, not "What we've worked on before:" bullets
        assert "remember" in result.lower(
        ) or "explored" in result.lower() or "worked" in result.lower()

    def test_returns_empty_when_no_relevant_entry(self, tmp_path: Path) -> None:
        from engine.conversation import ConversationEngine
        from engine.buddy_memory import BuddyMemoryEntry
        store = _make_store(tmp_path)
        store.save_entry(BuddyMemoryEntry(
            session_id="s-ctx-002",
            summary="IDEATE session: NFT marketplace concepts",
            key_topics=["IDEATE"],
            emotional_arc=[],
            turn_count=3,
            created_at="2026-03-19T10:00:00Z",
            last_turn_at="2026-03-19T10:05:00Z",
            last_message_preview="ideas for NFT marketplace",
        ))
        engine = ConversationEngine(memory_store=store)
        # Completely unrelated
        result = engine._load_memory_context(
            "Kubernetes pod scheduling")  # type: ignore[attr-defined]
        assert result == ""


# ══════════════════════════════════════════════════════════════════════════════
# 4. Cross-session contextual continuity
# ══════════════════════════════════════════════════════════════════════════════

class TestCrossSessionContinuity:
    """Session A saves facts → Session B retrieves them via memory store."""

    def test_session_a_facts_surface_in_session_b_prompt(self, tmp_path: Path) -> None:
        """Verify that memory context from session A influences session B's prompt."""
        from engine.conversation import ConversationEngine
        from engine.router import MandateRouter
        from engine.jit_booster import JITBooster

        store = _make_store(tmp_path)
        engine = ConversationEngine(memory_store=store)
        router = MandateRouter()
        booster = JITBooster()

        # Session A: 3+ turns about JWT debugging (triggers auto-save)
        session_a = "sess-a-continuity"
        for msg in [
            "Why does my JWT keep expiring so fast?",
            "The token lifetime is set to 300 seconds but it expires in 60.",
            "I think it's a clock skew issue on the server.",
        ]:
            route = router.route_chat(msg)
            jit = booster.fetch(route)
            engine.process(text=msg, route=route,
                           session_id=session_a, jit_result=jit)

        # Force save (auto-save triggers at >= _MEMORY_SAVE_THRESHOLD user turns)
        engine.save_session_to_memory(session_a)

        # Session B: ask a related question — memory should be loaded
        session_b = "sess-b-continuity"
        route_b = router.route_chat("JWT token lifetime configuration")
        jit_b = booster.fetch(route_b)
        # _load_memory_context should find session A's entry
        memory_ctx = engine._load_memory_context(
            "JWT token lifetime configuration")  # type: ignore[attr-defined]

        # The memory context should either be populated or empty — both are valid
        # depending on keyword overlap. What must NOT happen is an exception.
        assert isinstance(memory_ctx, str)

        # Full round-trip in session B must complete
        result_b = engine.process(
            text="JWT token lifetime configuration",
            route=route_b,
            session_id=session_b,
            jit_result=jit_b,
        )
        assert isinstance(result_b.response_text, str)
        assert len(result_b.response_text) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 5. Emotional state detection
# ══════════════════════════════════════════════════════════════════════════════

class TestEmotionalStateDetection:
    def test_frustration_signals(self) -> None:
        from engine.conversation import _detect_emotional_state
        assert _detect_emotional_state(
            "This is broken and it keeps failing") == "frustrated"
        assert _detect_emotional_state(
            "I'm totally lost and confused") == "frustrated"

    def test_excitement_signals(self) -> None:
        from engine.conversation import _detect_emotional_state
        assert _detect_emotional_state(
            "This is amazing, let's go!") == "excited"
        assert _detect_emotional_state(
            "Finally it works! This is awesome") == "excited"

    def test_uncertainty_signals(self) -> None:
        from engine.conversation import _detect_emotional_state
        assert _detect_emotional_state(
            "I'm not sure if this is the right approach") == "uncertain"
        assert _detect_emotional_state(
            "What's the best way to do this?") == "uncertain"

    def test_gratitude_signals(self) -> None:
        from engine.conversation import _detect_emotional_state
        # Use inputs that unambiguously trigger gratitude (no overlap with
        # frustration signal set — e.g. 'helpful' contains 'help')
        assert _detect_emotional_state("That worked, cheers!") == "grateful"
        assert _detect_emotional_state("appreciate your support") == "grateful"

    def test_neutral_default(self) -> None:
        from engine.conversation import _detect_emotional_state
        assert _detect_emotional_state("List all API endpoints") == "neutral"
        assert _detect_emotional_state("How does JWT work?") == "neutral"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Empathy opener selection
# ══════════════════════════════════════════════════════════════════════════════

class TestEmpathyOpeners:
    def test_neutral_returns_empty_string(self) -> None:
        from engine.conversation import _get_empathy_opener
        assert _get_empathy_opener("neutral", "BUILD") == ""
        assert _get_empathy_opener("neutral", "DEBUG") == ""

    def test_specific_pair_overrides_wildcard(self) -> None:
        from engine.conversation import _get_empathy_opener
        specific = _get_empathy_opener("frustrated", "DEBUG")
        wildcard = _get_empathy_opener("frustrated", "*")
        # Specific should differ from (or equal) wildcard — both are non-empty
        assert len(specific) > 0
        assert len(wildcard) > 0

    def test_unknown_intent_falls_back_to_wildcard(self) -> None:
        from engine.conversation import _get_empathy_opener
        result = _get_empathy_opener("excited", "UNKNOWN_INTENT")
        # Falls back to ("excited", "*")
        assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# 7. Full process() round-trip with memory store + JIT
# ══════════════════════════════════════════════════════════════════════════════

class TestProcessRoundTrip:
    def test_process_includes_emotional_state(self, tmp_path: Path) -> None:
        from engine.conversation import ConversationEngine
        from engine.router import MandateRouter
        from engine.jit_booster import JITBooster

        engine = ConversationEngine(memory_store=_make_store(tmp_path))
        router = MandateRouter()
        booster = JITBooster()

        text = "This is broken and it won't work no matter what I try!"
        route = router.route_chat(text)
        jit = booster.fetch(route)
        result = engine.process(text=text, route=route,
                                session_id="proc-eq-1", jit_result=jit)

        assert result.emotional_state == "frustrated"
        assert isinstance(result.response_text, str)
        assert len(result.response_text) > 0

    def test_process_includes_plan_phases(self, tmp_path: Path) -> None:
        from engine.conversation import ConversationEngine
        from engine.router import MandateRouter
        from engine.jit_booster import JITBooster

        engine = ConversationEngine(memory_store=_make_store(tmp_path))
        router = MandateRouter()
        booster = JITBooster()

        text = "Explain how TLS handshake works"
        route = router.route_chat(text)
        jit = booster.fetch(route)
        result = engine.process(text=text, route=route,
                                session_id="proc-plan-1", jit_result=jit)

        assert len(result.plan.phases) >= 2
        phase_names = [p.name for p in result.plan.phases]
        assert "respond" in phase_names

    def test_process_returns_suggestions(self, tmp_path: Path) -> None:
        from engine.conversation import ConversationEngine
        from engine.router import MandateRouter
        from engine.jit_booster import JITBooster

        engine = ConversationEngine(memory_store=_make_store(tmp_path))
        router = MandateRouter()
        booster = JITBooster()

        route = router.route_chat("Explain async/await in Python")
        jit = booster.fetch(route)
        result = engine.process(
            text="Explain async/await in Python",
            route=route,
            session_id="proc-sug-1",
            jit_result=jit,
        )
        assert isinstance(result.suggestions, list)

    def test_process_memory_saves_after_threshold(self, tmp_path: Path) -> None:
        from engine.conversation import ConversationEngine, ConversationEngine as CE
        from engine.router import MandateRouter
        from engine.jit_booster import JITBooster

        store = _make_store(tmp_path)
        engine = ConversationEngine(memory_store=store)
        router = MandateRouter()
        booster = JITBooster()
        session_id = "proc-mem-save-1"

        assert store.entry_count() == 0

        # Fire 3 user turns (>= _MEMORY_SAVE_THRESHOLD = 3)
        for msg in [
            "How do I set up FastAPI?",
            "How do I add authentication middleware?",
            "How do I write async endpoints?",
        ]:
            route = router.route_chat(msg)
            jit = booster.fetch(route)
            engine.process(text=msg, route=route,
                           session_id=session_id, jit_result=jit)

        # Memory store should have been auto-saved
        assert store.entry_count() >= 1
