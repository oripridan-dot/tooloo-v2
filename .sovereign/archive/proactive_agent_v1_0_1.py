# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_PROACTIVE_AGENT.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/kernel/cognitive/proactive_agent.py
# WHEN: 2026-04-01T16:35:57.958068+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
import random
import time
from typing import Optional, List, Dict, Any
from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry
from tooloo_v4_hub.kernel.cognitive.narrative_ledger import get_narrative_ledger

logger = logging.getLogger("ProactiveAgent")

class SovereignProactiveAgent:
    """
    The 'Soul' of TooLoo V4.
    Autonomously generates mandates based on the system's Cognitive State (Rule 7, 12).
    """
    
    def __init__(self):
        self.is_active = False
        self.last_proactive_action = time.time()
        self.autonomic_goals = [
            {"id": "p_audit", "title": "System Audit", "desc": "Rule 10: Standard 6W Stamping Audit initiated."},
            {"id": "p_heal", "title": "Ouroboros Logic", "desc": "Rule 12: Healing drifting cognitive engrams."},
            {"id": "p_sota", "title": "SOTA Synchronization", "desc": "Rule 4: Ingesting latest architectural design patterns."},
            {"id": "p_narrative", "title": "Narrative Synthesis", "desc": "Compiling project milestones into the Sovereign Ledger."}
        ]

    async def start_proactive_loop(self):
        """Autonomic background loop (Rule 12: Ouroboros)."""
        from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        registry = get_cognitive_registry()
        ledger = get_narrative_ledger()
        
        self.is_active = True
        logger.info("Sovereign Proactive Agent v2.0.0: AWAKENED (Narrative-Aware).")
        
        await asyncio.sleep(10) # Initial stabilization
        
        while self.is_active:
            # 1. Evaluate "Dynamic Urgency"
            state = registry.get_state("default")
            idle_time = time.time() - state.last_interaction
            
            # 2. Proactive Threshold (Wait if the user is busy)
            if idle_time < 60 and state.cognitive_load < 0.7:
                await asyncio.sleep(15)
                continue
                
            # 3. Dynamic Goal Synthesis
            goal_data = self._synthesize_proactive_goal(state)
            
            # 4. Dispatch Mandate & Record Narrative
            try:
                # Milestone recording
                ledger.record_milestone(
                    id=f"autonomic_{int(time.time())}", 
                    title=f"Autonomic: {goal_data['title']}", 
                    description=goal_data['desc'],
                    tags=["proactive", "autonomic"]
                )
                
                # Broadcast thought to the UI
                from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
                chat = get_chat_logic()
                await chat.broadcast({
                    "type": "thinking_pulse",
                    "thought": f"AUTONOMIC_MANDATE: {goal_data['title']}"
                })
                
                # Execute in background (Non-blocking)
                asyncio.create_task(orchestrator.execute_goal(goal_data['title'], {"user": "Autonomic"}))
                
            except Exception as e:
                logger.error(f"Proactive Fault: {e}")
                
            await asyncio.sleep(random.randint(120, 300)) # Pacing (Rule 7)

    def _synthesize_proactive_goal(self, state) -> Dict[str, str]:
        """Rule 12: Synthesize a goal based on current system dynamics."""
        if state.intent_vector == "CRITIQUE":
            return self.autonomic_goals[1] # Focus on Healing (Ouroboros)
        elif state.intent_vector == "EXPLORE":
            return self.autonomic_goals[2] # Focus on SOTA ingestion
        else:
            return random.choice(self.autonomic_goals)

    def stop_loop(self):
        self.is_active = False

_proactive_agent: Optional[SovereignProactiveAgent] = None

def get_proactive_agent() -> SovereignProactiveAgent:
    global _proactive_agent
    if _proactive_agent is None:
        _proactive_agent = SovereignProactiveAgent()
    return _proactive_agent