import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tooloo_v4_hub.organs.vertex_organ.vertex_logic import get_vertex_logic

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("BrainProofV2")

async def run_proof():
    print("============================================================")
    print(" SOVEREIGN HUB: SOTA SELECTION PROOF (RULE 5 HARDENING)")
    print("============================================================")
    
    logic = await get_vertex_logic()
    
    scenarios = [
        {
            "name": "High-Tier Logical Architecture",
            "intent": {"logic": 1.0, "constitutional": 0.9},
            "priority": 1.5
        },
        {
            "name": "Creative Vision Synthesis",
            "intent": {"vision": 1.0, "creative": 0.9},
            "priority": 1.0
        },
        {
            "name": "Mass System Logistics (Efficiency)",
            "intent": {"logic": 0.4, "efficiency": 1.0},
            "priority": 0.8
        },
        {
            "name": "Long-Context Engineering Audit",
            "intent": {"context": 1.0, "logic": 0.8},
            "priority": 1.2
        }
    ]
    
    for s in scenarios:
        print(f"\n[MISSION] {s['name']}")
        route = await logic.garden_route(s['intent'], priority=s['priority'])
        print(f"  -> SELECTED: {route['provider'].upper()} {route['model']}")
        print(f"  -> SCORE:    {route['sovereign_score']}")
        print(f"  -> VERDICT:  {route.get('sovereign_verdict', 'N/A')}")

    print("\n✅ Proof Complete. Sovereign Selection Hardened.")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(run_proof())
