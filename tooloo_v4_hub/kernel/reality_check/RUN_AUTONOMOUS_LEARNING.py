# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: RUN_AUTONOMOUS_LEARNING.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/reality_check/RUN_AUTONOMOUS_LEARNING.py
# WHEN: 2026-04-03T16:08:23.408228+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import asyncio
import os
import logging
import time
from tooloo_v4_hub.kernel.cognitive.calibration import get_calibration_engine
from tooloo_v4_hub.kernel.cognitive.soul_sync import get_soul_sync
from tooloo_v4_hub.kernel.governance.audit import get_auditor

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("LearningSupervisor")

async def monitor_vitality(duration_sec: int = 60, interval_sec: int = 20):
    """Monitors the local Hub's Vitality Index as it learns."""
    auditor = get_auditor()
    print("\n" + "="*60)
    print("TOO LOO V3: AUTONOMOUS LEARNING IN PROGRESS")
    print("="*60)
    
    start_v = await auditor.calculate_vitality_index()
    print(f"Starting Vitality Index: {start_v['vitality']:.4f}")
    
    elapsed = 0
    while elapsed < duration_sec:
        await asyncio.sleep(interval_sec)
        elapsed += interval_sec
        current_v = await auditor.calculate_vitality_index()
        delta = current_v['vitality'] - start_v['vitality']
        print(f"[{elapsed}s] Vitality: {current_v['vitality']:.4f} (Delta: +{delta:.4f})")
        
    print("\n" + "="*60)
    print("LEARNING CYCLE COMPLETE (Background loops remain active)")
    print("="*60)

async def run_learning_process():
    # 1. Activate Local Calibration (Training) - Pulse: 30s for this demo
    calibration = get_calibration_engine()
    asyncio.create_task(calibration.start_calibration_loop(interval=30))
    logger.info("Local Calibration Engine: ACTIVE (Pulse: 30s)")
    
    # 2. Activate Local Soul Sync (Sharing) - Pulse: 60s
    soul_sync = get_soul_sync()
    asyncio.create_task(soul_sync.start_sync_loop(interval=60))
    logger.info("Local Soul Sync Protocol: ACTIVE (Pulse: 60s)")
    
    # 3. Monitor and Report
    await monitor_vitality(duration_sec=70, interval_sec=30)

if __name__ == "__main__":
    # Ensure environment set for federation
    os.environ["GALACTIC_HUB_URL"] = "https://sovereign-hub-v3-gru3xdvw6a-zf.a.run.app"
    os.environ["SOVEREIGN_KEY"] = "SOVEREIGN_HUB_2026_V3"
    
    try:
        asyncio.run(run_learning_process())
    except KeyboardInterrupt:
        print("\nShutdown requested.")
