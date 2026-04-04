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
logger = logging.getLogger("SOTACheckup")

async def run_checkup():
    print("============================================================")
    print(" SOVEREIGN HUB: AUTONOMOUS SOTA CHECKUP (RULE 8)")
    print("============================================================")
    
    try:
        # 1. Initialize Vertex Logic
        logic = await get_vertex_logic()
        
        # 2. Run Live Inventory Refresh
        print("🌀 Initializing Cloud-Native Model Discovery...")
        await logic.refresh_garden_inventory()
        
        # 3. Print Results
        print("\n--- Current SOTA Registry Status ---")
        for provider, models in logic.sota_registry.items():
            print(f"Provider: {provider.upper()} ({len(models)} models discovered)")
            for m in models[:3]: # Show top 3
                print(f"  - {m['id']} [Tier: {m.get('tier', 'unknown')}]")
        
        print("\n✅ Checkup Complete. Operating Brain Synchronized.")
        print("============================================================")
        
    except Exception as e:
        logger.error(f"SOTA Checkup Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_checkup())
