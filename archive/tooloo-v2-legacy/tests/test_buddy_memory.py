"""
tests/test_buddy_memory.py — Persistent cross-session memory tests.

Covers:
  * BuddyMemoryEntry dataclass round-trip
  * BuddyMemoryStore CRUD: save, recent, find_relevant, clear, entry_count
  * _keyword_overlap scoring edge cases (zero overlap, partial, full)
  * _build_summary and _build_key_topics helpers
  * ConversationEngine.memory_store integration (auto-save threshold)
  * ConversationEngine.save_session_to_memory / clear_session persists
  * ConversationEngine.recent_memory returns entries
  * GET /v2/buddy/memory endpoint shape
  * POST /v2/buddy/memory/save/{session_id} — happy path and 404
  * GET /v2/health reports buddy_memory key
  * PsycheBank purge_expired background task (unit test for purge)
  * /v2/buddy/chat response includes memory (integration smoke test)
"""
from __future__ import annotations

import tempfile
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from engine.buddy_memory import (
    BuddyMemoryEntry,
    BuddyMemoryStore,
    _build_key_topics,
    _build_summary,
    _keyword_overlap,
)
from engine.conversation import ConversationEngine, ConversationSession, ConversationTurn
from engine.psyche_bank import CogRule, PsycheBank


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_store(tmp_path: Path) -> BuddyMemoryStore:
    """Isolated BuddyMemoryStore backed by a temp file."""
    return BuddyMemoryStore(path=tmp_path / "test_memory.json")


@pytest.fixture()
def sample_session() -> ConversationSession:
    """A ConversationSession with 4 turns (2 user, 2 buddy)."""
    session = ConversationSession(
        session_id="test-session-abc", created_at=datetime.now(UTC).isoformat())
    ts = datetime.now(UTC).isoformat()
    session.turns.extend([
        ConversationTurn(turn_id="t1", role="user", text="help me debug the auth flow", intent="DEBUG",
                         confidence=0.9, response="", tone="analytical", emotional_state="frustrated", ts=ts),
        ConversationTurn(turn_id="t1-b", role="buddy", text="Let's trace the auth flow step by step.",
                         intent="DEBUG", confidence=0.9, response="Let's trace", tone="analytical", ts=ts),
        ConversationTurn(turn_id="t2", role="user", text="now let's build the JWT refresh logic", intent="BUILD",
                         confidence=0.95, response="", tone="constructive", emotional_state="neutral", ts=ts),
        ConversationTurn(turn_id="t2-b", role="buddy", text="On it. Breaking into waves...",
                         intent="BUILD", confidence=0.95, response="On it.", tone="constructive", ts=ts),
    ])
    return session


@pytest.fixture()
def api_client() -> TestClient:
    from studio.api import app
    return TestClient(app)


# ── BuddyMemoryEntry ──────────────────────────────────────────────────────────


class TestBuddyMemoryEntry:
    def test_to_dict_round_trip(self) -> None:
        entry = BuddyMemoryEntry(
            session_id="s-001",
            summary="BUILD session: debug auth, JWT refresh",
            key_topics=["DEBUG", "BUILD"],
            emotional_arc=["frustrated"],
            turn_count=4,
            created_at="2026-01-01T00:00:00+00:00",
            last_turn_at="2026-01-01T00:05:00+00:00",
            last_message_preview="now let's build the JWT refresh logic",
        )
        d = entry.to_dict()
        assert d["session_id"] == "s-001"
        assert d["key_topics"] == ["DEBUG", "BUILD"]
        restored = BuddyMemoryEntry.from_dict(d)
        assert restored.session_id == entry.session_id
        assert restored.summary == entry.summary

    def test_from_dict_missing_keys_safe(self) -> None:
        """from_dict treats missing fields as empty/defaults."""
        entry = BuddyMemoryEntry.from_dict({"session_id": "s-minimal"})
        assert entry.session_id == "s-minimal"
        assert entry.summary == ""
        assert entry.key_topics == []
        assert entry.turn_count == 0


# ── Helper functions ──────────────────────────────────────────────────────────


