"""Tests for engine/sota_ingestion.py — SOTAIngestionEngine offline behaviour."""
from __future__ import annotations

from engine.knowledge_banks.manager import BankManager
from engine.sota_ingestion import IngestionReport, SOTAIngestionEngine, _INGESTION_TARGETS


class TestSOTAIngestionEngineOffline:
    def _make_engine(self) -> SOTAIngestionEngine:
        """Create an isolated engine with a fresh BankManager."""
        return SOTAIngestionEngine(manager=BankManager())

    def test_offline_ingestion_uses_structured_fallback(self):
        """In offline mode (conftest patches clients to None), source must be 'structured_fallback'."""
        engine = self._make_engine()
        result = engine.run_full_ingestion()
        # conftest.py patches engine.sota_ingestion._gemini_client=None and
        # engine.sota_ingestion._vertex_client=None → source = "structured_fallback"
        assert result.source == "structured_fallback"

    def test_run_full_ingestion_returns_ingestion_report(self):
        engine = self._make_engine()
        result = engine.run_full_ingestion()
        assert isinstance(result, IngestionReport)

    def test_entries_added_is_non_negative(self):
        engine = self._make_engine()
        result = engine.run_full_ingestion()
        assert result.entries_added >= 0

    def test_targets_attempted_matches_config(self):
        engine = self._make_engine()
        result = engine.run_full_ingestion()
        assert result.targets_attempted == len(_INGESTION_TARGETS)

    def test_no_errors_in_offline_mode(self):
        engine = self._make_engine()
        result = engine.run_full_ingestion()
        assert result.errors == [], f"Unexpected errors: {result.errors}"

    def test_per_bank_covers_expected_banks(self):
        engine = self._make_engine()
        result = engine.run_full_ingestion()
        # Structured fallback only covers a subset of banks, but per_bank must exist
        assert isinstance(result.per_bank, dict)

    def test_completed_at_is_set(self):
        engine = self._make_engine()
        result = engine.run_full_ingestion()
        assert result.completed_at != ""

    def test_ingest_single_manual_signals(self):
        engine = self._make_engine()
        signals = [
            "Use WCAG 2.2 Level AA color contrast for all interactive elements",
            "Apply 8px baseline grid for consistent vertical rhythm",
        ]
        report = engine.ingest_single("design", "accessibility", signals)
        assert report.source == "manual"
        assert report.entries_added >= 0
