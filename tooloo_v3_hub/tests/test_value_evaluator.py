# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TEST_VALUE_EVALUATOR.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/tests/test_value_evaluator.py
# WHEN: 2026-03-31T14:26:13.343215+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: test, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator

logging.basicConfig(level=logging.INFO)

async def mock_callback(msg: str):
    print(f"[CALLBACK STREAM] {msg}")

async def test_low_value_boost():
    print("--- TESTING LOW VALUE JIT BOOST ---")
    orchestrator = get_orchestrator()
    
    # "fix print logic" is considered low value by the heuristics
    await orchestrator.execute_goal(
        goal="quick fix print logic", 
        context={}, 
        mode="PATHWAY_A", 
        callback=mock_callback
    )

async def test_high_value():
    print("--- TESTING HIGH VALUE SOTA MANIFEST ---")
    orchestrator = get_orchestrator()
    
    # "manifest 3D Buddy sota" is considered high value
    await orchestrator.execute_goal(
        goal="manifest 3D Buddy sota design", 
        context={}, 
        mode="PATHWAY_A", 
        callback=mock_callback
    )

if __name__ == "__main__":
    asyncio.run(test_low_value_boost())
    print("\n")
    asyncio.run(test_high_value())