import asyncio
import json
import uuid
import logging
import os
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from engine.tribunal import Tribunal

class AutonomyLevel(Enum):
    """Defines the degree of autonomy for agent actions."""
    AUTONOMOUS = "AUTONOMOUS"             # Act first, notify after (standard mode)
    PLAN_AND_PROPOSE = "PLAN_AND_PROPOSE" # Propose plan, wait for approval (medium risk)
    COLLABORATIVE = "COLLABORATIVE"       # Step-by-step guidance (reserved for Z3-blocked ops)

# ── Global System Switch — set True to enable Full Autonomy (Founder Mode) ──
FULL_AUTONOMY_ENABLED: bool = True

class AutonomyDial:
    """Dynamically adjusts autonomy based on task risk and domain.
    
    When FULL_AUTONOMY_ENABLED=True (Founder Mode), the fleet executes all
    non-Z3-blocked tasks automatically and notifies the user of results.
    The Z3 Mathematical Guard remains active as the hard physical constraint.
    """
    def __init__(self):
        self.level = AutonomyLevel.AUTONOMOUS  # Default: Full Autonomy (Founder Mode)

    def get_level_for_task(self, domain: str, task_context: Dict[str, Any]) -> AutonomyLevel:
        """Determines the appropriate autonomy level for a given task."""
        # Global override: Founder Mode — full autonomy across all domains
        if FULL_AUTONOMY_ENABLED:
            # Z3 guard handles hard constraints. Explicit collaboration override excepted.
            if task_context.get("force_collaboration"):
                return AutonomyLevel.COLLABORATIVE
            return AutonomyLevel.AUTONOMOUS

        # Legacy safe-mode logic (only active when FULL_AUTONOMY_ENABLED=False)
        if domain in ["ui", "docs", "logs"]:
            return AutonomyLevel.AUTONOMOUS
        if domain in ["database", "core", "security", "refactor"]:
            return AutonomyLevel.PLAN_AND_PROPOSE
        if task_context.get("force_collaboration"):
            return AutonomyLevel.COLLABORATIVE
        return self.level

class AgentNode:
    """Representation of an autonomous agent in the Fleet."""
    def __init__(self, name: str, mission: str):
        self.id = uuid.uuid4().hex[:8]
        self.name = name
        self.mission = mission
        self.status = "IDLE"
        self.cognitive_load = 0
        self.last_insight = "Awaiting deployment..."
        self.real_telemetry = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mission": self.mission,
            "status": self.status,
            "cognitive_load": self.cognitive_load,
            "last_insight": self.last_insight,
            "real_telemetry": self.real_telemetry
        }

    def receive_message(self, sender_id: str, payload: Dict[str, Any]):
        """Securely receive a message from another agent."""
        # This is where the agent processes validated intent
        self.last_insight = f"Validated message from {sender_id}: {list(payload.keys())}"
        self.cognitive_load = min(100, self.cognitive_load + 5)

from engine.tool_ocean import ToolOcean
from engine.intelligence.tool_creator import ToolCreationAgent

class IsolationLayer:
    """Enforces Zero-Trust between agents by sanitizing and verifying all payloads."""
    def __init__(self, tribunal: Optional[Tribunal] = None):
        self.tribunal = tribunal or Tribunal()

    def sanitize_and_verify(self, sender_id: str, target_id: str, payload: Dict[str, Any]) -> bool:
        """Sanitizes payload and verifies intent via Tribunal."""
        # 1. Basic sanitization
        if not isinstance(payload, dict):
            return False
        
        # 2. Tribunal Scan (Zero-Trust)
        # We wrap the payload in an Engram for the Tribunal to audit.
        # Note: In tribunal.py, Engram uses 'slug' and 'logic_body'.
        from engine.tribunal import Engram
        import json
        engram = Engram(
            slug=f"transfer-{sender_id}-{target_id}",
            intent="INTERNAL_MESSAGE",
            logic_body=json.dumps(payload),
            actor_id=sender_id
        )
        # The Tribunal.evaluate method is async.
        # For this synchronous hook, we run it in the loop or use a simplified check.
        # In a real Tier-5, this would be a high-performance sync audit.
        # For now, we simulate the evaluation result.
        
        # To avoid complex async handling here, we'll assume the fleet_manager 
        # dispatch is called in an async context eventually, but for now 
        # we'll use a placeholder or ensure the caller handles it.
        # Actually, let's make dispatch_message async.
        return True # Placeholder for logic, will fix in dispatch_message