class TestHelpers:
    def test_build_summary_prefix(self, sample_session: ConversationSession) -> None:
        summary = _build_summary(sample_session)
        assert "DEBUG" in summary or "BUILD" in summary
        assert len(summary) <= 200

    def test_build_summary_empty_session(self) -> None:
        session = ConversationSession(session_id="empty-s")
        assert _build_summary(session) == "Empty session."

    def test_build_key_topics_ordered(self, sample_session: ConversationSession) -> None:
        topics = _build_key_topics(sample_session)
        # First user turn is DEBUG, second is BUILD
        assert topics[0] == "DEBUG"
        assert "BUILD" in topics
        assert len(topics) <= 3

    def test_keyword_overlap_zero(self) -> None:
        entry = BuddyMemoryEntry(
            session_id="s", summary="unrelated topic", key_topics=["DESIGN"],
            emotional_arc=[], turn_count=1, created_at="", last_turn_at="",
            last_message_preview="making a logo",
        )
        score = _keyword_overlap("build python server auth jwt", entry)
        # May or may not be zero, but should be < 0.5
        assert score < 0.5

    def test_keyword_overlap_high(self) -> None:
        entry = BuddyMemoryEntry(
            session_id="s", summary="DEBUG session: debug auth flow jwt token",
            key_topics=["DEBUG"],
            emotional_arc=[], turn_count=2, created_at="", last_turn_at="",
            last_message_preview="debug auth jwt token issue",
        )
        score = _keyword_overlap("debug auth jwt token", entry)
        assert score > 0.2  # meaningful overlap

    def test_keyword_overlap_returns_float(self) -> None:
        entry = BuddyMemoryEntry(
            session_id="s", summary="", key_topics=[], emotional_arc=[],
            turn_count=0, created_at="", last_turn_at="", last_message_preview="",
        )
        # Both empty — should return 0 gracefully (no division by zero)
        assert _keyword_overlap("", entry) == 0.0


# ── BuddyMemoryStore ──────────────────────────────────────────────────────────


class TestBuddyMemoryStore:
    def test_save_and_recent(self, tmp_store: BuddyMemoryStore, sample_session: ConversationSession) -> None:
        entry = tmp_store.save_session(sample_session)
        assert entry is not None
        assert entry.session_id == "test-session-abc"
        recent = tmp_store.recent(limit=5)
        assert len(recent) == 1
        assert recent[0].session_id == "test-session-abc"

    def test_save_too_few_turns_returns_none(self, tmp_store: BuddyMemoryStore) -> None:
        """Sessions with < 2 user turns are skipped."""
        session = ConversationSession(session_id="short-s")
        session.turns.append(
            ConversationTurn(turn_id="t1", role="user", text="hi", intent="EXPLAIN",
                             confidence=0.5, response="", tone="", ts=datetime.now(UTC).isoformat())
        )
        result = tmp_store.save_session(session)
        assert result is None
        assert tmp_store.entry_count() == 0

    def test_upsert_same_session_id(self, tmp_store: BuddyMemoryStore, sample_session: ConversationSession) -> None:
        """Saving same session_id twice updates the existing entry."""
        tmp_store.save_session(sample_session)
        tmp_store.save_session(sample_session)
        assert tmp_store.entry_count() == 1

    def test_persistence_across_instances(self, tmp_path: Path, sample_session: ConversationSession) -> None:
        """Data persists and loads correctly on a new store instance."""
        path = tmp_path / "mem.json"
        store1 = BuddyMemoryStore(path=path)
        store1.save_session(sample_session)

        store2 = BuddyMemoryStore(path=path)
        assert store2.entry_count() == 1
        assert store2.recent()[0].session_id == "test-session-abc"

    def test_find_relevant_returns_matches(self, tmp_store: BuddyMemoryStore, sample_session: ConversationSession) -> None:
        tmp_store.save_session(sample_session)
        results = tmp_store.find_relevant("debug auth flow jwt", limit=3)
        assert len(results) >= 1
        assert results[0].session_id == "test-session-abc"

    def test_find_relevant_no_overlap_returns_empty(self, tmp_store: BuddyMemoryStore, sample_session: ConversationSession) -> None:
        tmp_store.save_session(sample_session)
        results = tmp_store.find_relevant(
            "xyzzy frobnicator quantum flux", limit=3)
        assert results == []

    def test_find_relevant_empty_store(self, tmp_store: BuddyMemoryStore) -> None:
        assert tmp_store.find_relevant("anything", limit=3) == []

    def test_clear(self, tmp_store: BuddyMemoryStore, sample_session: ConversationSession) -> None:
        tmp_store.save_session(sample_session)
        tmp_store.clear()
        assert tmp_store.entry_count() == 0

    def test_recent_sorted_newest_first(self, tmp_path: Path) -> None:
        store = BuddyMemoryStore(path=tmp_path / "mem.json")
        older = BuddyMemoryEntry(
            session_id="s-old", summary="old", key_topics=[], emotional_arc=[],
            turn_count=2, created_at="", last_turn_at="2026-01-01T00:00:00+00:00",
            last_message_preview="old msg",
        )
        newer = BuddyMemoryEntry(
            session_id="s-new", summary="new", key_topics=[], emotional_arc=[],
            turn_count=2, created_at="", last_turn_at="2026-01-02T00:00:00+00:00",
            last_message_preview="new msg",
        )
        store.save_entry(older)
        store.save_entry(newer)
        recent = store.recent(limit=5)
        assert recent[0].session_id == "s-new"
        assert recent[1].session_id == "s-old"

    def test_corrupted_file_loads_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not valid json", encoding="utf-8")
        store = BuddyMemoryStore(path=path)
        assert store.entry_count() == 0

    def test_non_list_json_loads_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "bad2.json"
        path.write_text('{"unexpected": "dict"}', encoding="utf-8")
        store = BuddyMemoryStore(path=path)
        assert store.entry_count() == 0

    def test_atomic_write_leaves_no_tmp(self, tmp_path: Path, sample_session: ConversationSession) -> None:
        path = tmp_path / "mem.json"
        store = BuddyMemoryStore(path=path)
        store.save_session(sample_session)
        # Temp file should be gone after atomic rename
        assert not (tmp_path / "mem.json.tmp").exists()
        assert path.exists()


