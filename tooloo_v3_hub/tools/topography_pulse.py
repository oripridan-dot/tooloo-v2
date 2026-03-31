# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TOPOGRAPHY_PULSE.PY | Version: 1.0.0
# WHERE: tooloo_v3_hub/tools/topography_pulse.py
# WHEN: 2026-03-31T21:40:00.000000
# WHY: Force 3D spatial re-manifestation of the Living Map (Rule 7, 13)
# HOW: Orchestrated MCP tool call to circus_sync_topography
# TIER: T3:architectural-purity
# DOMAINS: research, tools, infrastructure, visualization, mapping
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import sys

async def trigger_pulse():
    """Commands the Circus Spoke to sync the entire Hub Topography to the 3D viewport."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TopographyPulse")
    
    logger.info("Initiating Hub Topography Pulse...")
    
    from tooloo_v3_hub.kernel.mcp_nexus import get_mcp_nexus
    nexus = get_mcp_nexus()
    
    # 1. Ensure Circus Spoke is tethered (Hub must be running)
    try:
        # If running as a standalone tool, we attempt to call the logic directly
        from tooloo_v3_hub.organs.circus_spoke.circus_logic import get_circus_logic
        logic = get_circus_logic()
        
        # We need the Living Map to be loaded
        from tooloo_v3_hub.kernel.governance.living_map import get_living_map
        get_living_map() # Bootstrapper
        
        # Trigger the sync
        result = await logic.sync_topography()
        logger.info(f"Topography Pulse: SUCCESS. {result.get('count')} nodes manifested in Spoke-1.")
        
    except Exception as e:
        logger.error(f"Topography Pulse: FAIL. Is the Hub running? Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(trigger_pulse())
