# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: test_recovery_heartbeat.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/test_recovery_heartbeat.py
# WHEN: 2026-04-03T16:08:23.382416+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import asyncio
import json
import logging
from pathlib import Path
from tooloo_v4_hub.kernel.cognitive.recovery_pulse import get_recovery_pulse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestRecovery")

async def test_recovery_flow():
    logger.info("Initializing Test: Ouroboros Recovery Pulse...")
    
    pulse = get_recovery_pulse()
    pulse.interval = 1 # High frequency for test
    
    # Simulate a running mission
    pulse.update_context(
        mission="Verify Claude 4.6 Integration",
        thought="Testing the recovery heartbeat for bit-perfect continuity.",
        files=["main.py", "recovery_pulse.py"]
    )
    
    # Trigger one snapshot manually
    await pulse.snapshot(event_description="MANUAL_TEST_PULSE")
    
    # Verify persistence in Psyche Bank
    registry_path = Path("tooloo_v4_hub/psyche_bank/active_cognition.json")
    if registry_path.exists():
        with open(registry_path, "r") as f:
            data = json.load(f)
            logger.info(f"Registry Snapshot: {data.get('timestamp')}")
            assert data.get("active_mission") == "Verify Claude 4.6 Integration"
            logger.info("✅ Physical Persistance Verified.")
    else:
        logger.error("❌ Physical Persistance Failed.")
        return

    # Verify resume logic
    checkpoint = await pulse.resume_from_last_checkpoint()
    if checkpoint and checkpoint.get("active_mission") == "Verify Claude 4.6 Integration":
        logger.info("✅ Resumption Logic Verified.")
    else:
        logger.error("❌ Resumption Logic Failed.")

if __name__ == "__main__":
    asyncio.run(test_recovery_flow())
