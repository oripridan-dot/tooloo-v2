# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: SCRIPT_HUB_INDEX_PULSE | Version: 1.0.1
# WHERE: scripts/hub_index_pulse.py
# WHEN: 2026-04-03T16:25:00.000000
# WHY: Rule 9: 3-Tier Memory (Initial Context Pulse)
# HOW: Awaiting the PsycheSyncer.sync_all() call properly
# ==========================================================

import asyncio
import logging
import sys
from tooloo_v4_hub.kernel.governance.living_map import get_living_map
from tooloo_v4_hub.kernel.cognitive.psyche_syncer import get_psyche_syncer

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HubIndexPulse")

async def main():
    print("\n" + "="*60)
    print(" SOVEREIGN HUB: FULL INDEX PULSE (RULE 9/11)")
    print("="*60)
    
    # Ensure LivingMap is updated first
    print("Rebuilding Hub Topography...")
    mapping = get_living_map()
    mapping.rebuild_topography(root_dir=".")
    
    print(f"Nodes registered: {len(mapping.nodes)}")
    
    # Trigger Full Sync
    print("Initiating Semantic Indexing (Psyche sync)...")
    syncer = get_psyche_syncer()
    await syncer.sync_all()
    
    print("\n[SUCCESS] HUB INDEX PULSE COMPLETE.")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
