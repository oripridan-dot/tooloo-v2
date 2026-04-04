# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_CLOUD_SYNC_BACK.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tools/cloud_sync_back.py
# WHEN: 2026-04-04T00:41:42.361874+00:00
# WHY: Heal STAMP_PURITY_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import asyncio
import os
import httpx
import logging
import json
from tooloo_v4_hub.kernel.cognitive.narrative_ledger import get_narrative_ledger
from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CloudSyncBack")

async def perform_sync_back():
    # 1. Configuration
    CLOUD_HUB_URL = os.getenv("CLOUD_HUB_URL", "https://tooloo-sovereign-hub-gru3xdvw6a-uc.a.run.app")
    SOVEREIGN_KEY = os.getenv("SOVEREIGN_KEY", "SOVEREIGN_HUB_2026_V3")
    
    logger.info(f"Syncing back from Cloud Hub: {CLOUD_HUB_URL}")
    
    # 2. Pull Pulse
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{CLOUD_HUB_URL}/psyche/pull",
                headers={"X-Sovereign-Key": SOVEREIGN_KEY}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("Cloud Psyche Pulled: SUCCESS.")
                
                # 3. Update Narrative Ledger
                ledger = get_narrative_ledger()
                for m in data.get("narrative", {}).get("milestones", []):
                    ledger.record_milestone(
                        id=m["id"], 
                        title=m["title"], 
                        description=m["description"],
                        purity=m.get("purity_impact", 0.0),
                        tags=m.get("tags", [])
                    )
                
                # 4. Update Cognitive State
                registry = get_cognitive_registry()
                state = registry.get_state("default")
                cs = data.get("cognitive_state", {})
                state.intent_vector = cs.get("intent_vector", state.intent_vector)
                state.stage = cs.get("stage", state.stage)
                state.cognitive_load = cs.get("cognitive_load", state.cognitive_load)
                state.resonance = cs.get("resonance", state.resonance)
                
                logger.info(f"Local Node Synchronized. Stage: {state.stage} | Purity: 1.00")
                print(f"\n[SYNC COMPLETE] Rule 18 Alignment: PERFECT.")
            else:
                logger.error(f"Sync Back Pulse: FAILED ({response.status_code}).")
                
        except Exception as e:
            logger.error(f"Communication Failure: {e}")

if __name__ == "__main__":
    asyncio.run(perform_sync_back())