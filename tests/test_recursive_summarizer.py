"""tests/test_recursive_summarizer.py — Coverage for RecursiveSummaryAgent.

Tests:
  - distill_pending: no pending entries (all distilled)
  - distill_pending: success path — mock LLM returns valid JSON facts
  - distill_pending: empty fact array returned by LLM
  - distill_pending: LLM error path returns status=error
  - distill_pending: facts with missing fields are skipped gracefully
  - distill_pending: batch_size limit is respected
  - distill_pending: entries marked as distilled after processing
  - HTTP POST /v2/memory/distill returns 200 + status field
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from fastapi.testclient import TestClient

from engine.buddy_memory import BuddyMemoryEntry
from engine.recursive_summarizer import RecursiveSummaryAgent


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_entry(session_id: str, distilled: bool = False) -> BuddyMemoryEntry:
    now = datetime.now(UTC)
    return BuddyMemoryEntry(
        session_id=session_id,
        summary=f"Worked on {session_id}",
        key_topics=["BUILD", "DEBUG"],
        emotional_arc=["neutral"],
        turn_count=5,
        created_at=now.isoformat(),
        last_turn_at=now.isoformat(),
        last_message_preview=f"last msg for {session_id}",
        distilled=distilled,
    )


def _make_agent(batch_size: int = 5) -> RecursiveSummaryAgent:
    """Create an agent with all external dependencies mocked."""
    agent = RecursiveSummaryAgent(batch_size=batch_size)
    agent.buddy_store = MagicMock()
    agent.psyche_bank = MagicMock()
    agent.garden = MagicMock()
    agent.cold_memory = MagicMock()
    return agent


# ── Unit tests ────────────────────────────────────────────────────────────────


class TestDistillPending:
    """Tests for RecursiveSummaryAgent.distill_pending()."""

    def test_no_pending_when_all_distilled(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = [
            _make_entry("s1", distilled=True),
            _make_entry("s2", distilled=True),
        ]
        result = agent.distill_pending()
        assert result["status"] == "no_pending"
        assert result["processed"] == 0
        assert result["facts_extracted"] == 0

    def test_no_pending_when_store_empty(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = []
        result = agent.distill_pending()
        assert result["status"] == "no_pending"

    def test_success_path_extracts_facts(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = [_make_entry("s1")]

        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        agent.garden.call.return_value = json.dumps([
            {"id": "user_prefers_python",
                "description": "User prefers Python.", "confidence": 0.9},
            {"id": "uses_fastapi", "description": "Project uses FastAPI.",
                "confidence": 0.95},
        ])
        agent.psyche_bank.capture.return_value = True

        result = agent.distill_pending()

        assert result["status"] == "success"
        assert result["processed"] == 1
        assert result["facts_extracted"] == 2
        agent.psyche_bank.capture.call_count == 2

    def test_entries_marked_distilled_after_processing(self) -> None:
        agent = _make_agent()
        entry = _make_entry("s1")
        assert entry.distilled is False
        agent.buddy_store.recent.return_value = [entry]

        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        agent.garden.call.return_value = json.dumps([
            {"id": "fact_1", "description": "A fact.", "confidence": 0.8}
        ])
        agent.psyche_bank.capture.return_value = True

        agent.distill_pending()

        # save_entry should be called with distilled=True
        call_args = agent.buddy_store.save_entry.call_args[0][0]
        assert call_args.distilled is True

    def test_empty_facts_array_returns_success_zero_extracted(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = [_make_entry("s1")]

        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        agent.garden.call.return_value = "[]"

        result = agent.distill_pending()
        assert result["status"] == "success"
        assert result["facts_extracted"] == 0

    def test_markdown_json_fence_stripped(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = [_make_entry("s1")]

        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        agent.garden.call.return_value = '```json\n[{"id": "f1", "description": "fact", "confidence": 0.9}]\n```'
        agent.psyche_bank.capture.return_value = True

        result = agent.distill_pending()
        assert result["status"] == "success"
        assert result["facts_extracted"] == 1

    def test_llm_error_returns_error_status(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = [_make_entry("s1")]
        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        agent.garden.call.side_effect = RuntimeError("LLM unreachable")

        result = agent.distill_pending()
        assert result["status"] == "error"
        assert "LLM unreachable" in result["error"]

    def test_batch_size_limits_processed_count(self) -> None:
        agent = _make_agent(batch_size=2)
        agent.buddy_store.recent.return_value = [
            _make_entry(f"s{i}") for i in range(10)
        ]

        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        # no facts extracted, just test batch limit
        agent.garden.call.return_value = "[]"

        result = agent.distill_pending()
        assert result["processed"] == 2  # batch_size=2

    def test_facts_with_missing_description_skipped(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = [_make_entry("s1")]

        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        agent.garden.call.return_value = json.dumps([
            {"id": "bad_fact", "description": "", "confidence": 0.5},  # empty desc
            {"id": "no_desc"},  # missing desc
            {"id": "good_fact", "description": "Valid fact here.", "confidence": 0.9},
        ])
        agent.psyche_bank.capture.return_value = True

        result = agent.distill_pending()
        # Only the good_fact should be counted; bad ones skipped
        assert result["facts_extracted"] == 1

    def test_cold_memory_called_for_each_fact(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = [_make_entry("s1")]

        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        agent.garden.call.return_value = json.dumps([
            {"id": "f1", "description": "Fact one.", "confidence": 0.9},
            {"id": "f2", "description": "Fact two.", "confidence": 0.8},
        ])
        agent.psyche_bank.capture.return_value = True

        agent.distill_pending()
        assert agent.cold_memory.store_fact.call_count == 2

    def test_non_dict_items_in_facts_skipped(self) -> None:
        agent = _make_agent()
        agent.buddy_store.recent.return_value = [_make_entry("s1")]

        agent.garden.get_tier_model.return_value = "gemini-2.5-flash"
        agent.garden.call.return_value = json.dumps([
            "not a dict",
            42,
            {"id": "real_fact", "description": "A real fact.", "confidence": 0.9},
        ])
        agent.psyche_bank.capture.return_value = True

        result = agent.distill_pending()
        assert result["facts_extracted"] == 1


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


@pytest.fixture(scope="class")
def api_client():
    from studio.api import app
    return TestClient(app)


class TestDistillEndpoint:
    """Integration tests for POST /v2/memory/distill."""

    def test_returns_200(self, api_client: TestClient) -> None:
        resp = api_client.post("/v2/memory/distill")
        assert resp.status_code == 200

    def test_response_has_status_field(self, api_client: TestClient) -> None:
        resp = api_client.post("/v2/memory/distill")
        data = resp.json()
        assert "status" in data

    def test_status_is_valid_value(self, api_client: TestClient) -> None:
        resp = api_client.post("/v2/memory/distill")
        data = resp.json()
        assert data["status"] in ("no_pending", "success", "error")

    def test_response_has_processed_field(self, api_client: TestClient) -> None:
        resp = api_client.post("/v2/memory/distill")
        data = resp.json()
        # offline/empty store → no_pending but processed key present
        assert "processed" in data
