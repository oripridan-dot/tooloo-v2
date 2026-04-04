# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_AGENT_TYPES | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/agent_types.py
# WHEN: 2026-04-03T16:20:00.000000
# WHY: Primitive 12: Sharp Roles (Prevent Minion Cloning and Operational Drift)
# HOW: Type-Safe Persona Constraints and Allowed Tool Patterns
# TIER: T1:foundation-primitives
# DOMAINS: kernel, cognitive, roles, agency, governance
# PURITY: 1.00
# ==========================================================

from enum import Enum
from typing import List, Set
from pydantic import BaseModel

class AgentType(str, Enum):
    """Primitive 12: The core agent type system (Sharp Roles)."""
    EXPLORE = "EXPLORE"   # Research, analysis, discovery.
    PLAN = "PLAN"         # Strategy, decomposition, orchestration.
    VERIFY = "VERIFY"     # Auditing, evaluation, testing.
    GUIDE = "GUIDE"       # Interactive help, documentation, assistance.
    STATUS = "STATUS"     # Monitoring, state reporting, telemetry.

class AgentPersona(BaseModel):
    """Defines the operational constraints for a role (Rule 12)."""
    type: AgentType
    allowed_actions: Set[str] = set()
    forbidden_actions: Set[str] = set()
    max_turn_budget: int = 10
    requires_approval: bool = False

# --- Default Personas ---

PERSONAS = {
    AgentType.EXPLORE: AgentPersona(
        type=AgentType.EXPLORE,
        allowed_actions={"read_url", "search_web", "view_file", "list_dir", "grep_search"},
        forbidden_actions={"run_command", "write_to_file", "replace_file_content", "mcp_cloudrun_deploy"},
        max_turn_budget=15
    ),
    AgentType.PLAN: AgentPersona(
        type=AgentType.PLAN,
        allowed_actions={"analyze_architecture", "list_dir", "read_url", "view_file"},
        forbidden_actions={"run_command", "write_to_file", "mcp_cloudrun_deploy"},
        max_turn_budget=10,
        requires_approval=True
    ),
    AgentType.VERIFY: AgentPersona(
        type=AgentType.VERIFY,
        allowed_actions={"run_command", "view_file", "list_dir", "grep_search", "command_status"},
        forbidden_actions={"write_to_file", "replace_file_content", "mcp_cloudrun_deploy"},
        max_turn_budget=20
    ),
    AgentType.GUIDE: AgentPersona(
        type=AgentType.GUIDE,
        allowed_actions={"view_file", "list_dir", "search_web"},
        forbidden_actions={"run_command", "write_to_file", "replace_file_content"},
        max_turn_budget=5
    ),
    AgentType.STATUS: AgentPersona(
        type=AgentType.STATUS,
        allowed_actions={"list_dir", "command_status", "read_resource"},
        forbidden_actions={"run_command", "write_to_file", "search_web"},
        max_turn_budget=3
    )
}

def get_persona(agent_type: AgentType) -> AgentPersona:
    return PERSONAS.get(agent_type, PERSONAS[AgentType.GUIDE])
