# 6W_STAMP
# WHO: TooLoo V4.5 (Autonomous Planner)
# WHAT: MODULE_NORTH_STAR_SYNTHESIZER | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/north_star_synthesizer.py
# WHEN: 2026-04-03T14:20:00.000000
# WHY: Rule 3: Native RAG Leveraged AI (Strategic Awareness)
# HOW: LLM-Based Retrospective + Predictive Roadmap Generation
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, planning, lmm, autonomy
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional

from tooloo_v4_hub.kernel.cognitive.north_star import get_north_star, NorthStarState
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.organs.memory_organ.sqlite_persistence import ChatRepository
from tooloo_v4_hub.kernel.governance.living_map import get_living_map

logger = logging.getLogger("NorthStarSynthesizer")

class NorthStarSynthesizer:
    """
    Strategic Cognitive Layer that updates the North Star.
    Analyzes the 'Story So Far' to architect the 'Path Ahead'.
    """
    def __init__(self):
        self.repo = ChatRepository()
        self.navigator = get_north_star()

    async def synthesize_state(self, history_limit: int = 15) -> NorthStarState:
        """Rule 16: Evaluates the delta between current state and user intent."""
        logger.info("North Star: Initiating Strategic Synthesis...")

        # 1. Gather Context
        history = self.repo.get_history(limit=history_limit)
        living_map = get_living_map()
        codebase_summary = f"Nodes: {len(living_map.nodes)} | Registry: {living_map.manifest_path}"
        
        history_text = "\n".join([f"{m.role.upper()}: {m.content[:200]}" for m in history])
        current_state = self.navigator.state

        # 2. Architect the Prompt
        prompt = f"""
        CURRENT_NORTH_STAR:
        - Macro Goal: {current_state.macro_goal}
        - Current Focus: {current_state.current_focus}
        - Micro Goals: {current_state.micro_goals}
        
        HISTORY_LOGS:
        {history_text}
        
        CODEBASE_STATE:
        {codebase_summary}
        
        MISSION:
        Analyze the recent interaction trajectory. Identify if the Macro Goal should shift, 
        what the immediate 'Current Focus' is, and update the queue of 'Micro Goals'.
        Move any completed items to 'Completed Milestones'.
        
        OUTPUT_FORMAT (STRICT JSON):
        {{
            "macro_goal": "str",
            "current_focus": "str",
            "micro_goals": ["str", ...],
            "completed_milestones": ["str", ...]
        }}
        """

        instruction = "You are the Sovereign Planner. Output ONLY valid JSON. Be strategic, brutal, and concise."

        # 3. LLM Invoke (Flash Tier)
        llm = get_llm_client()
        try:
            raw_response = await llm.generate_thought(prompt, instruction, model_tier="flash")
            # Clean JSON if wrapped in code blocks
            clean_json = raw_response.split("```json")[-1].split("```")[0].strip()
            if not clean_json.startswith("{"): clean_json = raw_response.strip()
            
            new_data = json.loads(clean_json)
            
            # 4. Update Navigator
            self.navigator.update(
                macro_goal=new_data.get("macro_goal"),
                current_focus=new_data.get("current_focus"),
                micro_goals=new_data.get("micro_goals"),
                completed_milestones=new_data.get("completed_milestones")
            )
            
            logger.info(f"North Star: Shift Detected -> Focus: {new_data.get('current_focus')}")
            return self.navigator.state
        except Exception as e:
            logger.error(f"North Star Synthesis Fault: {e}")
            return self.navigator.state

_synthesizer: Optional[NorthStarSynthesizer] = None

def get_north_star_synthesizer() -> NorthStarSynthesizer:
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = NorthStarSynthesizer()
    return _synthesizer
