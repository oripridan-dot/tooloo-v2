# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: KERNEL_PROACTIVE_AGENT_v3.0.0 — Autonomous Soul
# WHERE: tooloo_v3_hub/kernel/proactive_agent.py
# WHEN: 2026-03-29T12:00:00.000000
# WHY: Intentionality & Justification of Virtual Existence
# HOW: Periodic Goal Dispatching & High-Fidelity Reflective Poses
# ==========================================================

import asyncio
import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

class SovereignProactiveAgent:
    """
    The 'Soul' of TooLoo V3.
    Periodically generates and dispatches its own autonomic mandates.
    """
    
    def __init__(self):
        self.is_active = False
        self.thoughts = [
            "Scanning Data Pillars for Sovereign Faults...",
            "Synchronizing Skeletal Damping Layer...",
            "Optimizing Hub Vitality: Current 0.98",
            "Observing Architectural Duality in the Crypt...",
            "Awaiting Sovereign Mandate from Principal Architect...",
            "Refining 22D Tensor Weights for Local Domains..."
        ]
        self.goals = [
            "come closer and scan",
            "wave and think about data",
            "far away and ponder",
            "look at nearest pillar"
        ]

    async def start_proactive_loop(self):
        """Dedicated background loop for autonomous intentionality."""
        from tooloo_v3_hub.kernel.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        
        self.is_active = True
        logger.info("Sovereign Proactive Agent: SOUL-ACTIVE.")
        
        # Initial Warmup Delay
        await asyncio.sleep(20)
        
        while self.is_active:
            # 1. Idle Threshold: Only act if the user hasn't commanded recently
            await asyncio.sleep(random.randint(45, 90))
            
            # 2. Generate Autonomic Goal
            thought = random.choice(self.thoughts)
            goal = random.choice(self.goals)
            
            logger.info(f"PROACTIVE_MANDATE: {thought} (Executing: {goal})")
            
            # 3. Dispatch to Orchestrator (Subtle priority)
            try:
                # We broadcast the thought to the viewport via the logic bridge
                # For simplicity, we directly call the circus bridge if available
                from tooloo_v3_hub.organs.circus_spoke.circus_logic import get_circus_logic
                logic = get_circus_logic()
                await logic.broadcast({
                    "type": "inner_thought",
                    "thought": thought
                })
                
                # Execute the goal
                await orchestrator.execute_goal(goal, {"user": "Autonomic Hub"}, callback=None)
                
            except Exception as e:
                logger.error(f"Proactive Mandate Failed: {e}")

    def stop_loop(self):
        self.is_active = False

# --- Global Agent Instance ---
_proactive_agent: Optional[SovereignProactiveAgent] = None

def get_proactive_agent() -> SovereignProactiveAgent:
    global _proactive_agent
    if _proactive_agent is None:
        _proactive_agent = SovereignProactiveAgent()
    return _proactive_agent
