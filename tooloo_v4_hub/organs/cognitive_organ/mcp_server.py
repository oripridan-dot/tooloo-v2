# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: mcp_server.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/cognitive_organ/mcp_server.py
# WHEN: 2026-04-03T16:08:23.384441+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

# WHAT: MCP_SERVER_COGNITIVE | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/cognitive_organ/mcp_server.py
# WHEN: 2026-04-02T01:50:00.000000
# WHY: Rule 1, 16 - Mental Dimension Evaluation and Refinement
# HOW: MCP-Stream over stdio + Sovereign Cognitive Kernel
# TIER: T3:architectural-purity
# DOMAINS: organ, mcp, cognitive, evaluation, dimension, formula
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import os
import logging
import json
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP

from tooloo_v4_hub.kernel.cognitive.value_evaluator import get_value_evaluator
from tooloo_v4_hub.kernel.cognitive.calibration import get_calibration_engine
from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry

# 1. Initialize FastMCP
mcp = FastMCP("cognitive_organ")
logger = logging.getLogger("CognitiveOrgan-MCP")

@mcp.tool()
async def evaluate_intent(goal: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Evaluates a goal string and maps it to 16D Mental Dimensions.
    Returns predicted Emergence and ValueScore based on (C+I)/ENV.
    """
    evaluator = get_value_evaluator()
    ctx = context or {}
    
    score = evaluator.calculate_emergence(goal, ctx)
    
    # Enrich with Cognitive Registry data
    registry = get_cognitive_registry()
    state = registry.get_state()
    
    result = {
        "goal": goal,
        "predicted_emergence": score.total_emergence,
        "value_score": score.value_score,
        "dimensions": score.dimensions,
        "session_load": state.cognitive_load,
        "intent_vector": state.intent_vector,
        "resonance": state.resonance
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def calculate_delta(predicted_score: float, actual_performance: float, feedback: str = "") -> str:
    """
    Rule 16: Executes Calibration by comparing predicted Emergence vs Actual Performance.
    Updates the 22D World Model weights in the Psyche Bank.
    """
    delta = actual_performance - predicted_score
    logger.info(f"Rule 16 Calibration Triggered. Predicted: {predicted_score:.2f}, Actual: {actual_performance:.2f}, Delta: {delta:.2f}")
    
    engine = get_calibration_engine()
    # Apply refinement (Refining logic/weights)
    await engine.refine_weights(domain="logic", delta=delta * 0.1) # 0.1 scaling coefficient
    
    result = {
        "delta": delta,
        "predicted": predicted_score,
        "actual": actual_performance,
        "calibration_status": "Refined",
        "feedback_noted": feedback
    }
    
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_mental_state() -> str:
    """
    Returns the current hierarchy and state of the 16 Mental Dimensions.
    """
    evaluator = get_value_evaluator()
    registry = get_cognitive_registry()
    state = registry.get_state()
    
    # Sort dimensions by weight to show current 'Focus'
    # Since we don't have a global 'current' weights in the Evaluator yet, 
    # we'll return the base dimensions.
    
    result = {
        "dimensions": evaluator.D16,
        "current_load": state.cognitive_load,
        "current_intent": state.intent_vector,
        "world_model_version": "v3.0.0"
    }
    
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    mcp.run()
