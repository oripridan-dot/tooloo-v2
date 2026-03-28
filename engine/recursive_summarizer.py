# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.recursive_summarizer.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/recursive_summarizer.py — The Recursive Summary Agent for Tiered Memory.

This agent operates on the boundary between Hot Memory (Hippocampus / BuddyMemory)
and Warm Memory (PsycheBank / VectorStore).

It periodically distills recent conversation sessions into `pure facts` using a 
Tier 3 reasoning model, moving the extracted knowledge into the PsycheBank and
marking the Hot Memory entries as `distilled`.

By doing this, it prevents context window bloat and builds an ever-growing 
structured knowledge graph.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any

from pathlib import Path
from engine.buddy_memory import BuddyMemoryStore
from engine.psyche_bank import PsycheBank, CogRule
from engine.model_garden import get_garden
from engine.firestore_memory import ColdMemoryFirestore
from engine.vector_store import VectorStore

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CALIBRATION_PROOF_PATH = _REPO_ROOT / "psyche_bank" / "calibration_proof.json"

logger = logging.getLogger(__name__)


class RecursiveSummaryAgent:
    """Agent that distills Hippocampus/Hot Memory into VectorDB/Warm Memory."""

    def __init__(self, batch_size: int = 5) -> None:
        self.buddy_store = BuddyMemoryStore()
        self.psyche_bank = PsycheBank()
        self.garden = get_garden()
        self.batch_size = batch_size
        self.cold_memory = ColdMemoryFirestore()
        self.vector_store = VectorStore(dup_threshold=0.95)
        self.calibration_context = self._load_calibration_context()

    def _load_calibration_context(self) -> str:
        """Load the latest 16D calibration proof to guide distillation."""
        if not _CALIBRATION_PROOF_PATH.exists():
            return "No calibration data available."
        try:
            data = json.loads(_CALIBRATION_PROOF_PATH.read_text(encoding="utf-8"))
            metrics = data.get("system_metrics", {})
            summary = data.get("summary", "").split("\n\n")[0] # Get the first block
            return (
                f"SYSTEM CALIBRATION CONTEXT (Run {data.get('run_id')}):\n"
                f"- Overall Alignment: {metrics.get('alignment_after', 0.0):.4f}\n"
                f"- Mean 16D Gain: +{metrics.get('system_16d_gain', 0.0)*100:.2f}pp\n"
                f"- Critical Focus: {summary}\n"
            )
        except Exception as e:
            logger.warning(f"Failed to load calibration context: {e}")
            return "Error loading calibration data."

    async def distill_pending(self) -> dict[str, Any]:
        """Find non-distilled memory entries and extract pure facts."""
        all_entries = self.buddy_store.recent(limit=1000)
        pending = [e for e in all_entries if getattr(
            e, "distilled", False) is False]

        if not pending:
            return {"status": "no_pending", "processed": 0, "facts_extracted": 0}

        # Take up to batch_size
        batch = pending[:self.batch_size]

        # Prepare payload for LLM
        payload = [
            {
                "session_id": e.session_id,
                "summary": e.summary,
                "topics": e.key_topics,
                "emotions": e.emotional_arc
            }
            for e in batch
        ]

        prompt = (
            "You are the Recursive Summary Agent for the TooLoo V2 Cognitive OS.\n"
            "Your task is to analyze the following recent user conversation summaries (Hot Memory) "
            "and distill them into standalone 'pure facts' for long-term Warm Memory.\n\n"
            f"{self.calibration_context}\n\n"
            "Rules:\n"
            "1. Extract concrete knowledge: technical stack, user preferences, API choices, or project goals.\n"
            "2. Prioritize facts that address the 'Critical Focus' areas identified in the calibration context.\n"
            "3. Identify relationships: If fact A is a prerequisite or cause of fact B, include it.\n"
            "4. Output a strictly valid JSON object with two keys:\n"
            "   - 'facts': array of objects {id, description, confidence}\n"
            "   - 'relations': array of objects {source_id, target_id, relation_type}\n"
            "5. If no facts are worth keeping, return {'facts': [], 'relations': []}.\n\n"
            f"Hot Memory Batch:\n{json.dumps(payload, indent=2)}\n\n"
            "Return ONLY the JSON object."
        )

        model_id = self.garden.get_tier_model(tier=3, intent="DISTILL")
        try:
            response = self.garden.invoke(model_id, prompt)

            # Clean up potential markdown formatting
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]

            res_json = json.loads(text.strip())
            facts = res_json.get("facts", [])
            relations = res_json.get("relations", [])

            added_count = 0
            for f in facts:
                fid = str(f.get("id", "fact"))
                desc = str(f.get("description", ""))
                conf = float(f.get("confidence", 0.8))

                if not desc: continue

                # Vector-Symbolic Integrity Check
                if await self._fact_collides_with_warm_memory(desc):
                    continue

                rule = CogRule(
                    id=fid, description=desc, pattern=".*",
                    enforcement="warn", category="pure_fact",
                    source="recursive_summary_agent", expires_at=""
                )
                if self.psyche_bank.capture(rule):
                    added_count += 1
                
                self.cold_memory.store_fact(
                    fact_id=fid, 
                    payload={"description": desc, "confidence": conf, "distilled_at": "auto"}
                )

            # Process relationships
            for rel in relations:
                self.cold_memory.link_facts(
                    source_id=rel.get("source_id"),
                    target_id=rel.get("target_id"),
                    relation=rel.get("relation_type", "related_to")
                )

            # Also distill the raw summary into the warm vector store for semantic search
            for entry in batch:
                doc_text = (
                    f"Summary of a past session:\n"
                    f"Key Topics: {', '.join(entry.key_topics)}\n"
                    f"Summary: {entry.summary}\n"
                    f"Final User Message Snippet: {entry.last_message_preview}"
                )
                metadata = {
                    "session_id": entry.session_id,
                    "created_at": entry.created_at,
                    "last_turn_at": entry.last_turn_at,
                    "turn_count": entry.turn_count,
                }
                was_added = await self.vector_store.add(
                    doc_id=entry.session_id, text=doc_text, metadata=metadata
                )
                if was_added:
                    logger.info(f"Distilled summary for {entry.session_id} into warm vector store.")

            # Mark processed entries as distilled and save back
            for e in batch:
                e.distilled = True
                self.buddy_store.save_entry(e)

            return {
                "status": "success",
                "processed": len(batch),
                "facts_extracted": added_count
            }

        except Exception as e:
            logger.error(f"RecursiveSummaryAgent failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _fact_collides_with_warm_memory(self, description: str) -> bool:
        """Check if a new fact is semantically redundant via VectorStore search."""
        results = await self.vector_store.search(description, top_k=1)
        if not results:
            return False
        return results[0].score > 0.98

    async def migrate_adversarial_logs(self) -> dict[str, Any]:
        """Specialized one-time migration of hardening logs to Cold Memory."""
        log_path = _REPO_ROOT / "psyche_bank" / "adversarial_evolution_log.jsonl"
        if not log_path.exists():
            return {"status": "no_logs_found"}
        
        try:
            lines = log_path.read_text().splitlines()
            records = [json.loads(l) for l in lines]
            
            # Distill the latest state
            latest = records[-1]
            fact_id = f"hardening_calibration_{latest['epoch']}"
            desc = (
                f"Adversarial training completed epoch {latest['epoch']} with "
                f"Architectural_Foresight at {latest['weights_after']['Architectural_Foresight']:.4f}. "
                f"Stability detected at {latest.get('stability', 0.0):.4f}."
            )
            
            self.cold_memory.store_fact(fact_id, {
                "description": desc,
                "confidence": 1.0,
                "source": "manual_migration",
                "weights": latest['weights_after']
            })
            
            return {"status": "success", "migrated_epochs": len(records)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
