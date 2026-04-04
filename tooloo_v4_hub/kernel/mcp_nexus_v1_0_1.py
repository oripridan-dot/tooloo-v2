# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_MCP_NEXUS.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/kernel/mcp_nexus.py
# WHEN: 2026-04-03T10:37:24.420247+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

# WHAT: MODULE_MCP_NEXUS | Version: 1.4.0
# WHERE: tooloo_v4_hub/kernel/mcp_nexus.py
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
from typing import Dict, Any, List, Optional, Union

# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client

logger = logging.getLogger("MCPNexus")

class MCPNexus:
    """
    The Active Nerve Center for TooLoo V3.
    Orchestrates the lifecycle and JSON-RPC routing of federated organs.
    """

    def __init__(self):
        self.tethers: Dict[str, Any] = {}
        self.request_futures: Dict[str, asyncio.Future] = {}
        self._init_lock = asyncio.Lock()  # Rule 12: Atomic Awakening
        logger.info("Sovereign MCP Nexus V1.4.0 Awakened (Serialization-Hardened).")

    async def initialize_default_organs(self):
        """Rule 13: Auto-tethers the core organ cluster (Lazy if LEAN_MODE active)."""
        async with self._init_lock:
            # Check if already initialized inside the lock
            if any(t.get("status") == "Online" for t in self.tethers.values()):
                return
        # Federated Cloud Logic (Cloud Mode Immunity)
        # Rule 18: In Cloud Run, we WANT LEAN_MODE to prevent OOM on start
        lean_mode = os.getenv("LEAN_MODE", "false").lower() == "true"
        if os.getenv("CLOUD_NATIVE_WORKSPACE") == "true" and not lean_mode:
            # Default to Lean in Cloud unless explicitly forced otherwise, 
            # as the Hub is the primary orchestrator and organs should be JIT.
            lean_mode = True
            logger.info("Nexus: Cloud Native detected. Defaulting to LEAN_MODE=True for stability.")
        else:
            logger.info("Nexus: LEAN_MODE forced to False or local mode active.")
        
        logger.info(f"Nexus Initialization: LEAN_MODE={lean_mode} (Raw: {os.getenv('LEAN_MODE')})")
        if lean_mode:
            logger.info("Nexus: LEAN_MODE active. Checking for mandatory cloud tethering...")
            if os.getenv("DEFAULT_ORGAN") == "cloud_worker":
                await self.register_organ("cloud_worker", "rest", {
                    "url": os.getenv("CLOUD_WORKER_URL", "https://sovereign-cloud-worker-v4-gru3xdvw6a-zf.a.run.app")
                })
            return

        base_path = Path(__file__).parent.parent
        python_exe = sys.executable
        
        organs = {
            "system_organ": ["organs", "system_organ", "mcp_server.py"],
            "vertex_organ": ["organs", "vertex_organ", "mcp_server.py"],
            "anthropic_organ": ["organs", "anthropic_organ", "mcp_server.py"],
            "openai_organ": ["organs", "openai_organ", "mcp_server.py"],
            "sovereign_chat": ["python3", "-m", "tooloo_v4_hub.organs.sovereign_chat.mcp_server", "--port", "8087"],
            "memory_organ": ["organs", "memory_organ", "mcp_server.py"],
            "cognitive_organ": ["organs", "cognitive_organ", "mcp_server.py"],
            "audio_organ": ["organs", "audio_organ", "mcp_server.py"]
        }
        
        for name, p_parts in organs.items():
            # Standardize environment with Global Sovereignty (Rule 14)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(base_path.parent)
            
            # Regional Sovereignty Propagation
            if "ACTIVE_SOVEREIGN_PROJECT" in os.environ:
                 env["ACTIVE_SOVEREIGN_PROJECT"] = os.environ["ACTIVE_SOVEREIGN_PROJECT"]
            if "ACTIVE_SOVEREIGN_REGION" in os.environ:
                 env["ACTIVE_SOVEREIGN_REGION"] = os.environ["ACTIVE_SOVEREIGN_REGION"]
            if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                 env["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

            if name == "sovereign_chat":
                await self.register_organ(name, "subprocess", {
                    "command": p_parts,
                    "env": env
                }, lazy=lean_mode)
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
                }, lazy=lean_mode)
            else:
                logger.warning(f"Nexus: Organ script missing for '{name}' at {script_path}")

    async def attach_organ(self, name: str, command: Union[str, List[str]]):
        """
        Legacy alias for register_organ (Phase-Sync compatibility).
        Cloud Awareness: String input is treated as a remote REST organ (e.g., SSE URL).
        """
        if isinstance(command, str) and (command.startswith("http://") or command.startswith("https://")):
            logger.info(f"Nexus: Hub-Redirect [REST] -> {name} @ {command}")
            await self.register_organ(name, "rest", {"url": command})
        else:
            await self.register_organ(name, "subprocess", {"command": command})

    async def register_organ(self, name: str, tether_type: str, config: Dict[str, Any], lazy: bool = False):
        """Registers a decentralized organ. If lazy=True, orchestration is deferred."""
        # [DEFERRED_AWAKENING] JIT Library Loading to avoid Cloud Run Cold-Start Hangs
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        if lazy:
            logger.info(f"Nexus: Organ '{name}' registered (Lazy-Wake enabled).")
            self.tethers[name] = {
                "type": tether_type,
                "config": config,
                "status": "Dormant",
                "tools": []
            }
            return

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

        elif tether_type == "rest":
            url = config.get("url")
            self.tethers[name] = {
                "url": url,
                "type": "remote",
                "status": "Online",
                "tools": [{"name": "call_tool"}] # Default for Cloud Worker
            }
            logger.info(f"✅ Remote Organ '{name}' BOUND to {url}.")

        else:
            logger.warning(f"Tether type '{tether_type}' not yet implemented for real-mode.")

    async def call_tool(self, organ_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Dispatches an async tool call via the MCP SDK or REST (Rule 2)."""
        # 1. Bootstrap the Nexus (Lazy Organ Discovery) - Rule 13
        # WE DO NOT START ORGANS HERE in Cloud Mode to allow Uvicorn to bind immediately.
        # The organs will awaken on the first /execute or /call_tool call.
        get_mcp_nexus()
        logger.info("HubAPI: Passive Organ Discovery Active (Lazy-Wake enabled).")
        if organ_name not in self.tethers:
             # Try lazy init of THE ENTIRE HUB if nothing is tethered
             if not self.tethers: 
                 await self.initialize_default_organs()
             
             if organ_name not in self.tethers:
                 raise ValueError(f"Organ '{organ_name}' is not registered.")

        tether = self.tethers[organ_name]
        
        # [LAZY_WAKE] Orchestrate dormant organ on-demand
        if tether.get("status") == "Dormant":
            logger.info(f"Nexus: Awakening Dormant Organ '{organ_name}'...")
            await self.register_organ(organ_name, tether["type"], tether["config"], lazy=False)
            tether = self.tethers[organ_name]
        
        # REST Dispatched for Cloud Organs (Rule 13: Normalization)
        if tether.get("type") == "remote":
            import requests
            # Rule 13: Standardized REST execution endpoint (Hub API Contract)
            url = f"{tether['url']}/call_tool"
            
            # Rule 10: Sovereign Handshake (Authentication)
            headers = {
                "X-Sovereign-Key": os.getenv("SOVEREIGN_KEY", "SOVEREIGN_HUB_2026_V3"),
                "Content-Type": "application/json"
            }
            
            # Rule 13: ToolCallRequest Structure
            payload = {
                "organ": organ_name,
                "tool": tool_name,
                "arguments": arguments
            }
            
            logger.info(f"Nexus: Dispatching Secure REST pulse to {organ_name} -> {tool_name}")
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=120) # 120s Cognitive Limit
                resp.raise_for_status()
                try:
                    data = resp.json()
                    if isinstance(data, list): return data
                    return [{"type": "text", "text": json.dumps(data)}]
                except:
                    return [{"type": "text", "text": resp.text}]
            except Exception as e:
                logger.error(f"Nexus: Remote Organ Fatigue [{organ_name}] on '{tool_name}': {e}")
                raise

        # Standard MCP Dispatched for Local Organs
        if "session" not in tether:
             if tether.get("status") == "Tethering...":
                 logger.info(f"Nexus: Waiting for Organ '{organ_name}' handshake...")
                 # Wait up to 15 seconds
                 for _ in range(30):
                     await asyncio.sleep(0.5)
                     if "session" in self.tethers.get(organ_name, {}):
                         tether = self.tethers[organ_name]
                         break
             
             if "session" not in tether:
                 raise ValueError(f"Organ '{organ_name}' has no active session (Status: {tether.get('status')}).")
            
        session = tether["session"]
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