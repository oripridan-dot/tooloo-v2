# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TEST_OPERATIONAL_PULSE.PY | Version: 1.0.0
# WHERE: tooloo_v3_hub/tests/test_operational_pulse.py
# WHEN: 2026-03-31T20:20:00.000000
# WHY: Verify Federated Operational Connectivity (Rule 13, 16)
# HOW: MCP Tool-Execution Roundtrip
# TIER: T3:architectural-purity
# DOMAINS: research, testing, operational, federation, mcp
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import sys
import os
from tooloo_v3_hub.kernel.mcp_nexus import get_mcp_nexus

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("OperationalPulse")

async def run_pulse():
    """Executes a bit-perfect Model Context Protocol (MCP) tool call roundtrip."""
    logger.info("Initializing Operational Pulse Test...")
    nexus = get_mcp_nexus()
    python_exec = sys.executable
    
    # 1. Tether the Memory Organ
    logger.info("Tethering Memory Organ for Operational Pulse...")
    await nexus.register_organ("memory_test", "subprocess", {
        "command": [python_exec, "-m", "tooloo_v3_hub.organs.memory_organ.mcp_server"]
    })
    
    # Wait for discovery pulse
    await asyncio.sleep(2.0)
    
    # 2. Verify Discovery Pulse (Tool Registration)
    tools = nexus.tethers["memory_test"]["tools"]
    logger.info(f"Discovered Tools: {[t['name'] for t in tools]}")
    assert any(t["name"] == "memory_store" for t in tools), "Tool 'memory_store' not discovered."
    
    # 3. Execute Federated Tool Call (memory_store)
    logger.info("Triggering Federated Tool Execution: memory_store")
    test_engram = {"id": "pulse_test_001", "data": {"type": "operational_pulse", "status": "active"}}
    
    result = await nexus.call_tool("memory_test", "memory_store", {
        "engram_id": test_engram["id"],
        "data": test_engram["data"]
    })
    
    logger.info(f"✅ Tool Call Result: {result}")
    assert result.get("status") == "success", f"Tool execution failed: {result}"
    
    # 4. Cleanup (Severing Tether)
    logger.info("Operational Pulse: Test Complete. Hub is Operational.")

if __name__ == "__main__":
    try:
        asyncio.run(run_pulse())
        print("\n🏆 OPERATIONAL_PULSE: PASS")
    except Exception as e:
        logger.error(f"❌ OPERATIONAL_PULSE: FAIL -> {e}")
        sys.exit(1)
