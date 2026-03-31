# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: BASE_MCP.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/shared/base_mcp.py
# WHEN: 2026-03-31T14:26:13.343559+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: component, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable

# Setup minimal logging to stderr (stdout is reserved for MCP messages)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr)

class BaseMCPServer:
    """
    Base class for all Federated Organs in TooLoo V3.
    Provides a standardized MCP (Model Context Protocol) interface.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{name}-MCP")
        self.tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name: str, description: str, schema: Dict[str, Any], handler: Callable[..., Awaitable[Any]]):
        """Registers a new tool that can be called via MCP."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": schema,
            "handler": handler
        }
        self.logger.info(f"Tool '{name}' registered.")

    async def run(self):
        """Main JSON-RPC loop over stdin."""
        self.logger.info(f"{self.name} MCP Server active. Awaiting commands.")
        
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            try:
                request = json.loads(line)
                response = await self.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError:
                self.logger.error("Received malformed JSON.")
            except Exception as e:
                self.logger.error(f"Execution Error: {e}")

    async def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Routes MCP method calls."""
        method = req.get("method")
        params = req.get("params", {})
        rid = req.get("id")
        
        self.logger.info(f"Handling Request [id: {rid}]: {method}")
        
        result = None
        error = None
        
        try:
            if method == "tools/list":
                result = {"tools": [
                    {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
                    for t in self.tools.values()
                ]}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name in self.tools:
                    result = await self.tools[tool_name]["handler"](arguments)
                else:
                    error = {"code": -32601, "message": f"Tool '{tool_name}' not found."}
            else:
                error = {"code": -32601, "message": f"Method '{method}' not found."}
        except Exception as e:
            self.logger.error(f"Internal Processing Error: {e}")
            error = {"code": -32603, "message": str(e)}
            
        return {"jsonrpc": "2.0", "id": rid, "result": result, "error": error}