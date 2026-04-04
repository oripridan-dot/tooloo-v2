# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_MISSION_MANAGER | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/mission_manager.py
# WHEN: 2026-04-01T13:30:00.000000
# WHY: Rule 2 Async Parallel Orchestration (Non-Blocking Hub Context)
# HOW: Async Task Tracking + WebSocket Telemetry Handoff
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, orchestration, mission-control, telemetry
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import uuid
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MissionManager")

class Mission:
    """Represents an active background mission in the Hub."""
    def __init__(self, mission_id: str, goal: str):
        self.id = mission_id
        self.goal = goal
        self.start_time = time.time()
        self.status = "INITIATING"
        self.telemetry_log: List[Dict[str, Any]] = []
        self.results: List[Any] = []

    def log(self, message: str, level: str = "INFO", metadata: Optional[Dict] = None):
        entry = {
            "timestamp": time.time(),
            "message": message,
            "level": level,
            "metadata": metadata or {}
        }
        self.telemetry_log.append(entry)
        return entry

class SovereignMissionManager:
    """
    Sovereign Controller for Asynchronous Mission Execution.
    Bridges the gap between the Orchestrator's raw logic and the Chat's real-time UX.
    """
    def __init__(self):
        self.active_missions: Dict[str, Mission] = {}
        logger.info("Sovereign Mission Manager (V4.5.0) Awakened.")

    def create_mission(self, goal: str) -> str:
        mission_id = f"MISSION_{uuid.uuid4().hex[:8].upper()}"
        self.active_missions[mission_id] = Mission(mission_id, goal)
        return mission_id

    async def stream_telemetry(self, mission_id: str, message: str, level: str = "INFO", metadata: Optional[Dict] = None):
        """Broadcasts real-time telemetry from a background mission to the Portal."""
        mission = self.active_missions.get(mission_id)
        if not mission: return
        
        entry = mission.log(message, level, metadata)
        
        # Rule 2: Broadcast to Viewport via ChatLogic
        try:
            from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            await logic.broadcast({
                "type": "mission_telemetry",
                "mission_id": mission_id,
                "goal": mission.goal,
                "entry": entry
            })
        except Exception as e:
            logger.warning(f"Telemetry broadcast failed for mission {mission_id}: {e}")

    def complete_mission(self, mission_id: str, results: List[Any]):
        mission = self.active_missions.get(mission_id)
        if mission:
            mission.status = "COMPLETE"
            mission.results = results
            logger.info(f"Mission {mission_id} Complete. Results ingested into Sovereign Memory.")
            # We don't delete immediately; history is preserved for the session.

_mission_manager: Optional[SovereignMissionManager] = None

def get_mission_manager() -> SovereignMissionManager:
    global _mission_manager
    if _mission_manager is None:
        _mission_manager = SovereignMissionManager()
    return _mission_manager
