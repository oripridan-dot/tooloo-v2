# WHAT: MODULE_MCP_NEXUS | Version: 1.4.0
# WHERE: tooloo_v3_hub/kernel/mcp_nexus.py
# WHEN: 2026-03-31T23:23:00.000000
# WHY: Federated Intelligence with Bit-Perfect JSON Serialization (Rule 2, 13)
# HOW: Subprocess Stdin/Stdout + Structured SDK Output Mapping
# TIER: T4:zero-trust
# DOMAINS: nerve-center, mcp, federation, async-io, infrastructure, serialization
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

from pathlib import Path
import asyncio
import os
import sys
import logging
import json
import uuid
from typing import Dict, Any, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("MCPNexus")

class MCPNexus:
    """
    The Active Nerve Center for TooLoo V3.
    Orchestrates the lifecycle and JSON-RPC routing of federated organs.
    """

    def __init__(self):
        self.tethers: Dict[str, Any] = {}
        self.request_futures: Dict[str, asyncio.Future] = {}
        logger.info("Sovereign MCP Nexus V1.4.0 Awakened (Serialization-Hardened).")

    async def initialize_default_organs(self):
        """Rule 13: Auto-tethers the core organ cluster."""
        base_path = Path(__file__).parent.parent
        python_exe = sys.executable
        
        organs = {
            "system_organ": ["organs", "system_organ", "mcp_server.py"],
            "vertex_organ": ["organs", "vertex_organ", "mcp_server.py"],
            "anthropic_organ": ["organs", "anthropic_organ", "mcp_server.py"],
            "openai_organ": ["organs", "openai_organ", "mcp_server.py"],
            "sovereign_chat": ["python3", "-m", "tooloo_v3_hub.organs.sovereign_chat.mcp_server", "--port", "8087"],
            "memory_organ": ["organs", "memory_organ", "mcp_server.py"],
            "claudio_organ": ["claudio_v3", "mcp_server.py"]
        }
        
        for name, p_parts in organs.items():
            if name == "sovereign_chat":
                env = os.environ.copy()
                env["PYTHONPATH"] = str(base_path.parent)
                await self.register_organ(name, "subprocess", {
                    "command": p_parts,
                    "env": env
                })
                continue

            script_path = base_path.joinpath(*p_parts)
            if not script_path.exists():
                # Check workspace root for decoupled products (like Claudio)
                script_path = base_path.parent.joinpath(*p_parts)
                
            if script_path.exists():
                # Setting PYTHONPATH to workspace root for internal imports
                env = os.environ.copy()
                env["PYTHONPATH"] = str(base_path.parent)
                
                await self.register_organ(name, "subprocess", {
                    "command": [python_exe, str(script_path)],
                    "env": env
                })
            else:
                logger.warning(f"Nexus: Organ script missing for '{name}' at {script_path}")

    async def attach_organ(self, name: str, command: List[str]):
        """Legacy alias for register_organ (Phase-Sync compatibility)."""
        await self.register_organ(name, "subprocess", {"command": command})

    async def register_organ(self, name: str, tether_type: str, config: Dict[str, Any]):
        """Launches and tethers a decentralized organ via persistent async streams (Rule 13)."""
        logger.info(f"Nexus: Orchestrating Organ '{name}' (Type: {tether_type})...")
        
        if tether_type == "subprocess":
            command = config.get("command")
            env = config.get("env", os.environ)
            
            try:
                server_params = StdioServerParameters(
                    command=command[0],
                    args=command[1:],
                    env=env
                )
                
                # Opening stdio transport
                async def _startup():
                    try:
                        async with stdio_client(server_params) as (read, write):
                            async with ClientSession(read, write) as session:
                                 await session.initialize()
                                 
                                 # Store session for calling tools
                                 self.tethers[name] = {
                                     "session": session,
                                     "type": tether_type,
                                     "status": "Online",
                                     "tools": []
                                 }
                                 
                                 # Discover Tools
                                 tools_resp = await session.list_tools()
                                 self.tethers[name]["tools"] = tools_resp.tools
                                 logger.info(f"✅ Organ '{name}' TETHERED. Discovered {len(tools_resp.tools)} tools.")
                                 
                                 # Keep alive until session ends
                                 while True:
                                     await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Nexus: Tether [{name}] dissolved with error: {e}")
                        if name in self.tethers:
                            self.tethers[name]["status"] = "Offline"

                # Run tether in background task
                self.tethers[name] = {"task": asyncio.create_task(_startup()), "status": "Tethering..."}
                
                # Wait for session to be ready
                for _ in range(10):
                    if name in self.tethers and "session" in self.tethers[name]: break
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Failed to tether organ '{name}': {e}")
                raise
        else:
            logger.warning(f"Tether type '{tether_type}' not yet implemented for real-mode.")

    async def call_tool(self, organ_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Dispatches an async tool call via the MCP SDK (Rule 2)."""
        if organ_name not in self.tethers or "session" not in self.tethers[organ_name]:
            # Critical Trigger: JIT Tether Attempt if missing but in cluster
            await self.initialize_default_organs()
            if organ_name not in self.tethers:
                raise ValueError(f"Organ '{organ_name}' is not tethered and could not be reconstructed.")
            
        session = self.tethers[organ_name]["session"]
        logger.debug(f"Nexus -> {organ_name}: Call tool '{tool_name}' via MCP SDK")
        
        try:
            result = await session.call_tool(tool_name, arguments)
            
            # [SERIALIZATION_HARDENING] Convert TextContent/ImageContent objects to plain dicts
            serializable_content = []
            for block in result.content:
                if hasattr(block, 'text'):
                    serializable_content.append({"type": "text", "text": block.text})
                elif hasattr(block, 'data') and hasattr(block, 'mime_type'):
                    # Encode data to avoid raw binary if possible, or skip if too large
                    serializable_content.append({"type": "image", "data_len": len(block.data), "mime_type": block.mime_type})
                elif isinstance(block, dict):
                    serializable_content.append(block)
                else:
                    serializable_content.append({"type": "unknown", "repr": str(block)})
            
            return serializable_content
        except Exception as e:
            logger.error(f"Nexus: Execution fault on tool [{tool_name}]: {e}")
            raise

_nexus = None

def get_mcp_nexus() -> MCPNexus:
    global _nexus
    if _nexus is None:
        _nexus = MCPNexus()
    return _nexus