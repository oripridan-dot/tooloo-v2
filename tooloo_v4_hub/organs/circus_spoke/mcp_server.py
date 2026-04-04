# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MCP_SERVER.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/circus_spoke/mcp_server.py
# WHEN: 2026-03-31T14:26:13.352987+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: organ, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import sys
import json
import asyncio
import logging
from tooloo_v4_hub.organs.circus_spoke.circus_logic import get_circus_logic

# Setup minimal logging to stderr (stdout is reserved for MCP messages)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr)
logger = logging.getLogger("CircusSpoke-MCP")

class CircusMCPServer:
    """
    Standalone MCP Server for the Manifestation Circus (Spoke-1).
    Communicates via JSON-RPC over stdin/stdout.
    """
    
    def __init__(self):
        self.logic = get_circus_logic()
        logger.info("CircusMCPServer initialized. Awaiting commands.")

    async def run(self):
        """Main JSON-RPC loop over stdin."""
        # Step 1: Start the visual server in the background
        server_task = asyncio.create_task(self.logic.run_in_background())
        
        # Step 2: Handle Hub commands via stdin
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
                logger.error("Received malformed JSON.")
            except Exception as e:
                logger.error(f"Execution Error: {e}")

    async def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Routes MCP method calls to the Circus Logic."""
        method = req.get("method")
        params = req.get("params", {})
        rid = req.get("id")
        
        logger.info(f"Handling Request [id: {rid}]: {method}")
        
        result = None
        error = None
        
        try:
            if method == "tools/list":
                result = {"tools": [
                    {"name": "manifest_node", "description": "Manifest a 3D node in the spatial environment.", "inputSchema": {"type": "object"}},
                    {"name": "buddy_act", "description": "Execute a procedural animation on the Buddy avatar.", "inputSchema": {"type": "object"}},
                    {"name": "adjust_environment", "description": "Live-sculpt the 3D sanctuary settings (color, fog, intensity).", "inputSchema": {"type": "object"}},
                    {"name": "capture_viewport", "description": "Capture the current visual state.", "inputSchema": {"type": "object"}}
                ]}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "manifest_node":
                    # Call the async manifest method in the logic
                    node_id = arguments.get("id", "node-rand")
                    shape = arguments.get("shape", "cube")
                    color = arguments.get("color", "0x00ff88")
                    await self.logic.manifest(node_id, shape, color)
                    result = {"status": "success", "manifested": node_id}
                elif tool_name == "buddy_act":
                    # Execute a procedural animation or state shift on Buddy
                    directive = arguments.get("directive", "idle")
                    await self.logic.buddy_act(directive)
                    result = {"status": "success", "action": directive}
                elif tool_name == "adjust_environment":
                    settings = arguments.get("settings", {})
                    await self.logic.adjust_environment(settings)
                    result = {"status": "success", "adjusted": True}
                elif tool_name == "capture_viewport":
                    # Placeholder for screenshot logic
                    result = {"status": "success", "image_b64": "MOCK_VIEWPORT_PNK"}
                else:
                    error = {"code": -32601, "message": f"Tool '{tool_name}' not found."}
            else:
                error = {"code": -32601, "message": f"Method '{method}' not found."}
        except Exception as e:
            logger.error(f"Internal Processing Error: {e}")
            error = {"code": -32603, "message": str(e)}
            
        return {"jsonrpc": "2.0", "id": rid, "result": result, "error": error}

if __name__ == "__main__":
    server = CircusMCPServer()
    asyncio.run(server.run())