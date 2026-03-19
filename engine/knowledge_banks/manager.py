"""
engine/knowledge_banks/manager.py — BankManager: unified gateway to all knowledge banks.

Aggregates DesignBank, CodeBank, AIBank, and BridgeBank.
Provides:
  - Composite query across all banks
  - Intent-mapped signal selection (for JITBooster integration)
  - Health / summary dashboard
  - Ingestion endpoint for new SOTA data
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.knowledge_banks.base import KnowledgeBank, KnowledgeEntry
from engine.knowledge_banks.design_bank import DesignBank
from engine.knowledge_banks.code_bank import CodeBank
from engine.knowledge_banks.ai_bank import AIBank
from engine.knowledge_banks.bridge_bank import BridgeBank

# Intent → bank domains that are most relevant
_INTENT_TO_DOMAINS: dict[str, list[tuple[str, str]]] = {
    "BUILD": [
        ("code", "architecture"),
        ("code", "api_design"),
        ("code", "ci_cd"),
        ("code", "developer_experience"),
    ],
    "DEBUG": [
        ("code", "observability"),
        ("code", "testing"),
        ("code", "runtime_safety"),
        ("ai", "evaluation"),
    ],
    "AUDIT": [
        ("code", "security"),
        ("ai", "safety_alignment"),
        ("code", "observability"),
    ],
    "DESIGN": [
        ("design", "gestalt"),
        ("design", "layout"),
        ("design", "color"),
        ("design", "typography"),
        ("design", "interaction_patterns"),
        ("design", "accessibility"),
        ("design", "design_systems"),
    ],
    "EXPLAIN": [
        ("bridge", "communication_theory"),
        ("bridge", "conversational_design"),
        ("bridge", "ai_literacy"),
        ("ai", "foundations"),
    ],
    "IDEATE": [
        ("bridge", "gap_repair_patterns"),
        ("ai", "agents"),
        ("code", "architecture"),
        ("design", "ux_research"),
    ],
    "SPAWN_REPO": [
        ("code", "ci_cd"),
        ("code", "security"),
        ("code", "developer_experience"),
    ],
    "BLOCKED": [
        ("bridge", "trust_calibration"),
        ("bridge", "interaction_failures"),
    ],
    "UX_EVAL": [
        ("design", "gestalt"),
        ("design", "accessibility"),
        ("design", "interaction_patterns"),
        ("design", "visual_hierarchy"),
        ("bridge", "conversational_design"),
    ],
    "BUDDY": [
        ("bridge", "buddy_persona"),
        ("bridge", "gap_repair_patterns"),
        ("bridge", "emotional_intelligence"),
        ("bridge", "trust_calibration"),
        ("ai", "agents"),
    ],
}


class BankManager:
    """
    Unified read/write gateway to all TooLoo knowledge banks.

    All banks are instantiated lazily on first access. Thread-safe
    because each bank manages its own lock.
    """

    def __init__(self, bank_root: Path | None = None) -> None:
        root = bank_root or (
            Path(__file__).resolve().parents[3] / "psyche_bank")
        self._design = DesignBank(root / "design.cog.json")
        self._code = CodeBank(root / "code.cog.json")
        self._ai = AIBank(root / "ai.cog.json")
        self._bridge = BridgeBank(root / "bridge.cog.json")
        self._banks: dict[str, KnowledgeBank] = {
            "design": self._design,
            "code": self._code,
            "ai": self._ai,
            "bridge": self._bridge,
        }

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_bank(self, bank_id: str) -> KnowledgeBank | None:
        return self._banks.get(bank_id)

    def all_banks(self) -> dict[str, KnowledgeBank]:
        return dict(self._banks)

    def query(self, topic: str, context: str = "", n: int = 5) -> list[KnowledgeEntry]:
        """Alias for query_all — returns top-N entries across all banks."""
        return self.query_all(topic, context, n_per_bank=max(1, n))

    def query_all(self, topic: str, context: str = "", n_per_bank: int = 3) -> list[KnowledgeEntry]:
        """Query all banks and return the top entries across all domains."""
        results: list[KnowledgeEntry] = []
        for bank in self._banks.values():
            results.extend(bank.query(topic, context, n=n_per_bank))
        results.sort(key=lambda e: e.relevance_weight, reverse=True)
        return results

    def signals_for_intent(self, intent: str, n: int = 5) -> list[str]:
        """
        Return the highest-weight SOTA signals relevant to the given intent.
        Used by JITBooster to augment confidence with structured bank data.
        """
        domain_mappings = _INTENT_TO_DOMAINS.get(
            intent, _INTENT_TO_DOMAINS["EXPLAIN"])
        signals: list[tuple[float, str]] = []

        for bank_id, domain in domain_mappings:
            bank = self._banks.get(bank_id)
            if not bank:
                continue
            entries = bank.query(domain, intent, n=3)
            for e in entries:
                signals.append((e.relevance_weight, e.signal()))

        signals.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in signals[:n]]

    def buddy_context(self, intent: str, user_text: str) -> str:
        """
        Build a compact context block for Buddy's LLM prompt.
        Injects top signals from Bridge + intent-relevant banks.
        """
        bridge_signals = self._bridge.get_signals(n=3)
        intent_signals = self.signals_for_intent(intent, n=3)
        all_signals = list(dict.fromkeys(bridge_signals + intent_signals))[:5]
        if not all_signals:
            return ""
        lines = ["[Knowledge Bank Context]"] + [f"• {s}" for s in all_signals]
        return "\n".join(lines)

    def ingest(self, entry: KnowledgeEntry, bank_id: str) -> bool:
        """
        Add a new entry to the named bank.
        Returns True if newly added, False if duplicate.
        """
        bank = self._banks.get(bank_id)
        if not bank:
            raise ValueError(
                f"Unknown bank_id: {bank_id!r}. Valid: {list(self._banks)}")
        return bank.store(entry)

    def health(self) -> dict[str, Any]:
        """Return a health summary for all banks."""
        return {
            "banks": {
                bid: {
                    "name": bank.bank_name,
                    "entry_count": len(bank.all_entries()),
                    "domains": bank.domain_summary(),
                }
                for bid, bank in self._banks.items()
            },
            "total_entries": sum(len(b.all_entries()) for b in self._banks.values()),
        }

    def dashboard(self) -> dict[str, Any]:
        """Full dashboard dict for the UI panel."""
        return {
            "banks": {
                bank_id: bank.to_dict()
                for bank_id, bank in self._banks.items()
            }
        }
