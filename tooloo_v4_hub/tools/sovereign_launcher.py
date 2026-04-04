# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: SOVEREIGN_LAUNCHER.PY | Version: 1.3.0
# WHERE: tooloo_v4_hub/tools/sovereign_launcher.py
# WHEN: 2026-03-31T22:10:00.000000
# WHY: Pivot to Logic Foundations and 2D Sovereign Chat (Rule 7, 13)
# HOW: Orchestrated Async Process Pulse (Deactivating 3D)
# TIER: T3:architectural-purity
# DOMAINS: nerve-center, orchestration, launcher, infrastructure, lifecycle
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import sys
import os
from pathlib import Path

# Setup structured logging for the launcher
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SovereignLauncher")

async def launch_hub_api():
    """Starts the Hub API and internal cognitive engines in the background."""
    from tooloo_v4_hub.kernel.hub_api import app
    import uvicorn
    
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    
    logger.info(f"Initializing Sovereign Hub API on port {port}...")
    return asyncio.create_task(server.serve())

async def tether_organs():
    """Sequentially tethers federated organs to the active MCP Nexus."""
    from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
    nexus = get_mcp_nexus()
    
    python_exec = sys.executable
    
    # 1. Memory Organ (Persistent Cognition)
    logger.info("Tethering Organ: Memory (v1.0.0)...")
    await nexus.register_organ("memory", "subprocess", {
        "command": [python_exec, "-m", "tooloo_v4_hub.organs.memory_organ.mcp_server"]
    })
    
    # 2. Sovereign Chat (2D Developer Portal) - Replacing 3D Circus Spoke
    logger.info("Tethering Organ: Sovereign_Chat (v1.3.0)...")
    await nexus.register_organ("sovereign_chat", "subprocess", {
        "command": [python_exec, "-m", "tooloo_v4_hub.organs.sovereign_chat.mcp_server"]
    })
    
    # [DEACTIVATED] 3. Circus Spoke (3D Manifestation)
    # logger.info("Circus Spoke (3D) Deactivated for Logic Purity.")

async def run_sovereign_loop():
    """Main lifecycle pulse for the Hub and Federated Spoke matrix."""
    logger.info("--- Sovereign Purity Pulse: Initiating Logic Foundations (1.3.0) ---")
    
    # 1. Start Hub API
    hub_task = await launch_hub_api()
    
    # 2. Initialize Organ Matrix
    await tether_organs()
    
    logger.info("✅ Federated Matrix Active. Hub Status: SOVEREIGN.")
    logger.info(">>> Access Sovereign Chat at: http://localhost:8085")
    
    try:
        # 3. Persistent Loop (Watchdog for HubTask)
        while not hub_task.done():
            await asyncio.sleep(5.0)
    except asyncio.CancelledError:
        logger.info("Sovereign Shutdown Triggered. Severing Organ Tethers...")
    finally:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(run_sovereign_loop())
    except KeyboardInterrupt:
        logger.info("Sovereign Shutdown Manual Pulse Received. Terminating Cluster.")
