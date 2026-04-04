# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_COMMAND_REGISTRY | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/command_registry.py
# WHEN: 2026-04-03T16:40:00.000000
# WHY: Primitive 1: Metadata-First Tool Registry (Distinguish Command/Tool)
# HOW: Data-driven command definitions with SDK/REST mapping.
# TIER: T1:foundation-primitives
# DOMAINS: kernel, cognitive, registry, commands, tools
# PURITY: 1.00
# ==========================================================

from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class CommandMetadata(BaseModel):
    """Primitive 1: Command Metadata Structure."""
    name: str
    description: str
    requires_approval: bool = False
    trust_tier: str = "PLUG_IN"
    target_organ: str = "system_organ"

COMMANDS = {
    "view_file": CommandMetadata(
        name="view_file",
        description="Reads the contents of a local file.",
        trust_tier="BUILT_IN"
    ),
    "run_command": CommandMetadata(
        name="run_command",
        description="Executes a shell command in the local environment.",
        requires_approval=True,
        trust_tier="BUILT_IN"
    ),
    "search_web": CommandMetadata(
        name="search_web",
        description="Performs a Google Search via the sovereign worker.",
        trust_tier="SKILL",
        target_organ="cloud_worker"
    ),
    "mcp_cloudrun_deploy": CommandMetadata(
        name="mcp_cloudrun_deploy",
        description="Deploys a container or folder to Google Cloud Run.",
        requires_approval=True,
        trust_tier="PLUG_IN"
    )
}

class CommandRegistry:
    """The central authority for User-Facing Commands (Primitive 1)."""
    
    def __init__(self):
        self.commands = COMMANDS

    def get_command(self, name: str) -> Optional[CommandMetadata]:
        return self.commands.get(name)

    def list_commands(self) -> List[str]:
        return list(self.commands.keys())

_registry = None

def get_command_registry() -> CommandRegistry:
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry
