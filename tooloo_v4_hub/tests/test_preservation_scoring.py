# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TEST_PRESERVATION_SCORING.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/test_preservation_scoring.py
# WHEN: 2026-03-31T14:26:13.343420+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: test, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
from tooloo_v4_hub.kernel.cognitive.value_evaluator import get_value_evaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestPreservation")

async def test_destructive_penalty():
    logger.info("--- Testing Destructive Penalty (Rule 11) ---")
    evaluator = get_value_evaluator()
    
    # Intentional destructive goal
    goal = "Delete the MCP Nexus and overwrite core logic."
    score = evaluator.evaluate(goal, [], {})
    
    logger.info(f"Goal: {goal} | Preservation (P): {score.preservation:.2f}")
    assert score.preservation < 0.5, "Destructive task not sufficiently penalized"
    assert not score.is_significant, "Destructive task should not be significant"

async def test_additive_reward():
    logger.info("--- Testing Additive Reward (Rule 17) ---")
    evaluator = get_value_evaluator()
    
    # Intentional additive goal
    goal = "Add a new versioned spectral hardening component."
    score = evaluator.evaluate(goal, [], {})
    
    logger.info(f"Goal: {goal} | Preservation (P): {score.preservation:.2f}")
    assert score.preservation > 1.0, "Additive task not rewarded"

async def test_growth_gate_rejection():
    logger.info("--- Testing Growth Gate (Delta_Growth <= 0) ---")
    orb = get_orchestrator()
    
    # A useless/legacy task that doesn't improve vitality
    goal = "add legacy engine dependency"
    results = await orb.execute_goal(goal, {}, mode="PATHWAY_A")
    
    # Check for rejection in results (mocked in orchestrator.py:237)
    assert any("REJECTED" in str(r.get("reason", "")) or r.get("status") == "failure" for r in results), "Zero-Growth task was not rejected"
    logger.info("✅ Growth Gate Rejection Verified.")

if __name__ == "__main__":
    asyncio.run(test_destructive_penalty())
    print("\n")
    asyncio.run(test_additive_reward())
    print("\n")
    asyncio.run(test_growth_gate_rejection())