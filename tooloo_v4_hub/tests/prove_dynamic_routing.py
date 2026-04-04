import asyncio
import sys
import logging
import json

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, '.')

from tooloo_v4_hub.organs.vertex_organ.vertex_logic import get_vertex_logic

async def run_proof():
    print("=== Tooloo V4: Dynamic Model Garden Routing Proof ===\n")
    logic = await get_vertex_logic()
    
    # Task 1: Heavy Complex Logic & Math
    intent_reasoning = {
        "logic": 0.95,
        "coding": 0.90,
        "speed": 0.10,
        "constitutional_purity": 1.00
    }
    
    print("\n[Skill Simulation 1] Deep Architecture Refactoring & Mathematical Theorem Proving")
    print(f"Intent Vector: {intent_reasoning}")
    res1 = await logic.garden_route(intent_vector=intent_reasoning, priority=1.5)
    print(f"-> SELECTED MODEL: {res1.get('model')} | PROVIDER: {res1.get('provider')}")
    print(f"   REASON: {res1.get('sovereign_verdict')}")
    
    # Task 2: Extremely Fast, Low-Cost UX Parsing
    intent_speed = {
        "speed": 0.99,
        "logic": 0.20,
        "coding": 0.40,
        "constitutional_purity": 0.50
    }
    
    print("\n[Skill Simulation 2] High-Frequency Event Loop JIT UI Parsing")
    print(f"Intent Vector: {intent_speed}")
    res2 = await logic.garden_route(intent_vector=intent_speed, priority=1.0)
    print(f"-> SELECTED MODEL: {res2.get('model')} | PROVIDER: {res2.get('provider')}")
    print(f"   REASON: {res2.get('sovereign_verdict')}")

    # Task 3: Vision & Multi-modal Task 
    intent_balanced = {
        "logic": 0.60,
        "speed": 0.70,
        "vision": 0.95,
        "constitutional_purity": 0.85
    }
    
    print("\n[Skill Simulation 3] UI Screenshot Validation & OCR Breakdown")
    print(f"Intent Vector: {intent_balanced}")
    res3 = await logic.garden_route(intent_vector=intent_balanced, priority=1.2)
    print(f"-> SELECTED MODEL: {res3.get('model')} | PROVIDER: {res3.get('provider')}")
    print(f"   REASON: {res3.get('sovereign_verdict')}")

if __name__ == "__main__":
    asyncio.run(run_proof())
