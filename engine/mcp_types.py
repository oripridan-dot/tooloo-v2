# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.mcp_types.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/mcp_types.py — DTOs for the Model Context Protocol.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class MCPToolSpec:
    """Describes one registered MCP tool."""
    uri: str
    name: str
    description: str
    parameters: dict[str, Any]
    code: str = ""
    author: str = "system"

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

@dataclass
class MCPCallResult:
    """Result of one MCP tool invocation."""
    uri: str
    success: bool
    output: Any
    error: str | None = None
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "truncated": self.truncated,
        }
