# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MCP_SERVER_CHAT | Version: 1.0.0
# WHERE: tooloo_v3_hub/organs/sovereign_chat/mcp_server.py
# WHEN: 2026-03-31T22:15:00.000000
# WHY: Federated 2D Chat Organ for Logic Foundations (Rule 13)
# HOW: MCP-Stream over stdio (JSON-RPC)
# TIER: T3:architectural-purity
# DOMAINS: organ, mcp, infrastructure, chat, federation
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from tooloo_v3_hub.organs.sovereign_chat.chat_logic import get_chat_logic

# 1. Initialize FastMCP
mcp = FastMCP("sovereign_chat")
logger = logging.getLogger("SovereignChat-MCP")

@mcp.tool()
async def chat_broadcast(message: str, role: str = "Buddy") -> str:
    """Broadcasts a message to the 2D chat viewport."""
    logic = get_chat_logic()
    await logic.broadcast({
        "type": "buddy_chat",
        "response": message,
        "speaker": role
    })
    return "Message Broadcasted."

@mcp.tool()
async def chat_status(status: str) -> str:
    """Updates the system status in the chat portal."""
    logic = get_chat_logic()
    await logic.broadcast({
        "type": "status_update",
        "status": status
    })
    return "Status Updated."

async def run():
    """Main entry for the chat organ."""
    logger.info("Sovereign Chat Organ: Awakening (FastMCP Mode)...")
    
    # Run the Chat Logic background worker (SSE/WS)
    logic_task = asyncio.create_task(get_chat_logic().run_in_background())
    
    # Run FastMCP (Stdio) asynchronously
    await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(run())
