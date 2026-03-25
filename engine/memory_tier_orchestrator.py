import time
import logging
from typing import Any, Dict, List, Optional
from engine.kv_store import get_kv_store
from engine.vector_store import get_vector_store
from engine.firestore_memory import ColdMemoryFirestore
from engine.buddy_memory import BuddyMemoryStore, BuddyMemoryEntry
from engine.jit_booster import JITBooster

logger = logging.getLogger(__name__)

class MemoryTierOrchestrator:
    """
    Orchestrates the flow of data across memory tiers:
    Hot (KV/Session) -> Warm (Vector/Buddy) -> Cold (Firestore).
    """
    def __init__(self):
        self.kv = get_kv_store()
        self.vector = get_vector_store()
        self.cold = ColdMemoryFirestore()
        self.buddy = BuddyMemoryStore()
        self.booster = JITBooster()

    async def recursive_summarize(self, session_id: str) -> Optional[BuddyMemoryEntry]:
        """
        Transitions a Hot Session into Warm Memory by summarizing and vectorizing.
        """
        logger.info(f"MemoryTier: Starting recursive summarization for {session_id}")
        
        # 1. Hot -> Warm (Buddy Summary)
        # Note: BuddyMemoryStore.save_session normally handles this 
        # but we add an extra layer of semantic vectorization here.
        entry = self.buddy.recent(limit=1) # Assume latest for demo or pass session
        if not entry or entry[0].session_id != session_id:
            logger.warning(f"MemoryTier: Session {session_id} not found in Buddy Store.")
            return None
        
        entry = entry[0]
        
        # 2. Warm (Vector Store)
        # We index the summary for semantic search
        self.vector.add(
            doc_id=f"summary_{session_id}",
            text=entry.summary,
            metadata={
                "type": "session_summary",
                "topics": entry.key_topics,
                "ts": entry.last_turn_at
            }
        )
        
        # 3. Warm -> Cold (Fact Distillation)
        await self.distill_facts(entry)
        
        return entry

    async def distill_facts(self, entry: BuddyMemoryEntry):
        """
        Extracts atomic facts from a summary and commits them to Tier 3 Cold Memory.
        """
        prompt = (
            f"Extract up to 3 atomic, permanent facts from this conversation summary:\n"
            f"'{entry.summary}'\n\n"
            f"Return a JSON list of strings. Do not include duplicates or vague statements."
        )
        
        try:
            # Attempt LLM extraction via JITBooster
            facts = []
            import engine.jit_booster as _jib
            from engine.config import GEMINI_MODEL
            
            if _jib._gemini_client:
                resp = _jib._gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                if resp.text:
                    import json
                    import re
                    # Simple extraction from potential markdown
                    match = re.search(r"\[.*\]", resp.text, re.DOTALL)
                    if match:
                        facts = json.loads(match.group(0))
            
            for i, fact in enumerate(facts):
                fact_id = f"fact_{entry.session_id}_{i}"
                success = self.cold.store_fact(fact_id, {
                    "fact": fact,
                    "source_session": entry.session_id,
                    "confidence": 0.95,
                    "ts": entry.last_turn_at
                })
                if success:
                    logger.info(f"MemoryTier: Distilled fact to Cold Memory: {fact}")
                    
        except Exception as e:
            logger.error(f"MemoryTier: Fact distillation failed: {e}")

_orchestrator = None
def get_memory_orchestrator() -> MemoryTierOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MemoryTierOrchestrator()
    return _orchestrator
