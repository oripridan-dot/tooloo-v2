# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: CLOUD_TRANSITION.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/tools/cloud_transition.py
# WHY: Rule 7/9/13 - Seamless context handover for "Buddy in the Cloud"
# HOW: HTTP POST to /context/sync on the Sovereign Cloud Hub
# ==========================================================

import asyncio
import os
import json
import httpx
import logging
from pathlib import Path
from tooloo_v4_hub.kernel.cognitive.narrative_ledger import get_narrative_ledger
from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CloudTransition")

async def perform_handover():
    # 1. Configuration
    CLOUD_HUB_URL = os.getenv("CLOUD_HUB_URL", "https://tooloo-sovereign-hub-gru3xdvw6a-uc.a.run.app")
    SOVEREIGN_KEY = os.getenv("SOVEREIGN_KEY", "SOVEREIGN_HUB_2026_V3")
    
    logger.info(f"Initiating Sovereign Handover to: {CLOUD_HUB_URL}")
    
    # 2. Gather Narrative
    ledger = get_narrative_ledger()
    narrative_data = {
        "milestones": [m.__dict__ for m in ledger.milestones]
    }
    
    # 3. Gather Cognitive State
    registry = get_cognitive_registry()
    state = registry.get_state("default")
    cognitive_data = {
        "intent_vector": state.intent_vector,
        "stage": state.stage,
        "cognitive_load": state.cognitive_load,
        "resonance": state.resonance
    }
    
    # 4. Gather Recent Engrams
    nexus = get_mcp_nexus()
    engrams = []
    try:
        # Get last 20 engrams
        engrams = await nexus.call_tool("memory_organ", "memory_query", {"query": "", "top_k": 20})
    except Exception as e:
        logger.warning(f"Failed to gather engrams: {e}")

    # 5. Build Payload
    payload = {
        "narrative": narrative_data,
        "cognitive_state": cognitive_data,
        "engrams": engrams,
        "session_id": "default",
        "sovereignty_takeover": True  # Rule 18: Primary Developer Pulse
    }
    
    # 6. Dispatch Pulse
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{CLOUD_HUB_URL}/context/sync",
                json=payload,
                headers={"X-Sovereign-Key": SOVEREIGN_KEY}
            )
            
            if response.status_code == 200:
                logger.info("Transition Pulse: SUCCESS. Context is now persistent in the Cloud Hub.")
                print("\n[HANDOVER COMPLETE] Rule 18 Manifested.")
                print(f"Cloud Hub URL: {CLOUD_HUB_URL}")
                print("Buddy is now the Primary Developer in the Cloud.")
            else:
                logger.error(f"Transition Pulse: FAILED ({response.status_code}). Detail: {response.text}")
                
        except Exception as e:
            logger.error(f"Communication Failure: {e}")


if __name__ == "__main__":
    asyncio.run(perform_handover())
