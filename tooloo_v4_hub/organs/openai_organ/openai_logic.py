# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MODULE_OPENAI_ORGAN_LOGIC | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/openai_organ/openai_logic.py
# WHEN: 2026-03-31T23:01:00.000000
# WHY: Rule 13 Federated SOTA Infrastructure (Enterprise Access)
# HOW: Psyche Bank Querying + O1 Reasoning Mapping
# TIER: T3:architectural-purity
# DOMAINS: openai, enterprise, sota, academy, reasoning
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from tooloo_v4_hub.organs.openai_organ.openai_client import get_openai_engine

logger = logging.getLogger("OpenAILogic")

class OpenAIEnterpriseLogic:
    """
    The SOTA Bridge for OpenAI Enterprise Knowledge.
    Manages the 'Content List' of Academy and Platform engrams.
    """

    def __init__(self):
        self.enterprise_groups = {
            "science": "https://academy.openai.com/public/collections/science-ai",
            "work": "https://academy.openai.com/public/collections/work-hub",
            "education": "https://academy.openai.com/public/collections/education-ai",
            "stories": "https://academy.openai.com/public/collections/stories-hub"
        }
        logger.info("OpenAI Enterprise Logic Awakened. SOTA Groups: 4.")

    async def query_enterprise_sota(self, group: str, query: str = "") -> Dict[str, Any]:
        """
        Rule 4: SOTA Injection.
        Retrieves bit-perfect engrams for a specific enterprise collection.
        """
        if group not in self.enterprise_groups:
            return {"status": "error", "message": f"Group '{group}' not in enterprise matrix."}
            
        logger.info(f"OpenAI Organ: Querying '{group}' for '{query}'...")
        
        # Accessing the Memory Organ via the Hub's logic
        from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic
        memory = await get_memory_logic()
        
        # Searching for OpenAI-tagged engrams
        all_engrams = await memory.list_engrams() # Simplified for this organ
        
        relevant = []
        for eid in all_engrams:
            if "openai" in eid or group in eid:
                engram = await memory.retrieve(eid)
                if query.lower() in str(engram).lower():
                    relevant.append(engram)
                    
        return {
            "status": "success",
            "group": group,
            "results_count": len(relevant),
            "engrams": relevant[:5] # Sticking to Top 5 for bandwidth
        }

    async def generate_sota_reasoning(self, prompt: str, model: str = "gpt-5.4", effort: str = "high") -> Dict[str, Any]:
        """
        Rule 4: Active SOTA Reasoning.
        Delegates to the Response Engine for GPT-5.4 execution (Rule 13).
        """
        engine = get_openai_engine()
        res = await engine.generate_thought(prompt, model=model, effort=effort)
        
        # Rule 10: Metadata Stamping
        if res["status"] == "success":
            logger.info(f"OpenAI: SOTA Pulse Generated. Model: {model}. Δ: 0.1")
            return {
                "status": "success",
                "content": res["content"],
                "reasoning": res["reasoning_summary"],
                "usage": res["usage"]
            }
        else:
            return {"status": "error", "message": res["message"]}

    def get_content_list(self) -> Dict[str, str]:
        """Exposes the on-demand SOTA mapping."""
        return self.enterprise_groups

_logic: Optional[OpenAIEnterpriseLogic] = None

def get_openai_logic() -> OpenAIEnterpriseLogic:
    global _logic
    if _logic is None:
        _logic = OpenAIEnterpriseLogic()
    return _logic
