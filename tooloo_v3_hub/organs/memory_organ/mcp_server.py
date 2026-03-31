# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MCP_SERVER.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/organs/memory_organ/mcp_server.py
# WHEN: 2026-03-31T14:26:13.351488+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: organ, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from tooloo_v3_hub.organs.memory_organ.memory_logic import MemoryOrganLogic

# 1. Initialize FastMCP
mcp = FastMCP("memory_organ")
logger = logging.getLogger("MemoryMCPServer")

# 2. Logic Instance
logic = MemoryOrganLogic(".")

@mcp.tool()
async def memory_store(engram_id: str, data: dict) -> dict:
    """Store an engram in the sovereign tier (Rule 9)."""
    return logic.store_engram(engram_id, data)

@mcp.tool()
async def memory_query(query: str) -> list:
    """Search the cognitive memory for context and engrams."""
    return logic.query_memory(query)

@mcp.tool()
async def soul_sync() -> bool:
    """Trigger galactic persistence and cross-node synchronization."""
    return await logic.soul_sync()

if __name__ == "__main__":
    mcp.run()