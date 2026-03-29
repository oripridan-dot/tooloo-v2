# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.memory_tier_orchestrator.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/memory_tier_orchestrator.py — Unified Tiered Memory Architecture.

Manages the 3-tier memory system for Buddy:

  HOT  (in-process)  — Last 50 conversation turns, L1 BuddyCache
  WARM (vector DB)   — Semantically-indexed session summaries (VectorStore)
  COLD (knowledge)   — Distilled atomic facts (PsycheBank + Firestore)

Tier Transitions:
  HOT → WARM:  Session ends or reaches _MEMORY_SAVE_THRESHOLD turns
  WARM → COLD: Recursive summariser extracts facts from summaries
  COLD → retrieval: Semantic search retrieves relevant cold facts

Architecture note (4D Routing — Macro timeframe):
  This replaces the previous stub orchestrator with a unified pipeline
  that actually promotes memory across tiers. The key addition is the
  ``query()`` method which searches ACROSS all tiers — enabling Buddy
  to answer questions like "what were we working on last week?" from
  warm/cold memory.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from engine.buddy_memory import BuddyMemoryStore, BuddyMemoryEntry
from engine.vector_store import VectorStore, get_vector_store
from engine.firestore_memory import ColdMemoryFirestore

logger = logging.getLogger(__name__)


@dataclass
class MemorySearchResult:
    """A single result from cross-tier memory search."""
    tier: str                    # "hot", "warm", "cold"
    content: str                 # Summary or fact text
    score: float                 # Relevance score (0.0–1.0)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "content": self.content[:500],
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