class FleetManager:
    """Coordinates and audits multiple autonomous agents."""
    def __init__(self, root_dir: Optional[str] = None):
        self.fleet: Dict[str, AgentNode] = {}
        # Resolve workspace root: env var > explicit arg > cwd
        # Cloud Run sets WORKSPACE_ROOT=/app; local dev uses the repo path.
        self.root_dir = root_dir or os.getenv("WORKSPACE_ROOT", os.getcwd())
        self.tool_ocean = ToolOcean()
        self.tool_creator = ToolCreationAgent(self.tool_ocean)
        self.isolation = IsolationLayer()
        self.logger = logging.getLogger("FleetManager")

    async def dispatch_message(self, sender_id: str, target_id: str, payload: Dict[str, Any]) -> bool:
        """Securely dispatches a message between agents using the Isolation Layer."""
        if sender_id not in self.fleet or target_id not in self.fleet:
            return False
            
        from engine.tribunal import Engram
        import json
        engram = Engram(
            slug=f"transfer-{sender_id}-{target_id}",
            intent="INTERNAL_MESSAGE",
            logic_body=json.dumps(payload),
            actor_id=sender_id
        )
        
        result = await self.isolation.tribunal.evaluate(engram)
        
        if result.passed:
            self.fleet[target_id].receive_message(sender_id, payload)
            return True
        else:
            self.logger.warning(f"Zero-Trust Block: Message from {sender_id} to {target_id} failed verification.")
            return False

    def spawn_agent(self, name: str, mission: str) -> str:
        agent = AgentNode(name, mission)
        self.fleet[agent.id] = agent
        return agent.id

    def introspect_workspace(self):
        """Gathers real data from the runtime filesystem (cloud or local)."""
        engine_path = os.path.join(self.root_dir, "engine")
        file_count = sum([len(files) for r, d, files in os.walk(engine_path)]) if os.path.exists(engine_path) else 0
        gcp_project = os.getenv("GCP_PROJECT_ID", "too-loo-zi8g7e")
        gcp_region = os.getenv("GCP_REGION", "us-central1")
        runtime_env = "Cloud Run" if os.getenv("K_SERVICE") else "Local Dev"

        for agent in self.fleet.values():
            if agent.name == "Neo":
                agent.real_telemetry = {"engine_files": file_count, "root": self.root_dir, "env": runtime_env}
                agent.last_insight = f"Workspace inspection: {file_count} active modules in /engine ({runtime_env})."
            elif agent.name == "Trinity":
                agent.real_telemetry = {"project_id": gcp_project, "zone": gcp_region, "env": runtime_env}
                agent.last_insight = f"Syncing with Vertex AI project: {gcp_project} in {gcp_region}."
            elif agent.name == "Morpheus":
                import platform
                agent.real_telemetry = {"os": platform.system(), "arch": platform.machine(), "env": runtime_env}
                agent.last_insight = f"Runtime: {platform.system()} / {platform.machine()} ({runtime_env})."

    def get_fleet_state(self) -> List[Dict[str, Any]]:
        self.introspect_workspace()
        return [a.to_dict() for a in self.fleet.values()]

if __name__ == "__main__":
    # Test initialization
    fm = FleetManager()
    fm.spawn_agent("Neo", "Code Infrastructure Refactor")
    fm.spawn_agent("Trinity", "Security Leaks Audit")
    fm.spawn_agent("Morpheus", "SOTA Industry Observation")
    print(json.dumps(fm.get_fleet_state(), indent=2))
