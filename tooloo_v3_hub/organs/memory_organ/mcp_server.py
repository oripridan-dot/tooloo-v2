# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MEMORY_ORGAN_MCP_v3.0.0 — The Federated Service
# WHERE: tooloo_v3_hub/organs/memory_organ/mcp_server.py
# WHEN: 2026-03-29T09:40:00.000000
# WHY: Standalone MCP bridge for cognitive persistence
# HOW: Stdout JSON-RPC Protocol (MCP Compliant)
# ==========================================================

import sys
import json
import asyncio
import logging
from tooloo_v3_hub.shared.base_mcp import BaseMCPServer
from tooloo_v3_hub.organs.memory_organ.memory_logic import MemoryOrganLogic

class MemoryMCPServer(BaseMCPServer):
    """
    Consolidated MCP Server for the Memory Organ.
    Inherits from BaseMCPServer for standardized JSON-RPC communication.
    """
    
    def __init__(self):
        super().__init__("MemoryOrgan")
        self.logic = MemoryOrganLogic(".")

    async def initialize_logic(self):
        """Pre-run logic initialization."""
        # Register Memory-specific tools
        self.register_tool(
            "memory_store", 
            "Store an engram in the sovereign tier.", 
            {"type": "object", "properties": {"engram_id": {"type": "string"}, "data": {"type": "object"}}},
            self.memory_store_handler
        )
        self.register_tool(
            "memory_query", 
            "Search the cognitive memory for context.", 
            {"type": "object", "properties": {"query": {"type": "string"}}},
            self.memory_query_handler
        )
        self.register_tool(
            "soul_sync", 
            "Trigger galactic persistence.", 
            {"type": "object"},
            self.soul_sync_handler
        )

    async def memory_store_handler(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.logic.store_engram(arguments.get("engram_id", ""), arguments.get("data", {}))

    async def memory_query_handler(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.logic.query_memory(arguments.get("query", ""))

    async def soul_sync_handler(self, arguments: Dict[str, Any]) -> bool:
        return await self.logic.soul_sync()

async def main():
    server = MemoryMCPServer()
    await server.initialize_logic()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
