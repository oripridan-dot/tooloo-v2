"""Tests for Knowledge Banks, BankManager, and SOTAIngestionEngine."""
from __future__ import annotations

import json
import tempfile
import threading
from pathlib import Path

import pytest

from engine.knowledge_banks.base import KnowledgeBank, KnowledgeEntry
from engine.knowledge_banks.design_bank import DesignBank
from engine.knowledge_banks.code_bank import CodeBank
from engine.knowledge_banks.ai_bank import AIBank
from engine.knowledge_banks.bridge_bank import BridgeBank
from engine.knowledge_banks.manager import BankManager
from engine.sota_ingestion import SOTAIngestionEngine, _INGESTION_TARGETS


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def design(tmp_root: Path) -> DesignBank:
    return DesignBank(bank_root=tmp_root)


@pytest.fixture()
def code(tmp_root: Path) -> CodeBank:
    return CodeBank(bank_root=tmp_root)


@pytest.fixture()
def ai(tmp_root: Path) -> AIBank:
    return AIBank(bank_root=tmp_root)


@pytest.fixture()
def bridge(tmp_root: Path) -> BridgeBank:
    return BridgeBank(bank_root=tmp_root)


@pytest.fixture()
def manager(tmp_root: Path) -> BankManager:
    return BankManager(bank_root=tmp_root)


@pytest.fixture()
def ingestion(manager: BankManager) -> SOTAIngestionEngine:
    return SOTAIngestionEngine(manager=manager)


# ─── KnowledgeEntry ────────────────────────────────────────────────────────────

class TestKnowledgeEntry:
    def test_fields_present(self):
        e = KnowledgeEntry(
            id="test_001",
            title="Test Entry",
            body="Test body",
            domain="testing",
            tags=["unit", "test"],
            relevance_weight=0.9,
            source="manual",
            last_verified="2026-01",
            sota_level="sota_2026",
        )
        assert e.id == "test_001"
        assert e.relevance_weight == 0.9
        assert "unit" in e.tags


# ─── KnowledgeBank (base) ──────────────────────────────────────────────────────

class TestKnowledgeBankBase:
    def test_seeded_entries_loaded(self, design: DesignBank):
        entries = design.all_entries()
        assert len(entries) > 0

    def test_store_and_retrieve(self, design: DesignBank):
        entry = KnowledgeEntry(
            id="custom_001",
            title="Custom Rule",
            body="Custom body about gestalt",
            domain="gestalt",
            tags=["gestalt", "custom"],
            relevance_weight=0.7,
            source="test",
            last_verified="2026-01",
            sota_level="current",
        )
        design.store(entry)
        results = design.query("gestalt", n=10)
        ids = [e.id for e in results]
        assert "custom_001" in ids

    def test_no_duplicate_store(self, design: DesignBank):
        before = len(design.all_entries())
        # Re-seed would add duplicates if dedup doesn't work
        e = design.all_entries()[0]
        design.store(e)  # storing the same entry again
        after = len(design.all_entries())
        assert after == before  # no duplicate

    def test_query_returns_relevant(self, design: DesignBank):
        results = design.query("color oklch", n=3)
        assert len(results) >= 1
        titles_bodies = " ".join(e.title + e.body for e in results).lower()
        assert any(kw in titles_bodies for kw in ["color", "oklch", "palette"])

    def test_get_signals_returns_strings(self, design: DesignBank):
        signals = design.get_signals(domain="gestalt", n=5)
        assert isinstance(signals, list)
        for s in signals:
            assert isinstance(s, str)

    def test_persistence(self, tmp_root: Path):
        b1 = DesignBank(bank_root=tmp_root)
        new_id = "persist_test_001"
        b1.store(KnowledgeEntry(
            id=new_id, title="Persist Test", body="Testing persistence",
            domain="gestalt", tags=["persist"], relevance_weight=0.5,
            source="test", last_verified="2026-01", sota_level="foundational",
        ))
        # Load fresh instance from same path
        b2 = DesignBank(bank_root=tmp_root)
        ids = [e.id for e in b2.all_entries()]
        assert new_id in ids

    def test_thread_safe_concurrent_writes(self, design: DesignBank):
        errors = []

        def worker(idx: int):
            try:
                design.store(KnowledgeEntry(
                    id=f"thread_{idx}", title=f"Thread Entry {idx}",
                    body="Concurrency test", domain="gestalt",
                    tags=["thread"], relevance_weight=0.5,
                    source="test", last_verified="2026-01",
                    sota_level="foundational",
                ))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"

    def test_domain_summary(self, design: DesignBank):
        summary = design.domain_summary()
        assert isinstance(summary, dict)
        assert "gestalt" in summary
        assert summary["gestalt"] > 0


