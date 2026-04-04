# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: CLOUD_MISSION.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/tools/cloud_mission.py
# WHY: Rule 18 - Sovereign orchestration in the Cloud
# HOW: HTTP POST to /execute on the Sovereign Hub Cloud
# ==========================================================

import asyncio
import os
import httpx
import logging
import argparse
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CloudMission")

async def execute_cloud_mission(goal: str, mode: str = "MACRO"):
    # 1. Configuration
    CLOUD_HUB_URL = os.getenv("CLOUD_HUB_URL", "https://sovereign-hub-v4-awakening-hwn5gyft5q-zf.a.run.app")
    SOVEREIGN_KEY = os.getenv("SOVEREIGN_KEY", "SOVEREIGN_HUB_2026_V3")
    
    logger.info(f"Dispatching Cloud Mission: {goal}")
    
    # 2. Payload
    payload = {
        "goal": goal,
        "context": {"user": "Principal Architect", "source": "hub_node_local_sync"},
        "mode": mode,
        "async_execute": False
    }
    
    # 3. Dispatch Pulse
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{CLOUD_HUB_URL}/execute",
                json=payload,
                headers={"X-Sovereign-Key": SOVEREIGN_KEY}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("Cloud Mission: SUCCESS.")
                print("\n[MISSION COMPLETE] Result from Cloud Hub:")
                for res in data.get("results", []):
                    # Filter/Print key results
                    print(f"- {res.get('status', 'unknown')}: {res.get('node', 'unknown')}")
                    if "receipt" in res:
                        print(f"  Receipt Context: {res['receipt']}")
            else:
                logger.error(f"Cloud Mission: FAILED ({response.status_code}). Detail: {response.text}")
                
        except Exception as e:
            logger.error(f"Communication Failure: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch a Sovereign Mission to the Cloud Hub.")
    parser.add_argument("goal", help="The mission goal to execute.")
    parser.add_argument("--mode", default="MACRO", help="Execution mode (DIRECT, MACRO, MEGA).")
    args = parser.parse_args()
    
    asyncio.run(execute_cloud_mission(args.goal, args.mode))