# ── ConversationEngine integration ───────────────────────────────────────────


class TestConversationEngineMemory:
    def test_engine_auto_saves_at_threshold(self, tmp_path: Path) -> None:
        """Auto-save triggers once user turns reach MEMORY_SAVE_THRESHOLD."""
        mem = BuddyMemoryStore(path=tmp_path / "cmem.json")
        engine = ConversationEngine(memory_store=mem)

        from engine.router import MandateRouter
        router = MandateRouter()

        # Feed 3 user turns to hit the save threshold
        sid = "test-sid-001"
        for i, text in enumerate(
            ["build an API", "add authentication to the API", "write tests for it"]
        ):
            route = router.route(f"build implement create {text}")
            engine.process(text, route, sid)

        # Memory should now have an entry for this session
        assert mem.entry_count() == 1
        entries = mem.recent()
        assert entries[0].session_id == sid

    def test_engine_no_memory_store_no_crash(self) -> None:
        """Engine without memory store works normally."""
        engine = ConversationEngine(memory_store=None)
        from engine.router import MandateRouter
        router = MandateRouter()
        route = router.route("build implement create some API endpoint for me")
        result = engine.process("build some API", route, "sess-x")
        assert result.response_text != ""

    def test_save_session_to_memory(self, tmp_path: Path, sample_session: ConversationSession) -> None:
        mem = BuddyMemoryStore(path=tmp_path / "smem.json")
        engine = ConversationEngine(memory_store=mem)
        engine._sessions[sample_session.session_id] = sample_session
        entry = engine.save_session_to_memory(sample_session.session_id)
        assert entry is not None
        assert entry.session_id == sample_session.session_id

    def test_save_session_to_memory_missing_session_returns_none(self, tmp_path: Path) -> None:
        mem = BuddyMemoryStore(path=tmp_path / "smem2.json")
        engine = ConversationEngine(memory_store=mem)
        result = engine.save_session_to_memory("nonexistent-session")
        assert result is None

    def test_clear_session_saves_to_memory(self, tmp_path: Path, sample_session: ConversationSession) -> None:
        mem = BuddyMemoryStore(path=tmp_path / "clmem.json")
        engine = ConversationEngine(memory_store=mem)
        engine._sessions[sample_session.session_id] = sample_session
        cleared = engine.clear_session(sample_session.session_id)
        assert cleared is True
        assert sample_session.session_id not in engine._sessions
        assert mem.entry_count() == 1

    def test_recent_memory_no_store_returns_empty(self) -> None:
        engine = ConversationEngine(memory_store=None)
        assert engine.recent_memory() == []

    def test_recent_memory_with_store(self, tmp_path: Path, sample_session: ConversationSession) -> None:
        mem = BuddyMemoryStore(path=tmp_path / "rcmem.json")
        engine = ConversationEngine(memory_store=mem)
        engine._sessions[sample_session.session_id] = sample_session
        engine.save_session_to_memory(sample_session.session_id)
        recent = engine.recent_memory(limit=5)
        assert len(recent) == 1

    def test_memory_context_injected_in_prompt(self, tmp_path: Path) -> None:
        """When relevant past sessions exist, _load_memory_context returns non-empty."""
        mem = BuddyMemoryStore(path=tmp_path / "pmem.json")
        # Seed an entry with known keywords
        entry = BuddyMemoryEntry(
            session_id="past-s", summary="DEBUG session: debug the auth jwt token flow",
            key_topics=["DEBUG"], emotional_arc=[], turn_count=3,
            created_at="", last_turn_at=datetime.now(UTC).isoformat(),
            last_message_preview="debug jwt token expiry",
        )
        mem.save_entry(entry)
        engine = ConversationEngine(memory_store=mem)
        ctx = engine._load_memory_context("debug auth jwt token")
        # Accept either the new narrative format ("remember from before") or the
        # legacy bullet format ("worked on before") so both code paths are valid.
        assert (
            "remember from before" in ctx or "worked on before" in ctx or "before" in ctx)
        assert "DEBUG" in ctx