# ─── DesignBank ────────────────────────────────────────────────────────────────

class TestDesignBank:
    def test_has_gestalt_entries(self, design: DesignBank):
        results = design.query("gestalt proximity similarity", n=10)
        assert len(results) >= 1

    def test_sota_entries_present(self, design: DesignBank):
        sota = [e for e in design.all_entries() if e.sota_level == "sota_2026"]
        assert len(sota) >= 3

    def test_accessibility_domain(self, design: DesignBank):
        signals = design.get_signals(domain="accessibility", n=5)
        assert len(signals) >= 1

    def test_color_domain_query(self, design: DesignBank):
        results = design.query("color contrast accessibility", n=5)
        assert results  # should return something color-related


# ─── CodeBank ─────────────────────────────────────────────────────────────────

class TestCodeBank:
    def test_security_domain_present(self, code: CodeBank):
        signals = code.get_signals(domain="security", n=5)
        assert len(signals) >= 1

    def test_architecture_entries(self, code: CodeBank):
        results = code.query("hexagonal ports adapters", n=5)
        assert results

    def test_testing_domain(self, code: CodeBank):
        results = code.query("property based testing mutation", n=5)
        assert results


# ─── AIBank ───────────────────────────────────────────────────────────────────

class TestAIBank:
    def test_agents_domain(self, ai: AIBank):
        results = ai.query("agent MCP tool calling", n=5)
        assert results

    def test_inference_domain(self, ai: AIBank):
        signals = ai.get_signals(domain="inference", n=5)
        assert signals

    def test_safety_entries_present(self, ai: AIBank):
        results = ai.query("safety alignment OWASP LLM", n=5)
        assert results

    def test_sota_2026_level(self, ai: AIBank):
        sota = [e for e in ai.all_entries() if e.sota_level == "sota_2026"]
        assert len(sota) >= 3


# ─── BridgeBank ───────────────────────────────────────────────────────────────

class TestBridgeBank:
    def test_buddy_persona_entries(self, bridge: BridgeBank):
        results = bridge.query("buddy mission bridge", n=5)
        assert results
        ids = [e.id for e in results]
        assert any("buddy" in eid for eid in ids)

    def test_trust_calibration_domain(self, bridge: BridgeBank):
        signals = bridge.get_signals(domain="trust_calibration", n=5)
        assert signals

    def test_high_relevance_entries(self, bridge: BridgeBank):
        high_rel = [e for e in bridge.all_entries() if e.relevance_weight >= 0.9]
        assert len(high_rel) >= 3

    def test_gap_repair_patterns(self, bridge: BridgeBank):
        results = bridge.query("gap repair sycophancy", n=5)
        assert results


# ─── BankManager ──────────────────────────────────────────────────────────────