class MemoryTierOrchestrator:
    """
    Orchestrates the flow of data across memory tiers:
    Hot (BuddyCache/Session) → Warm (VectorStore) → Cold (Firestore/PsycheBank).
    """

    # Promotion thresholds
    WARM_TO_COLD_AGE_DAYS = 7   # Warm entries older than 7 days → Cold
    MAX_WARM_ENTRIES = 500      # Cap warm tier to prevent unbounded growth

    def __init__(self) -> None:
        self.buddy_store = BuddyMemoryStore()
        from engine.system_memory import SystemMemoryStore
        self.system_store = SystemMemoryStore()
        self.vector_store = get_vector_store()
        self.cold = ColdMemoryFirestore()

    # ── Hot → Warm Promotion ──────────────────────────────────────────────

    async def promote_hot_to_warm(self, session_id: str, domain: str = "buddy") -> bool:
        """Summarise a finished session and index it in the vector store.

        Called when a conversation session ends or crosses the turn threshold,
        or when a daemon autonomous cycle completes (domain="system").
        """
        if domain == "buddy":
            entries = self.buddy_store.recent(limit=50)
            target = next((e for e in entries if e.session_id == session_id), None)
            
            if target is None:
                logger.warning(f"MemoryTier: Session {session_id} not found in Hot buddy memory.")
                return False

            doc_text = (
                f"Session summary (topics: {', '.join(target.key_topics)}):\n"
                f"{target.summary}\n"
                f"Last message: {target.last_message_preview}"
            )
            metadata = {
                "session_id": target.session_id,
                "created_at": target.created_at,
                "domain": "buddy",
                "tier": "warm",
            }
        elif domain == "system":
            sys_entries = self.system_store.recent(limit=50)
            sys_target = next((e for e in sys_entries if e.cycle_id == session_id), None)
            
            if sys_target is None:
                logger.warning(f"MemoryTier: Cycle {session_id} not found in Hot system memory.")
                return False

            doc_text = (
                f"Daemon Cycle {sys_target.domain} (success={sys_target.success}):\n"
                f"{sys_target.summary}\n"
                f"Learnings: {' '.join(sys_target.key_learnings)}\n"
                f"Modules touched: {', '.join(sys_target.modules_touched)}"
            )
            if getattr(sys_target, "is_anti_pattern", False):
                doc_text = f"[ANTI-PATTERN WARNING]\n" + doc_text

            metadata = {
                "cycle_id": sys_target.cycle_id,
                "created_at": sys_target.created_at,
                "domain": "system",
                "tier": "warm",
                "is_anti_pattern": getattr(sys_target, "is_anti_pattern", False),
                "git_sha": getattr(sys_target, "git_sha", "unknown"),
            }
            # mark it distilled in the store
            self.system_store.mark_distilled(session_id)
        else:
            return False

        was_added = await self.vector_store.add(
            doc_id=f"warm_{session_id}",
            text=doc_text,
            metadata=metadata,
        )

        if was_added:
            logger.info(f"MemoryTier: Promoted session {session_id} to Warm tier.")
        else:
            logger.info(f"MemoryTier: Session {session_id} already in Warm tier (near-dup).")

        return was_added

    # ── Warm → Cold Promotion ─────────────────────────────────────────────

    async def promote_warm_to_cold(self) -> dict[str, Any]:
        """Distill old warm entries into cold atomic facts.

        Runs the RecursiveSummaryAgent on entries older than WARM_TO_COLD_AGE_DAYS.
        """
        try:
            from engine.recursive_summarizer import RecursiveSummaryAgent
            agent = RecursiveSummaryAgent(batch_size=5)
            result = await agent.distill_pending()
            logger.info(f"MemoryTier: Warm→Cold promotion result: {result}")
            return result
        except Exception as e:
            logger.error(f"MemoryTier: Warm→Cold promotion failed: {e}")
            return {"status": "error", "error": str(e)}

    # ── Full Pipeline: Hot → Warm → Cold ──────────────────────────────────

    async def recursive_summarize(self, session_id: str, domain: str = "buddy") -> dict[str, Any]:
        """Run the full Hot → Warm → Cold pipeline for a session.

        1. Promote session from Hot to Warm (vectorise)
        2. Try promoting old Warm entries to Cold (distill facts)
        """
        result: dict[str, Any] = {"session_id": session_id, "domain": domain}

        # Step 1: Hot → Warm
        promoted = await self.promote_hot_to_warm(session_id, domain=domain)
        result["hot_to_warm"] = promoted

        # Step 2: Warm → Cold (only if we have enough warm entries)
        warm_size = self.vector_store.size()
        if warm_size > 10:  # Don't distill until we have meaningful volume
            cold_result = await self.promote_warm_to_cold()
            result["warm_to_cold"] = cold_result
        else:
            result["warm_to_cold"] = {"status": "skipped", "warm_size": warm_size}

        return result

    # ── Cross-Tier Query ──────────────────────────────────────────────────

    def query(self, query_text: str, top_k: int = 5, domain: str = "buddy") -> list[MemorySearchResult]:
        """Search across ALL memory tiers for relevant context.

        This searches Hot (recent records), Warm (vectorised summaries), and
        Cold (distilled facts) for the specified domain (buddy vs system).
        """
        results: list[MemorySearchResult] = []
        query_lower = query_text.lower()

        # Hot tier
        if domain == "buddy":
            hot_entries = self.buddy_store.recent(limit=20)
            for entry in hot_entries:
                topics = " ".join(entry.key_topics).lower()
                summary = entry.summary.lower()
                overlap = sum(1 for word in query_lower.split() if word in topics or word in summary)
                if overlap > 0:
                    score = min(1.0, overlap / max(len(query_lower.split()), 1))
                    results.append(MemorySearchResult(
                        tier="hot",
                        content=entry.summary,
                        score=score,
                        metadata={"session_id": entry.session_id, "topics": entry.key_topics},
                    ))
        elif domain == "system":
            hot_entries_sys = self.system_store.recent(limit=20)
            for sys_entry in hot_entries_sys:
                summary = sys_entry.summary.lower()
                learnings = " ".join(sys_entry.key_learnings).lower()
                overlap = sum(1 for word in query_lower.split() if word in summary or word in learnings)
                if overlap > 0:
                    score = min(1.0, overlap / max(len(query_lower.split()), 1))
                    results.append(MemorySearchResult(
                        tier="hot",
                        content=sys_entry.summary,
                        score=score,
                        metadata={
                            "cycle_id": sys_entry.cycle_id, 
                            "modules_touched": sys_entry.modules_touched,
                            "is_anti_pattern": getattr(sys_entry, "is_anti_pattern", False),
                            "git_sha": getattr(sys_entry, "git_sha", "unknown")
                        },
                    ))

        # Warm tier: semantic search via VectorStore (filter by domain)
        warm_results = self.vector_store.search(query_text, top_k=top_k * 2, threshold=0.1)
        for r in warm_results:
            r_domain = r.doc.metadata.get("domain", "buddy")
            if r_domain == domain:
                results.append(MemorySearchResult(
                    tier="warm",
                    content=r.doc.text,
                    score=r.score,
                    metadata=r.doc.metadata,
                ))

        # Cold tier: search distilled facts (mock collection name filtering for system vs buddy)
        # Note: self.cold might be pulling all facts regardless of domain right now.
        cold_facts = self.cold.query_facts(limit=200)
        for fact in cold_facts:
            f_domain = fact.get("domain", "buddy")
            if f_domain != domain:
                continue
            desc = str(fact.get("description", fact.get("fact", "")))
            if not desc:
                continue
            overlap = sum(1 for word in query_lower.split() if word in desc.lower())
            if overlap > 0:
                score = min(1.0, overlap / max(len(query_lower.split()), 1))
                results.append(MemorySearchResult(
                    tier="cold",
                    content=desc,
                    score=score * 0.8,
                    metadata=fact,
                ))

        # Sort by score descending and return top_k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return tier sizes and health."""
        return {
            "hot_buddy": {
                "entries": self.buddy_store.entry_count(),
                "tier": "in-process session summaries",
            },
            "hot_system": {
                "entries": self.system_store.entry_count(),
                "tier": "daemon cycle tracking & anti-patterns",
            },
            "warm": {
                "entries": self.vector_store.size(),
                "tier": "vectorised semantic memory (mixed domain)",
                "vocabulary_size": len(self.vector_store._idf),
            },
            "cold": {
                "entries": len(self.cold.query_facts(limit=10000)),
                "tier": "distilled atomic facts (mixed domain)",
                "backend": "firestore" if self.cold.enabled else "local-mock",
            },
        }


# ── Singleton ────────────────────────────────────────────────────────────────
_orchestrator: MemoryTierOrchestrator | None = None


def get_memory_orchestrator() -> MemoryTierOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MemoryTierOrchestrator()
    return _orchestrator
