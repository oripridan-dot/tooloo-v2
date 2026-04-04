# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: TEST_CLAUDIO_INTEGRATION.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/reality_check/TEST_CLAUDIO_INTEGRATION.py
# WHEN: 2026-04-03T16:08:23.410891+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus

# Configure logging for 16-Rule Transparency
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClaudioIntegrationTest")

async def test_claudio_decoupling():
    """
    Rule 13: Physical Decoupling Verification.
    Verifies that the Hub can tether the standalone Claudio product.
    """
    logger.info("--- INTEGRATION TEST: CLAUDIO DECOUPLING ---")
    
    nexus = get_mcp_nexus()
    
    # 1. Initialize Default Organs (Including the new decoupled Claudio)
    logger.info("Nexus: Initializing federated organ cluster...")
    await nexus.initialize_default_organs()
    
    # 2. Verify Claudio Tethering
    await asyncio.sleep(2) # Give it time to tether
    if "claudio_organ" in nexus.tethers:
        logger.info("✅ SUCCESS: 'claudio_organ' TETHERED from decoupled root.")
        tools = nexus.tethers["claudio_organ"].get("tools", [])
        logger.info(f"Claudio Tools: {[t.name for t in tools]}")
    else:
        logger.error("❌ FAILURE: 'claudio_organ' NOT TETHERED.")
        return

    # 3. Call Claudio Tool (The Federated SOTA Pulse)
    logger.info("Nexus: Dispatching SOTA Realtime pulse to Claudio...")
    try:
        res = await nexus.call_tool("claudio_organ", "start_claudio_realtime", {"modal": "audio_text"})
        logger.info(f"Claudio Response: {res[0]['text']}")
    except Exception as e:
        logger.error(f"❌ Tool Call FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_claudio_decoupling())