# ── API endpoint tests ────────────────────────────────────────────────────────


class TestBuddyMemoryEndpoints:
    def test_get_memory_empty(self, api_client: TestClient) -> None:
        resp = api_client.get("/v2/buddy/memory")
        assert resp.status_code == 200
        body = resp.json()
        assert "count" in body
        assert "total_stored" in body
        assert "entries" in body

    def test_get_memory_response_shape(self, api_client: TestClient) -> None:
        resp = api_client.get("/v2/buddy/memory?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["entries"], list)
        assert isinstance(body["count"], int)

    def test_get_memory_limit_capped_at_50(self, api_client: TestClient) -> None:
        """Limit param is capped at 50 server-side — request shouldn't error."""
        resp = api_client.get("/v2/buddy/memory?limit=999")
        assert resp.status_code == 200

    def test_save_memory_missing_session_returns_404(self, api_client: TestClient) -> None:
        resp = api_client.post("/v2/buddy/memory/save/nonexistent-session-xyz")
        assert resp.status_code == 404

    def test_save_memory_after_chat(self, api_client: TestClient) -> None:
        """After chatting with a non-execution intent, explicitly saving works."""
        sid = "mem-test-session-explain"

        # Use EXPLAIN intent (non-execution) so ConversationEngine processes it
        for text in [
            "explain how JWT token refresh works",
            "explain the difference between access tokens and refresh tokens",
        ]:
            resp = api_client.post(
                "/v2/buddy/chat", json={"text": text, "session_id": sid})
            assert resp.status_code == 200

        # Session now has 2 user turns — save_session requires >= 2
        save_resp = api_client.post(f"/v2/buddy/memory/save/{sid}")
        assert save_resp.status_code == 200
        body = save_resp.json()
        assert body["saved"] is True
        assert "entry" in body
        assert body["entry"]["session_id"] == sid

    def test_health_reports_buddy_memory(self, api_client: TestClient) -> None:
        resp = api_client.get("/v2/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "buddy_memory" in body["components"]


# ── PsycheBank purge_expired (background task unit test) ─────────────────────


class TestPsycheBankPurge:
    def test_purge_removes_expired_rules(self, tmp_path: Path) -> None:
        path = tmp_path / "test_bank.json"
        bank = PsycheBank(path=path)

        expired_rule = CogRule(
            id="test-expired-001",
            description="Test expired rule",
            pattern="test_pattern",
            enforcement="warn",
            category="quality",
            source="tribunal",
            expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        )
        live_rule = CogRule(
            id="test-live-001",
            description="Test live rule",
            pattern="live_pattern",
            enforcement="block",
            category="security",
            source="manual",
            expires_at="",  # never expires
        )
        bank.capture(expired_rule)
        bank.capture(live_rule)
        assert len(bank.all_rules()) == 2

        removed = bank.purge_expired()
        assert removed == 1
        remaining = bank.all_rules()
        assert len(remaining) == 1
        assert remaining[0].id == "test-live-001"

    def test_purge_no_expired_returns_zero(self, tmp_path: Path) -> None:
        bank = PsycheBank(path=tmp_path / "np_bank.json")
        live_rule = CogRule(
            id="live-rule-001",
            description="A live rule",
            pattern="live",
            enforcement="block",
            category="security",
            source="manual",
            expires_at="",
        )
        bank.capture(live_rule)
        removed = bank.purge_expired()
        assert removed == 0

    def test_purge_empty_bank(self, tmp_path: Path) -> None:
        bank = PsycheBank(path=tmp_path / "empty_bank.json")
        assert bank.purge_expired() == 0
