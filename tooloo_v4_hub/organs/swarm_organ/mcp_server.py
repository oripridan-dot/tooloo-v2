# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: mcp_server.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/swarm_organ/mcp_server.py
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Swarm Delegation Tools for Sub-Missions
# PURITY: 1.00
# ==========================================================

import asyncio
import os
import logging
import json
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP

# 1. Initialize FastMCP
mcp = FastMCP("swarm_organ")
logger = logging.getLogger("SwarmOrgan-MCP")

@mcp.tool()
async def spawn_subagent(label: str, goal: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Spawns a specialized subagent to achieve a specific goal.
    This creates a recursive execution context with focused intent.
    """
    from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
    orchestrator = get_orchestrator()
    
    ctx = context or {}
    ctx["swarm_label"] = label
    ctx["is_subagent"] = True
    
    logger.info(f"SwarmOrgan: Spawning Worker [{label}] for goal: {goal}")
    
    # Rule 12: Recursive Execution via Orchestrator
    results = await orchestrator.execute_goal(goal, ctx, mode="DIRECT")
    
    return json.dumps({
        "label": label,
        "goal": goal,
        "results": results,
        "status": "COMPLETED"
    }, indent=2)

@mcp.tool()
async def list_active_swarms() -> str:
    """Lists current active swarm missions from the MissionManager."""
    from tooloo_v4_hub.kernel.cognitive.mission_manager import get_mission_manager
    mm = get_mission_manager()
    
    swarms = [
        {"id": m.id, "goal": m.goal, "status": m.status} 
        for m in mm.active_missions.values() 
        if "SWARM" in m.goal or getattr(m, "is_subagent", False)
    ]
    
    return json.dumps(swarms, indent=2)

if __name__ == "__main__":
    mcp.run()
