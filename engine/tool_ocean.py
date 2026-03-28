# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining tool_ocean.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.926736
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/tool_ocean.py — Dynamic registry for JIT-synthesized Python tools.

Enables the TooLoo engine to expand its own capabilities at runtime by 
registering and hot-reloading tools authored by the ToolCreationAgent.
"""
from __future__ import annotations

import importlib.util
import inspect
import logging
import os
import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.mcp_types import MCPToolSpec

logger = logging.getLogger("tool_ocean")

class ToolOcean:
    """A dynamic repository for tools authored by the primary engine agents."""
    
    def __init__(self, storage_dir: str = "engine/tool_ocean"):
        self._workspace_root = Path(__file__).resolve().parents[1]
        self._storage_dir = self._workspace_root / storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._dynamic_tools: Dict[str, tuple[Callable[..., Dict[str, Any]], MCPToolSpec]] = {}
        
        # Ensure the storage directory is in sys.path for dynamic imports
        if str(self._storage_dir) not in sys.path:
            sys.path.append(str(self._storage_dir))

    @property
    def tools(self) -> Dict[str, tuple[Callable[..., Dict[str, Any]], MCPToolSpec]]:
        """Returns the active dynamic tool registry."""
        return self._dynamic_tools

    def register_tool(self, tool_id: str, code: str, spec: MCPToolSpec) -> bool:
        """Saves tool code to disk and registers it in the active registry."""
        try:
            file_name = f"{tool_id}.py"
            file_path = self._storage_dir / file_name
            file_path.write_text(code, encoding="utf-8")
            
            # Hot-load the module
            module_name = f"dynamic_tool_{tool_id}"
            spec_module = importlib.util.spec_from_file_location(module_name, str(file_path))
            if not spec_module or not spec_module.loader:
                logger.error(f"Failed to create spec for tool {tool_id}")
                return False
                
            module = importlib.util.module_from_spec(spec_module)
            spec_module.loader.exec_module(module)
            
            # Identify the handler function (assumed to be 'handler' or matching name)
            handler = getattr(module, "handler", None) or getattr(module, spec.name, None)
            if not handler or not callable(handler):
                logger.error(f"Tool {tool_id} does not expose a valid 'handler' function.")
                return False
                
            self._dynamic_tools[spec.name] = (handler, spec)
            logger.info(f"Successfully registered dynamic tool: {spec.name} (mcp://tooloo/dynamic/{spec.name})")
            return True
        except Exception as e:
            logger.error(f"Failed to register dynamic tool {tool_id}: {e}")
            return False

    def get_tool(self, name: str) -> Optional[tuple[Callable[..., Dict[str, Any]], MCPToolSpec]]:
        """Retrieves a registered dynamic tool by name."""
        return self._dynamic_tools.get(name)

    def list_tools(self) -> List[MCPToolSpec]:
        """Returns metadata for all registered dynamic tools."""
        return [spec for _, spec in self._dynamic_tools.values()]

    def unregister_tool(self, name: str):
        """Removes a tool from the active registry entries."""
        if name in self._dynamic_tools:
            del self._dynamic_tools[name]