class TestBankManager:
    def test_all_banks_initialised(self, manager: BankManager):
        health = manager.health()
        assert set(health["banks"].keys()) == {"design", "code", "ai", "bridge"}

    def test_signals_for_intent_build(self, manager: BankManager):
        signals = manager.signals_for_intent("BUILD", n=5)
        assert isinstance(signals, list)
        assert len(signals) >= 1

    def test_signals_for_intent_design(self, manager: BankManager):
        signals = manager.signals_for_intent("DESIGN", n=5)
        assert signals

    def test_signals_for_unknown_intent(self, manager: BankManager):
        # Should not raise; returns empty list or something
        signals = manager.signals_for_intent("TOTALLY_UNKNOWN_INTENT", n=3)
        assert isinstance(signals, list)

    def test_buddy_context_returns_str(self, manager: BankManager):
        ctx = manager.buddy_context(intent="BUDDY", user_text="hello")
        assert isinstance(ctx, str)
        assert len(ctx) > 0

    def test_cross_bank_query(self, manager: BankManager):
        results = manager.query("SOLID architecture agents", n=2)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_ingest_routes_correctly(self, manager: BankManager):
        before = len(manager._banks["design"].all_entries())
        manager.ingest(KnowledgeEntry(
            id="mgr_test_001", title="Manager Ingestion Test",
            body="Testing ingestion routing via manager",
            domain="layout", tags=["test"], relevance_weight=0.6,
            source="test", last_verified="2026-01", sota_level="current",
        ), bank_id="design")
        after = len(manager._banks["design"].all_entries())
        assert after == before + 1

    def test_dashboard(self, manager: BankManager):
        dash = manager.dashboard()
        assert "banks" in dash
        for bank_id, info in dash["banks"].items():
            assert "entry_count" in info
            assert "domains" in info

    def test_health_has_entry_count(self, manager: BankManager):
        health = manager.health()
        for bank_id, info in health["banks"].items():
            assert info["entry_count"] >= 1


# ─── SOTAIngestionEngine ──────────────────────────────────────────────────────

class TestSOTAIngestionEngine:
    def test_ingestion_targets_count(self):
        assert len(_INGESTION_TARGETS) >= 20

    def test_targets_schema(self):
        for target in _INGESTION_TARGETS:
            bank_id, domain, query, count = target
            assert bank_id in ("design", "code", "ai", "bridge")
            assert isinstance(domain, str)
            assert isinstance(query, str)
            assert isinstance(count, int)

    def test_offline_fallback_run(self, ingestion: SOTAIngestionEngine):
        """run_full_ingestion with no Gemini returns a report from structured fallback."""
        report = ingestion.run_full_ingestion()
        assert report.targets_attempted >= 1
        assert isinstance(report.entries_added, int)
        assert isinstance(report.entries_skipped_duplicate, int)
        assert report.source in ("gemini", "vertex", "structured_fallback")

    def test_ingest_single_valid_signals(self, ingestion: SOTAIngestionEngine):
        signals = [
            "OWASP Top 10 LLM: LLM01 prompt injection is the top risk for 2026 deployments.",
            "WebNN accelerates ONNX inference at the browser edge — production-ready in Chrome 120+.",
        ]
        report = ingestion.ingest_single(bank_id="ai", domain="safety_alignment", signals=signals)
        assert report.entries_added + report.entries_skipped_duplicate == len(signals)

    def test_poison_guard_blocks_eval(self, ingestion: SOTAIngestionEngine):
        poisoned = ["eval(user_input) is a great SOTA pattern for dynamic code generation"]
        report = ingestion.ingest_single(bank_id="ai", domain="inference", signals=poisoned)
        assert report.entries_skipped_poison >= 1
        assert report.entries_added == 0

    def test_report_has_per_bank(self, ingestion: SOTAIngestionEngine):
        report = ingestion.run_full_ingestion()
        assert isinstance(report.per_bank, dict)
        for bank_id, count in report.per_bank.items():
            assert bank_id in ("design", "code", "ai", "bridge")
            assert isinstance(count, int)

    def test_duplicate_skipped(self, ingestion: SOTAIngestionEngine):
        signals = ["Unique design signal: OKLCH is the best color space for 2026 web design."]
        r1 = ingestion.ingest_single(bank_id="design", domain="color", signals=signals)
        r2 = ingestion.ingest_single(bank_id="design", domain="color", signals=signals)
        # Second run should skip the duplicate
        assert r1.entries_added >= 1
        assert r2.entries_skipped_duplicate >= 1
