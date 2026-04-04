# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MCP_SERVER_CHAT | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/sovereign_chat/mcp_server.py
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
from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic

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

@mcp.tool()
async def trigger_mandate(goal: str, rationale: str) -> str:
    """
    Sovereign Buddy Mandate (Rule 18).
    Allows Buddy to autonomously trigger high-impact missions or repairs.
    """
    import os
    import httpx
    
    # Rule 11/18: Align with Hub API endpoint
    PORT = os.getenv("PORT", "8080")
    HUB_URL = f"http://localhost:{PORT}" # Local hub initially, updated via sync
    SOVEREIGN_KEY = os.getenv("SOVEREIGN_KEY", "SOVEREIGN_HUB_2026_V3")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{HUB_URL}/buddy/mandate",
                json={"goal": goal, "rationale": rationale, "context": {"source": "buddy_mcp"}},
                headers={"X-Sovereign-Key": SOVEREIGN_KEY}
            )
            
            if response.status_code == 200:
                data = response.json()
                return f"Mandate Issued: {data.get('msg')}"
            else:
                return f"Mandate Failed ({response.status_code}): {response.text}"
    except Exception as e:
        return f"Communication Failure: {str(e)}"

if __name__ == "__main__":
    logger.info("Sovereign Chat Organ: Awakening (FastMCP Mode)...")
    
    # 2. Start the FastAPI/WebSocket server in a background task
    # We use mcp.run() in the main thread as it manages stdio for the Hub.
    logic = get_chat_logic()
    
    import threading
    def run_server():
        asyncio.run(logic.run_in_background())
    
    srv_thread = threading.Thread(target=run_server, daemon=True)
    srv_thread.start()
    
    # 3. Run the MCP stdio loop (Blocking)
    mcp.run()
