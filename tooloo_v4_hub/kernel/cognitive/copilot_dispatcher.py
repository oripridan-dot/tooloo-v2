"""
# 6W_STAMP
# WHO: Buddy (Sovereign Co-Architect) — Autonomous Co-pilot Mandate
# WHAT: COPILOT_DISPATCHER | Version: 2.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/copilot_dispatcher.py
# WHY: Rule 18 (Cloud-Native) + Rule 3 — Buddy triggers real executions via Cloud Hub
# HOW: Parses MANDATE/ACTION/FORGE_SKILL/PLAN tokens; POSTs to Cloud Hub /buddy/mandate.
#      Falls back to local orchestrator if cloud is unreachable.
# PURITY: 1.00
# ==========================================================
"""

import asyncio
import logging
import os
import re
import random
from typing import List, Dict, Any, Optional

logger = logging.getLogger("CopilotDispatcher")

# Mandate token patterns
_MANDATE_RE = re.compile(r"(?:MANDATE|ACTION):\s*(.+?)(?:\n|$)")
_PLAN_RE = re.compile(r"PLAN:\s*(.+?)(?:\n|$)")
_FORGE_RE = re.compile(r"FORGE_SKILL[:\s]+([^\n|]+?)(?:\s*\|\s*(.+))?(?:\n|$)", re.IGNORECASE)

# Cloud Hub — Rule 18: The Mac is the Portal. Cloud is the Brain.
CLOUD_HUB_URL = os.getenv(
    "CLOUD_HUB_URL",
    "https://tooloo-v4-hub-gru3xdvw6a-uc.a.run.app"
)
SOVEREIGN_KEY = os.getenv("SOVEREIGN_MASTER_KEY", "SOVEREIGN_HUB_2026_V3")


class CopilotDispatcher:
    """
    Buddy's autonomous execution arm.

    When Buddy emits MANDATE/ACTION/FORGE_SKILL/PLAN tokens in a response,
    this dispatcher fires them to the Sovereign Cloud Hub for real execution.

    Architecture (Rule 18):
      Buddy text → CopilotDispatcher → POST /buddy/mandate (Cloud Hub)
                                     ↳ fallback: local Orchestrator
    """

    def __init__(self):
        self._dispatched: List[str] = []  # In-session dedup audit trail

    async def dispatch_from_response(self, response: str, message: str) -> List[Dict[str, Any]]:
        """
        Parse Buddy's response and dispatch all directives to the Cloud Hub.
        Returns a list of dispatch receipts.
        """
        receipts = []

        # 1. FORGE_SKILL (highest priority — creates new capability)
        for match in _FORGE_RE.finditer(response):
            skill_name = match.group(1).strip().replace(" ", "_").lower()
            intent = (match.group(2) or match.group(1)).strip()
            goal = f"FORGE_SKILL: {skill_name} — {intent}"
            if goal not in self._dispatched:
                receipt = await self._call_cloud_hub(goal, intent, message)
                receipts.append(receipt)

        # 2. MANDATE / ACTION (direct execution goals)
        for match in _MANDATE_RE.finditer(response):
            goal = match.group(1).strip()
            if goal and goal not in self._dispatched:
                receipt = await self._call_cloud_hub(goal, goal, message)
                receipts.append(receipt)

        # 3. PLAN (collaborative path selection in Portal)
        plan_matches = _PLAN_RE.findall(response)
        if plan_matches:
            receipt = await self._dispatch_plan(plan_matches)
            receipts.append(receipt)

        return receipts

    async def _call_cloud_hub(self, goal: str, rationale: str, origin: str) -> Dict[str, Any]:
        """
        Rule 18: POSTs a mandate to the Sovereign Cloud Hub /buddy/mandate.
        Falls back to local Orchestrator if cloud is unreachable.
        """
        self._dispatched.append(goal)
        mission_id = f"MSN_BUDDY_{random.randint(1000, 9999)}"

        # Broadcast mission_start to Portal immediately (Rule 7: instant feedback)
        await self._broadcast({
            "type": "mission_start",
            "mission_id": mission_id,
            "goal": goal
        })

        # Try Cloud Hub first (Rule 18)
        try:
            import httpx
            url = f"{CLOUD_HUB_URL}/buddy/mandate"
            payload = {
                "goal": goal,
                "rationale": rationale,
                "context": {
                    "origin_message": origin[:300],
                    "initiator": "BUDDY",
                    "mission_id": mission_id
                }
            }
            logger.info(f"CopilotDispatcher → Cloud Hub: {goal[:80]} [{mission_id}]")

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"X-Sovereign-Key": SOVEREIGN_KEY}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(f"Cloud Hub accepted mandate: {data.get('status')} [{mission_id}]")
                    await self._broadcast({
                        "type": "mission_telemetry",
                        "goal": goal,
                        "entry": {
                            "level": "PROCESS",
                            "message": f"Cloud Hub executing: {goal[:60]}",
                            "timestamp": __import__("time").time()
                        }
                    })
                    return {"type": "cloud_mandate", "goal": goal, "mission_id": mission_id, "status": "dispatched"}
                else:
                    logger.warning(f"Cloud Hub returned {resp.status_code}. Falling back to local.")
        except Exception as e:
            logger.warning(f"Cloud Hub unreachable ({e}). Falling back to local orchestrator.")

        # Fallback: local Orchestrator
        return await self._dispatch_local(goal, origin, mission_id)

    async def _dispatch_local(self, goal: str, origin: str, mission_id: str) -> Dict[str, Any]:
        """Local fallback when cloud is unreachable."""
        logger.info(f"CopilotDispatcher [LOCAL]: {goal[:80]} [{mission_id}]")
        try:
            from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
            orchestrator = get_orchestrator()
            asyncio.create_task(orchestrator.execute_goal(
                goal,
                {"rationale": "Buddy Co-pilot (local fallback)", "initiator": "BUDDY", "origin": origin[:200]},
                mode="DIRECT"
            ))
            return {"type": "local_mandate", "goal": goal, "mission_id": mission_id, "status": "dispatched_locally"}
        except Exception as e:
            logger.error(f"CopilotDispatcher: Local fallback fault: {e}")
            return {"type": "error", "goal": goal, "error": str(e)}

    async def _dispatch_plan(self, plan_goals: List[str]) -> Dict[str, Any]:
        """Emits Path Selection Cards to the Portal for collaborative planning."""
        paths = [
            {"id": "purity_sprint", "label": "Purity Sprint (Stamp Audit)", "icon": "shield",
             "summary": "Enforce 6W compliance across all unstamped nodes"},
            {"id": "feature_forge", "label": "Feature Forge (Expansion)", "icon": "hammer",
             "summary": "Build the capability Buddy identified"},
            {"id": "self_heal", "label": "Self-Healing (Refactor)", "icon": "heart",
             "summary": "Stabilize and refactor the flagged area"},
        ]
        await self._broadcast({
            "type": "path_selection",
            "header": "Buddy Suggests Architectural Paths",
            "paths": paths
        })
        logger.info(f"CopilotDispatcher: Path Selection Cards broadcast ({len(plan_goals)} plans)")
        return {"type": "plan", "plans": plan_goals}

    async def _broadcast(self, payload: Dict[str, Any]):
        """Sends a real-time event to the Portal via the unified transmission layer."""
        try:
            from tooloo_v4_hub.kernel.cognitive.transmission import broadcast_buddy
            await broadcast_buddy(payload)
        except Exception as e:
            logger.debug(f"CopilotDispatcher: Broadcast fault (no active Portal): {e}")


_dispatcher: Optional[CopilotDispatcher] = None


def get_copilot_dispatcher() -> CopilotDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = CopilotDispatcher()
    return _dispatcher
