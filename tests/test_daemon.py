"""
tests/test_daemon.py — BackgroundDaemon unit tests.

Coverage:
  · BackgroundDaemon instantiation with mock broadcast
  · start() sets active=True and emits daemon_status:started event
  · stop() sets active=False and emits daemon_status:stopped event
  · _cycle() runs SelfImprovementEngine, broadcasts daemon_rt events
  · High-risk component gating: tribunal/psyche_bank/router proposals go to
    approval queue, not auto-applied
  · PsycheBank purge_expired() is called at the start of each _cycle
  · Proposal fields: id, component, suggestion, risk, roi, rationale, status
  · Awaiting-approval queue grows for high-risk proposals
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.daemon import BackgroundDaemon, _HIGH_RISK_COMPONENTS


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def broadcast_events() -> list[dict[str, Any]]:
    return []


@pytest.fixture()
def broadcast_fn(broadcast_events: list[dict[str, Any]]):
    def _fn(event: dict[str, Any]) -> None:
        broadcast_events.append(event)
    return _fn


@pytest.fixture()
def daemon(broadcast_fn) -> BackgroundDaemon:
    return BackgroundDaemon(broadcast_fn)


# ── Instantiation ─────────────────────────────────────────────────────────────

class TestBackgroundDaemonInit:
    def test_initial_state(self, daemon: BackgroundDaemon):
        assert daemon.active is False

    def test_has_si_engine(self, daemon: BackgroundDaemon):
        assert daemon.si_engine is not None

    def test_awaiting_approval_empty(self, daemon: BackgroundDaemon):
        assert daemon.awaiting_approval == []

    def test_high_risk_components_set(self):
        assert "tribunal" in _HIGH_RISK_COMPONENTS
        assert "psyche_bank" in _HIGH_RISK_COMPONENTS
        assert "router" in _HIGH_RISK_COMPONENTS


# ── start / stop ──────────────────────────────────────────────────────────────

class TestDaemonStartStop:
    def test_stop_sets_inactive(self, daemon: BackgroundDaemon, broadcast_events):
        daemon.stop()
        assert daemon.active is False
        stopped_events = [
            e for e in broadcast_events if e.get("status") == "stopped"]
        assert stopped_events

    @pytest.mark.asyncio
    async def test_start_sets_active_and_broadcasts(
        self, daemon: BackgroundDaemon, broadcast_events
    ):
        """start() must set active=True and broadcast daemon_status:started.

        We mock _cycle and asyncio.sleep to avoid real I/O and 60-second delays.
        """
        call_count = 0

        async def _fake_cycle():
            nonlocal call_count
            call_count += 1
            daemon.stop()  # stop after first cycle so the while-loop exits

        with patch.object(daemon, "_cycle", side_effect=_fake_cycle):
            with patch("engine.daemon.asyncio.sleep", new_callable=AsyncMock):
                await daemon.start()

        started_events = [
            e for e in broadcast_events if e.get("status") == "started"]
        assert started_events
        assert call_count >= 1


# ── _cycle behaviour ──────────────────────────────────────────────────────────

class TestDaemonCycle:
    def _make_mock_assessment(
        self,
        component: str,
        suggestions: list[str] | None = None,
    ) -> MagicMock:
        a = MagicMock()
        a.component = component
        a.suggestions = suggestions or [
            f"FIX 1: engine/{component}.py:10 — add safety check"
        ]
        return a

    def _make_mock_report(self, assessments) -> MagicMock:
        report = MagicMock()
        report.assessments = assessments
        return report

    @pytest.mark.asyncio
    async def test_cycle_broadcasts_initiating_message(
        self, daemon: BackgroundDaemon, broadcast_events
    ):
        mock_report = self._make_mock_report([])
        with patch.object(daemon.si_engine, "run", return_value=mock_report):
            with patch.object(daemon._bank, "purge_expired", return_value=0):
                await daemon._cycle()

        rt_events = [
            e for e in broadcast_events if e.get("type") == "daemon_rt"
        ]
        assert any("scan" in e.get("msg", "").lower() for e in rt_events)

    @pytest.mark.asyncio
    async def test_cycle_calls_purge_expired(
        self, daemon: BackgroundDaemon, broadcast_events
    ):
        mock_report = self._make_mock_report([])
        with patch.object(daemon.si_engine, "run", return_value=mock_report) as mock_run:
            with patch.object(daemon._bank, "purge_expired", return_value=2) as mock_purge:
                await daemon._cycle()
                mock_purge.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_fix_suggestions_skipped(
        self, daemon: BackgroundDaemon
    ):
        """Suggestions not matching the FIX N: file.py:line pattern are ignored."""
        a = self._make_mock_assessment("router", ["improve the keyword list"])
        mock_report = self._make_mock_report([a])
        with patch.object(daemon.si_engine, "run", return_value=mock_report):
            with patch.object(daemon._bank, "purge_expired", return_value=0):
                await daemon._cycle()
        assert daemon.awaiting_approval == []

    @pytest.mark.asyncio
    async def test_high_risk_proposal_goes_to_approval_queue(
        self, daemon: BackgroundDaemon
    ):
        """Proposals for high-risk components must land in awaiting_approval."""
        a = self._make_mock_assessment(
            "tribunal",
            ["FIX 1: engine/tribunal.py:45 — add BOLA detection regex"],
        )
        mock_report = self._make_mock_report([a])
        with patch.object(daemon.si_engine, "run", return_value=mock_report):
            with patch.object(daemon._bank, "purge_expired", return_value=0):
                await daemon._cycle()

        assert len(daemon.awaiting_approval) >= 1
        proposal = daemon.awaiting_approval[0]
        assert proposal["component"] == "tribunal"
        assert proposal["status"] == "awaiting_approval"

    @pytest.mark.asyncio
    async def test_proposal_has_required_fields(self, daemon: BackgroundDaemon):
        a = self._make_mock_assessment(
            "psalm_bank",
            ["FIX 1: engine/psalm_bank.py:10 — refactor rule storage"],
        )
        # psalm_bank is NOT in _HIGH_RISK_COMPONENTS so it won't be gated
        # Use a high-risk one to guarantee it enters the queue
        a2 = self._make_mock_assessment(
            "psyche_bank",
            ["FIX 1: engine/psyche_bank.py:30 — add dedupe index"],
        )
        mock_report = self._make_mock_report([a2])
        with patch.object(daemon.si_engine, "run", return_value=mock_report):
            with patch.object(daemon._bank, "purge_expired", return_value=0):
                await daemon._cycle()

        assert daemon.awaiting_approval
        p = daemon.awaiting_approval[0]
        for field in ("id", "component", "suggestion", "risk", "roi", "rationale", "status"):
            assert field in p, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_multiple_proposals_accumulate(self, daemon: BackgroundDaemon):
        assessments = [
            self._make_mock_assessment(
                "tribunal",
                [f"FIX {i}: engine/tribunal.py:{i*10} — tweak pattern {i}"],
            )
            for i in range(1, 4)
        ]
        mock_report = self._make_mock_report(assessments)
        with patch.object(daemon.si_engine, "run", return_value=mock_report):
            with patch.object(daemon._bank, "purge_expired", return_value=0):
                await daemon._cycle()

        assert len(daemon.awaiting_approval) == 3
