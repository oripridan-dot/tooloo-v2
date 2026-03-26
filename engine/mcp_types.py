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
