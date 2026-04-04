# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: RECOVERY_PULSE.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/recovery_pulse.py
# WHEN: 2026-04-01T14:10:30.000000
# WHY: User Request: Autonomous work continuity after system crash (Rule 1, 9, 12)
# HOW: High-Frequency Session Serialization to Fast-Tier Memory
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, recovery, persistence
# PURITY: 1.00
# TRUST: T3:arch-purity
# ==========================================================

import asyncio
import logging
import json
import os
import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger("RecoveryPulse")

class RecoveryPulse:
    """
    The Ouroboros Heartbeat: Regularly snapshots the Hub's cognitive state.
    Allows for 1.00 Purity recovery after a process termination or crash.
    """

    def __init__(self, interval: int = 15):
        self.interval = interval
        self.is_running = False
        self.active_mission: Optional[str] = None
        self.thought_trace: List[str] = []
        self.open_files: List[str] = []
        
        # Psyche Bank Path
        self.registry_path = Path("tooloo_v4_hub/psyche_bank/active_cognition.json")

    async def start_recovery_loop(self):
        """Main background loop for the Ouroboros Heartbeat."""
        self.is_running = True
        logger.info(f"Recovery Pulse: Awakened. Interval: {self.interval}s.")
        
        while self.is_running:
            try:
                await self.snapshot()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"Recovery Pulse Fault: {e}")
                await asyncio.sleep(5)

    async def snapshot(self, event_description: Optional[str] = None):
        """Captures and persists the current architectural state."""
        from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic
        memory = await get_memory_logic()
        
        from tooloo_v4_hub.kernel.cognitive.mission_manager import get_mission_manager
        mission_manager = get_mission_manager()
        
        state = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "active_mission": self.active_mission,
            "mission_states": {mid: m.status for mid, m in mission_manager.active_missions.items()},
            "thoughts": self.thought_trace[-10:], # Last 10 thoughts
            "open_files": self.open_files,
            "event": event_description or "HEARTBEAT_TICK",
            "purity_score": 1.00
        }
        
        # 1. Persist to dedicated JSON for fast OS-level recovery
        try:
            with open(self.registry_path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Physical Snapshot Failed: {e}")

        # 2. Store as Engram in Fast Memory (Rule 9)
        await memory.store("session_checkpoint", state, layer="fast")
        
        logger.debug(f"Recovery Snapshot Captured: {state['timestamp']}")

    def update_context(self, mission: Optional[str] = None, thought: Optional[str] = None, files: Optional[List[str]] = None):
        """Allows other components to feed context into the Heartbeat."""
        if mission: self.active_mission = mission
        if thought: self.thought_trace.append(thought)
        if files: self.open_files = files

    async def resume_from_last_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Restores the Hub's focus from the last known-good state."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r") as f:
                    data = json.load(f)
                    logger.info(f"Recovery: Resuming from {data['timestamp']} | Mission: {data['active_mission']}")
                    return data
            except:
                logger.warning("Recovery: Checkpoint corrupted. Starting fresh.")
        return None

    def stop(self):
        self.is_running = False
        logger.info("Recovery Pulse: Hibernating.")

# --- Global Instance ---
_recovery_pulse: Optional[RecoveryPulse] = None

def get_recovery_pulse() -> RecoveryPulse:
    global _recovery_pulse
    if _recovery_pulse is None:
        _recovery_pulse = RecoveryPulse()
    return _recovery_pulse
