#!/usr/bin/env python3
import time
import os
import sys
import logging
from datetime import datetime, timedelta, UTC
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OuroborosDaemon")

# Add root to sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.ouroboros_cycle import OuroborosCycle
from engine.resource_governor import ResourceGovernor # Assuming it exists based on Mission Control/Open files

async def main():
    duration_hours = 2
    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=duration_hours)
    
    logger.info(f"Ouroboros Daemon: Starting 2-hour autonomous perfection loop.")
    logger.info(f"Target End Time: {end_time.isoformat()}")
    
    cycle_count = 0
    governor = ResourceGovernor()

    while datetime.now(UTC) < end_time:
        cycle_count += 1
        logger.info(f"\n--- Ouroboros Cycle #{cycle_count} Starting ---")
        
        # Resource Governance Check
        stats = governor.get_throttle_log_entry()
        ram_pct = stats.get("ram_percent", 0)
        if ram_pct > 85:
            logger.warning(f"Ouroboros Daemon: High memory usage ({ram_pct}%). Sleeping for 5 minutes.")
            await asyncio.sleep(300)
            continue

        try:
            cycle = OuroborosCycle(god_mode=True)
            report = await cycle.run()
            logger.info(f"Cycle #{cycle_count} Complete. Verdict: {report.overall_verdict}")
        except Exception as e:
            logger.error(f"Ouroboros Daemon: Cycle failed with error: {e}")
            await asyncio.sleep(30) # Cool down on error
            
        # Passive sleep between cycles to prevent API thrashing
        await asyncio.sleep(60)
        
    logger.info(f"Ouroboros Daemon: 2-hour window expired. Total cycles completed: {cycle_count}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
