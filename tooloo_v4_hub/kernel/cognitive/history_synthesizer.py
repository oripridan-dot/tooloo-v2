# 6W_STAMP
# WHO: TooLoo V4.5.0 (Collective Common Sense)
# WHAT: MODULE_HISTORY_SYNTHESIZER | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/history_synthesizer.py
# WHEN: 2026-04-03T13:20:00.000000
# WHY: Rule 9 Tiered Memory + Rule 16 Retrospective (Systemic Common Sense)
# HOW: Sequential Engram Aggregation + LLM Synthesis of "The Story So Far"
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, memory, synthesis, history
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional

from tooloo_v4_hub.organs.memory_organ.sqlite_persistence import ChatRepository
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client

logger = logging.getLogger("HistorySynthesizer")

class HistorySynthesizer:
    """
    Builds Buddy's "Collective Common Sense" by reviewing past sessions.
    Prevents Buddy from recurring in "Contextual Blindness" after restarts.
    """

    def __init__(self):
        self.repo = ChatRepository()
        self.common_sense_cache: Optional[str] = None

    async def synthesize_collective_state(self, limit: int = 20) -> str:
        """Rule 9: Aggregates recent chat history and identifies the long-term arc."""
        logger.info(f"Buddy: Synthesizing Collective Common Sense from last {limit} messages...")
        
        # 1. Retrieve History
        history = self.repo.get_history(limit=limit)
        if not history:
            return "No prior history detected. Current State: PROGENESIS."

        history_text = ""
        for msg in history:
            role = msg.role or "unknown"
            content = msg.content or ""
            history_text += f"{role.upper()}: {content[:200]}...\n"

        # 2. LLM Synthesis of "The Story So Far"
        llm = get_llm_client()
        prompt = f"""
        HISTORY_LOGS:
        {history_text}
        
        MISSION: Based on this history, synthesize the 'Collective Common Sense' for the system.
        What is the current project trajectory? What are the recurring themes, solved problems, and outstanding gaps?
        
        OUTPUT: A concise 2-3 paragraph summary of Buddy's situational awareness.
        """
        
        instruction = "You are the Collective Memory of Buddy. Synthesize the project arc with Brutal Honesty."
        
        try:
            summary = await llm.generate_thought(prompt, instruction, model_tier="flash")
            self.common_sense_cache = summary
            logger.info("Buddy: Collective Common Sense update COMPLETE.")
            return summary
        except Exception as e:
            logger.error(f"Synthesis Fault: {e}")
            return "History is present but synthesis failed. Operating on raw memory engrams."

    def get_current_sense(self) -> str:
        """Returns the last synthesized common sense or a default."""
        return self.common_sense_cache or "Collective Common Sense is initializing..."

_synthesizer = None

def get_history_synthesizer() -> HistorySynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = HistorySynthesizer()
    return _synthesizer
