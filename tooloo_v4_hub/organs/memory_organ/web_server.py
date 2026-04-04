# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: WEB_SERVER.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/memory_organ/web_server.py
# WHEN: 2026-03-31T14:26:13.351378+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: organ, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from memory_logic import MemoryOrganLogic
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Memory-SSE-Server")

# Initialize Logic
logic = MemoryOrganLogic()

# Initialize MCP Server
server = Server("MemoryOrgan-Federated")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available memory tools."""
    return [
        Tool(
            name="memory_store",
            description="Store an engram in the sovereign tier.",
            inputSchema={
                "type": "object",
                "properties": {
                    "engram_id": {"type": "string"},
                    "data": {"type": "object"}
                },
                "required": ["engram_id", "data"]
            }
        ),
        Tool(
            name="memory_query",
            description="Search the cognitive memory for context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Execute memory tools."""
    if not arguments:
        return [TextContent(type="text", text="No arguments provided.")]

    if name == "memory_store":
        result = logic.store_engram(arguments.get("engram_id", ""), arguments.get("data", {}))
        return [TextContent(type="text", text=str(result))]
    elif name == "memory_query":
        result = logic.query_memory(arguments.get("query", ""))
        return [TextContent(type="text", text=str(result))]
    else:
        raise ValueError(f"Tool '{name}' not found.")

# FastAPI app with SSE transport
app = FastAPI()
sse = SseServerTransport("/messages")

@app.get("/")
@app.get("/health")
async def health_check():
    """Rule 16: High-Fidelity Ready Check endpoint."""
    return {
        "status": "SOVEREIGN_V4_2_ACTIVE", 
        "organ": "MemoryOrgan", 
        "tier": "Platinum",
        "cloud_native": True
    }

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP client connections."""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

@app.post("/messages")
async def messages_endpoint(request: Request):
    """Message endpoint for the client to send JSON-RPC data."""
    await sse.handle_post_message(request.scope, request.receive, request._send)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)