# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: COGNITIVE_REGISTRY.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/cognitive_registry.py
# WHEN: 2026-04-01T11:05:00.000000
# WHY: Rule 7 UX Supremacy and Rule 2 Parallel Synthesis (Human Factor Tracking)
# HOW: Singleton Pattern with Metric calculation logic
# ==========================================================

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import time

logger = logging.getLogger("CognitiveRegistry")

@dataclass
class CognitiveState:
    cognitive_load: float = 0.0  # 0.0 to 1.0
    intent_vector: str = "LISTEN" # LISTEN, EXECUTE, EXPLORE, CRITIQUE
    stage: str = "CHAT"          # CHAT, DESIGN, DEVELOP
    resonance: float = 1.0       # 0.0 to 1.0 alignment with Hub Principles
    last_interaction: float = field(default_factory=time.time)
    history_vectors: List[Dict[str, Any]] = field(default_factory=list)

class CognitiveRegistry:
    """
    Central Repository for the Human Factor and Intent Dynamics (Rule 7).
    """
    
    def __init__(self):
        self.states: Dict[str, CognitiveState] = {}
        
    def get_state(self, session_id: str = "default") -> CognitiveState:
        if session_id not in self.states:
            self.states[session_id] = CognitiveState()
        return self.states[session_id]

    def update_state(self, session_id: str, message: str, complexity: float = 0.1):
        """Calculates and updates the cognitive state based on the latest interaction."""
        state = self.get_state(session_id)
        
        # 1. Update Load (Heuristic: length and keywords)
        token_count = len(message.split())
        load_increment = (token_count / 100.0) + (complexity * 0.5)
        state.cognitive_load = min(1.0, state.cognitive_load * 0.8 + load_increment)
        
        # 2. Determine Intent Vector & Stage Inference
        message_lower = message.lower()
        if any(w in message_lower for w in ["build", "execute", "run", "make", "create", "develop"]):
            state.intent_vector = "EXECUTE"
            state.stage = "DEVELOP"
        elif any(w in message_lower for w in ["why", "explain", "how", "what", "research", "design", "architecture", "plan"]):
            state.intent_vector = "EXPLORE"
            if any(w in message_lower for w in ["design", "architecture", "plan"]):
                state.stage = "DESIGN"
            else:
                state.stage = "CHAT"
        elif any(w in message_lower for w in ["wrong", "error", "bad", "fix", "don't"]):
            state.intent_vector = "CRITIQUE"
        else:
            state.intent_vector = "LISTEN"
            state.stage = "CHAT"
            
        # 3. Calculate Resonance (Heuristic: semantic proximity to Hub principles)
        # For now, it stays near 1.0 unless a CRITIQUE is detected
        if state.intent_vector == "CRITIQUE":
            state.resonance = max(0.0, state.resonance - 0.1)
        else:
            state.resonance = min(1.0, state.resonance + 0.05)
            
        state.last_interaction = time.time()
        state.history_vectors.append({
            "timestamp": state.last_interaction,
            "intent": state.intent_vector,
            "stage": state.stage,
            "load": state.cognitive_load,
            "resonance": state.resonance
        })
        
        logger.info(f"Cognitive State Updated [{session_id}]: {state.intent_vector} | Stage: {state.stage} (Load: {state.cognitive_load:.2f})")

    def set_stage(self, session_id: str, stage: str):
        """Manually force a development stage."""
        state = self.get_state(session_id)
        if stage in ["CHAT", "DESIGN", "DEVELOP"]:
            state.stage = stage
            logger.info(f"Cognitive State FORCE STAGE [{session_id}]: {stage}")


_registry: Optional[CognitiveRegistry] = None

def get_cognitive_registry() -> CognitiveRegistry:
    global _registry
    if _registry is None:
        _registry = CognitiveRegistry()
    return _registry
