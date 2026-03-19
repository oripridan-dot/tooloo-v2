"""
engine/knowledge_banks — Multi-domain SOTA knowledge bank system for TooLoo V2.

Each bank is a curated, always-updated foundation of SOTA knowledge in its domain.
All banks are seeded with peer-reviewed, production-verified knowledge and can be
enriched via live JIT web queries or structured signals.

Banks:
  DesignBank  — Gestalt, typography, color, layout, SOTA design systems (2026)
  CodeBank    — Architecture patterns, SOTA frameworks, security, testing, perf
  AIBank      — Model architectures, training, inference, agents, safety (2026)
  BridgeBank  — Human-AI gap: cognition, communication, trust, interaction

BankManager aggregates all banks and provides composite query/signal APIs.
"""
from engine.knowledge_banks.base import KnowledgeEntry, KnowledgeBank
from engine.knowledge_banks.design_bank import DesignBank
from engine.knowledge_banks.code_bank import CodeBank
from engine.knowledge_banks.ai_bank import AIBank
from engine.knowledge_banks.bridge_bank import BridgeBank
from engine.knowledge_banks.manager import BankManager

__all__ = [
    "KnowledgeEntry",
    "KnowledgeBank",
    "DesignBank",
    "CodeBank",
    "AIBank",
    "BridgeBank",
    "BankManager",
]
