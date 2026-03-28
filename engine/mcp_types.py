# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining mcp_types.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.931040
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
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
