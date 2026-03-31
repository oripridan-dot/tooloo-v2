import asyncio
import logging
import json
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator
from tooloo_v3_hub.kernel.mcp_nexus import get_nexus

logging.basicConfig(level=logging.INFO)

async def main():
    orchestrator = get_orchestrator()
    nexus = get_nexus()
    
    # 1. Attach the Federated Organs
    await nexus.attach_organ("memory", ["python3", "-m", "tooloo_v3_hub.organs.memory_organ.mcp_server"])
    await nexus.attach_organ("circus", ["python3", "-m", "tooloo_v3_hub.organs.circus_spoke.mcp_server"])
    
    # 2. Execute the Goal
    goal = "Buddy, manifest in the spatial viewport and wave to the user, then transition to thinking pose."
    print(f"\n[Hub] Executing Goal: {goal}")
    
    results = await orchestrator.execute_goal(goal, {"user": "Principal Architect"})
    
    for r in results:
        print(f"\n[Hub] Milestone Result: {json.dumps(r, indent=2)}")

    print("\n[Hub] Buddy Manifestation Cycle Complete. Viewporte updated.")

if __name__ == "__main__":
    asyncio.run(main())
