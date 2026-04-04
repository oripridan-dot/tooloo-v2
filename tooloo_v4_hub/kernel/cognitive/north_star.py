# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_NORTH_STAR | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/north_star.py
# WHEN: 2026-04-03T14:15:00.000000
# WHY: Rule 1: Sovereign Core (The Persistent North Star)
# HOW: JSON Persistence + Singleton Accessor
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, navigation, alignment
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import os
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from tooloo_v4_hub.organs.memory_organ.firestore_persistence import get_firestore_persistence

logger = logging.getLogger("NorthStar")

@dataclass
class NorthStarState:
    macro_goal: str = "Initialize System Sovereignty"
    current_focus: str = "System Configuration"
    micro_goals: List[str] = field(default_factory=list)
    completed_milestones: List[str] = field(default_factory=list)
    vitality_score: float = 1.0 # Rule 16: Sovereign Vitality Index (SVI)
    last_mission_initiator: str = "ARCHITECT"

class SovereignNorthStar:
    """
    The centralized navigator for TooLoo V4.
    Maintains the 'Story So Far' and the 'Road Ahead'.
    """
    def __init__(self, storage_path: str = "tooloo_v4_hub/psyche_bank/north_star.json"):
        self.storage_path = storage_path
        self._state = NorthStarState()
        self.load()

    def load(self):
        """Loads state from persistence layer (Firestore in Cloud Native)."""
        cloud_native = os.getenv("CLOUD_NATIVE", "false").lower() == "true"
        if cloud_native:
            try:
                import asyncio
                # Use a background task or run_in_executor for sync firestore if needed, 
                # but here we'll assume a simpler sync fetch for the singleton init.
                fs = get_firestore_persistence()
                doc = fs.db.collection("sovereign_core").document("north_star").get()
                if doc.exists:
                    self._state = NorthStarState(**doc.to_dict())
                    logger.info(f"North Star Re-Stabilized (Firestore): {self._state.macro_goal}")
                    return
            except Exception as e:
                logger.error(f"North Star Firestore Recovery Failed: {e}. Falling back to local/default.")

        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self._state = NorthStarState(**data)
                logger.info(f"North Star Re-Stabilized: {self._state.macro_goal}")
            except Exception as e:
                logger.error(f"North Star Recovery Failed: {e}. Using default trajectory.")
        else:
            self.save() # Create initial file

    def save(self):
        """Persists current state to the Hub's psyche bank and Firestore."""
        cloud_native = os.getenv("CLOUD_NATIVE", "false").lower() == "true"
        payload = asdict(self._state)
        
        if cloud_native:
            try:
                fs = get_firestore_persistence()
                fs.db.collection("sovereign_core").document("north_star").set(payload, merge=True)
                logger.info("North Star: Synchronized to Firestore.")
            except Exception as e:
                logger.error(f"North Star Firestore Sync Error: {e}")

        dirname = os.path.dirname(self.storage_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        try:
            with open(self.storage_path, "w") as f:
                json.dump(payload, f, indent=4)
        except Exception as e:
            logger.error(f"North Star Persistence Fault: {e}")
            raise e # Reraise for tests

    def update(self, macro_goal: Optional[str] = None, current_focus: Optional[str] = None, 
               micro_goals: Optional[List[str]] = None, completed_milestones: Optional[List[str]] = None,
               vitality_score: Optional[float] = None):
        """Updates the state with new navigational vectors."""
        if macro_goal: self._state.macro_goal = macro_goal
        if current_focus: self._state.current_focus = current_focus
        if micro_goals is not None: self._state.micro_goals = micro_goals
        if completed_milestones is not None: self._state.completed_milestones = completed_milestones
        if vitality_score is not None: self._state.vitality_score = vitality_score
        self.save()

    async def recalibrate(self):
        """Rule 16: Performs a SOTA audit and updates the North Star's vitality."""
        from tooloo_v4_hub.kernel.governance.sota_benchmarker import get_benchmarker
        bench = get_benchmarker()
        report = await bench.run_full_audit()
        
        self._state.vitality_score = report["svi"]
        
        # Rule-12: Autonomous Pivot logic
        if self._state.vitality_score < 0.85:
            # Shift focus to Hub Health
            self._state.current_focus = "CRITICAL: Sovereign Hub Restoration (Ouroboros Pulse)"
            logger.warning(f"Vitality Degraded: {self._state.vitality_score}. Steering Hub toward internal Purity.")
        
        self.save()
        return report

    @property
    def state(self) -> NorthStarState:
        return self._state

# Singleton Accessor
_north_star: Optional[SovereignNorthStar] = None

def get_north_star() -> SovereignNorthStar:
    global _north_star
    if _north_star is None:
        _north_star = SovereignNorthStar()
    return _north_star
