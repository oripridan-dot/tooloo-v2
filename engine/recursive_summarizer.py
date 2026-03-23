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

from engine.buddy_memory import BuddyMemoryStore
from engine.psyche_bank import PsycheBank, CogRule
from engine.model_garden import get_garden
from engine.firestore_memory import ColdMemoryFirestore

logger = logging.getLogger(__name__)


class RecursiveSummaryAgent:
    """Agent that distills Hippocampus/Hot Memory into VectorDB/Warm Memory."""

    def __init__(self, batch_size: int = 5) -> None:
        self.buddy_store = BuddyMemoryStore()
        # Initialise PsycheBank pointing to a specific 'pure_facts' store
        # to separate it from the main forbidden_patterns bank, or use the global one.
        self.psyche_bank = PsycheBank()
        self.garden = get_garden()
        self.batch_size = batch_size
        self.cold_memory = ColdMemoryFirestore()

    def distill_pending(self) -> dict[str, Any]:
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
            "Rules:\n"
            "1. Extract concrete knowledge: technical stack, user preferences, API choices, or project goals.\n"
            "2. Ignore ephemeral chatter or immediate tool errors that are already resolved.\n"
            "3. Output a strictly valid JSON array of objects, where each object has:\n"
            "   - 'id': A short snake_case slug (e.g. 'user_prefers_rust')\n"
            "   - 'description': One-sentence factual summary\n"
            "   - 'confidence': float 0.0 to 1.0\n"
            "4. If no long-term facts are worth keeping, return an empty array [].\n\n"
            f"Hot Memory Batch:\n{json.dumps(payload, indent=2)}\n\n"
            "Return ONLY the JSON array."
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

            facts = json.loads(text.strip())

            added_count = 0
            for f in facts:
                if not isinstance(f, dict):
                    continue
                fid = str(f.get("id", "fact"))
                desc = str(f.get("description", ""))
                conf = float(f.get("confidence", 0.8))

                if not desc:
                    continue

                # Store in PsycheBank as category class 'pure_fact'
                rule = CogRule(
                    id=fid,
                    description=desc,
                    pattern=".*",  # Match-all or generic pattern for pure facts
                    enforcement="warn",
                    category="pure_fact",
                    source="recursive_summary_agent",
                    expires_at=""
                )
                if self.psyche_bank.capture(rule):
                    added_count += 1
                
                # Push the distilled fact up the hierarchy to GCP Cold Memory 
                self.cold_memory.store_fact(
                    fact_id=fid, 
                    payload={
                        "description": desc, 
                        "confidence": conf,
                        "distilled_at": "auto"
                    }
                )

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
