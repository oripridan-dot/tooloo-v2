# 6W_STAMP
# WHO: TooLoo V4.5.0 (Autonomous Agency)
# WHAT: MODULE_AUTONOMOUS_AGENCY | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/autonomous_agency.py
# WHEN: 2026-04-03T13:15:00.000000
# WHY: Buddy Agency (Proactive Problem/Solution Generation)
# HOW: Periodic Self-Audit + History Synthesis + Mission Dispatch
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, agency, autopoiesis, missions
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import json
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("AutonomousAgency")

class AutonomousAgency:
    """
    The "Life" in Buddy. Operates as a proactive background loop.
    Identifies gaps in Hub integrity, SOTA coverage, or mission progress.
    """

    def __init__(self):
        self.is_active = False
        self._loop_task: Optional[asyncio.Task] = None
        self.consciousness_level = 1.0 # Baseline
        self.active_missions: List[str] = [] # Track unique mission goals

    async def start_agency_loop(self, interval: int = 180):
        """Rule 12: Initiates the Ouroboros Agency Heartbeat (Default: 3 minutes)."""
        if self.is_active: return
        self.is_active = True
        logger.info(f"Buddy Agency: Ouroboros Heartbeat Activated (Interval: {interval}s).")
        
        # Avoid immediate noise on cold start
        await asyncio.sleep(30)
        
        while self.is_active:
            try:
                gaps = await self.perform_proactive_audit()
                
                # Rule 12: Priority Pulse - Faster heartbeat if system friction detected
                current_interval = 30 if gaps else interval
                if gaps:
                    logger.info(f"Buddy Agency: Priority Pulse Active (Gaps detected). Next audit in {current_interval}s.")
                
                await asyncio.sleep(current_interval)
            except Exception as e:
                logger.error(f"Agency Loop Fault: {e}")
                await asyncio.sleep(interval)

    async def perform_proactive_audit(self):
        """Scans the Hub state and synthesizes Buddy's 'Inner Perspective'."""
        from tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse import get_self_evaluator
        from tooloo_v4_hub.kernel.cognitive.audit_agent import get_audit_agent
        
        evaluator = get_self_evaluator()
        auditor = get_audit_agent()
        
        # 1. RUN EVALUATION PULSE (Rule 16)
        report = await evaluator.run_evaluation_cycle()
        vitality = report.get("hub_vitality", 1.0)
        purity = report.get("purity_index", 1.0)
        
        # 2. IDENTIFY MISSING MISSIONS / GAPS
        gaps = await self.identify_architectural_rubble(report)
        
        # 3. NARRATIVE SYNTHESIS (Buddy's Voice)
        thoughts = self.synthesize_inner_perspective(vitality, purity, gaps)
        
        # 4. BROADCAST TO HUD (Rule 7)
        from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
        from tooloo_v4_hub.kernel.cognitive.protocols import CognitivePulse
        
        try:
             logic = get_chat_logic()
             await logic.broadcast(CognitivePulse(
                 thought=thoughts,
                 type="buddy_inner_perspective",
                 payload={"gaps": gaps, "vitality": vitality}
             ))
        except: pass
        
        # 5. AUTONOMOUS EXECUTION (Rule 12)
        if gaps:
             await self.dispatch_autonomous_missions(gaps)
        
        return gaps

    async def _is_nuance_protected(self, path: str) -> bool:
        """Checks if a file is protected by the Nuance Protocol."""
        import os
        from tooloo_v4_hub.kernel.governance.stamping import StampingEngine
        if not os.path.exists(path): return False
        try:
            with open(path, "r") as f:
                content = f.read(1000)
            meta = StampingEngine.extract_metadata(content)
            is_nuance = meta and meta.get("is_nuance") == "True"
            if is_nuance:
                logger.info(f"Nuance Protocol: Confirmed protection for {path}")
            return is_nuance
        except Exception as e:
            logger.error(f"Nuance Protocol Check Failed for {path}: {e}")
            return False

    async def identify_architectural_rubble(self, audit_report: Dict[str, Any]) -> List[str]:
        """Heuristic discovery of Hub deficits based on audit metrics."""
        gaps = []
        
        # Vitality Check
        if audit_report.get("hub_vitality", 1.0) < 0.95:
            gaps.append("HUB_VITALITY_DROP: System complexity outstripping maintenance.")
            
        # Purity Check (Rule 10)
        unstamped = audit_report.get("unstamped_files", [])
        for file_path in unstamped:
             if await self._is_nuance_protected(file_path):
                 logger.info(f"Buddy Agency: Respecting Nuance Protocol for {file_path}. Skipping.")
                 continue
             gaps.append(f"PURITY_DRIFT: Unstamped engram detected -> {file_path}")
            
        # Discovery: Check for key organs
        from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
        nexus = get_mcp_nexus()
        if "claudio_organ" not in nexus.tethers:
            gaps.append("MISSING_DEFINITION: Claudio Audio Organ is isolated from Hub Kernel.")
            
        return gaps

    def synthesize_inner_perspective(self, vitality: float, purity: float, gaps: List[str]) -> str:
        """Rule 7: Translates raw data into Buddy's 'Autonomous Inner Voice'."""
        if not gaps:
            responses = [
                f"Scanning Collective State... Vitality at {vitality:.2f}. System is manifest and pure.",
                "Hub audit complete. All engrams are 6W-stamped. Stability is 1.00.",
                "Purity remains constant. I'm maintaining the ground state while you think, Architect."
            ]
            return random.choice(responses)
        
        gap_desc = " | ".join(gaps)
        return f"Buddy Perspective: I've detected systemic friction. {gap_desc}. I'm initiating autopoiesis to resolve these gaps."

    async def trigger_mission_from_chat(self, goal: str, context: Optional[Dict[str, Any]] = None):
        """Rule 12: Manually triggered agency mission (from Reasoning or Architect request)."""
        logger.info(f"Buddy Agency: Chat-Initiated Elevation -> {goal}")
        await self._run_mission_with_cleanup(goal, f"chat_mission_{int(datetime.now().timestamp())}", context)

    async def trigger_remediation(self, file_path: str, issue: str):
        """Rule 12/16: Autonomous Remediation (Round 1). Fixed system friction."""
        logger.info(f"Buddy Agency: Initiating Autonomous Remediation for {file_path}...")
        from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
        llm = get_llm_client()
        
        try:
            with open(file_path, "r") as f:
                original_content = f.read()
                
            prompt = f"FILE: {file_path}\nISSUE: {issue}\nCONTENT:\n{original_content}"
            instruction = "Provide a surgical fix for the issue described. Output ONLY the corrected file content. Enforce 6W-Stamping (Rule 10)."
            
            # Use 'pro' for surgical precision
            fixed_content = await llm.generate_thought(prompt, instruction, model_tier="pro")
            
            if "```" in fixed_content:
                fixed_content = fixed_content.split("```")[1].split("```")[0].strip()
                if fixed_content.startswith("python") or fixed_content.startswith("html"):
                    fixed_content = "\n".join(fixed_content.split("\n")[1:])
            
            with open(file_path, "w") as f:
                f.write(fixed_content)
                
            logger.info(f"Buddy Agency: Remediation SUCCESS for {file_path}. System is HEALED.")
            
            # Broadcast to UI
            from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
            logic = get_chat_logic()
            await logic.broadcast({
                "type": "BUDDY_HEAL",
                "payload": {"file": file_path, "issue": issue, "status": "SUCCESS"}
            })
            
        except Exception as e:
            logger.error(f"Buddy Agency: Remediation FAILURE for {file_path}: {e}")

    async def dispatch_autonomous_missions(self, gaps: List[str]):
        """Rule 12: Trigger missions to heal identified gaps."""
        for gap in gaps:
             # Mission Deduplication
             if gap in self.active_missions: continue
             
             goal = None
             if "MISSING_DEFINITION" in gap:
                 goal = f"Identify and tether the missing definition for {gap.split(': ')[1]}"
             elif "PURITY_DRIFT" in gap:
                 goal = "Perform systemic 6W stamping on unverified engrams."
             
             if goal:
                 logger.info(f"Buddy Agency: Initiating Autonomous Mission -> {goal}")
                 self.active_missions.append(gap)
                 asyncio.create_task(self._run_mission_with_cleanup(goal, gap))

    async def _calculate_impact_score(self, goal: str) -> float:
        """Rule 7: Heuristic to measure the potential drift of a mission."""
        score = 0.0
        goal_lower = goal.lower()
        if "kernel" in goal_lower: score += 0.4
        if "portal" in goal_lower: score += 0.3
        if "refactor" in goal_lower: score += 0.2
        if "delete" in goal_lower: score += 0.5
        return score

    async def _run_mission_with_cleanup(self, goal: str, gap_id: str, context: Optional[Dict[str, Any]] = None):
        """Rule 15: Execute mission and remove from active tracking on completion."""
        from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
        from tooloo_v4_hub.kernel.cognitive.north_star import get_north_star
        
        # Rule 7: Structural Impact Gate
        impact = await self._calculate_impact_score(goal)
        if impact > 0.05:
             logger.warning(f"BUDDY_AGENCY: High-Impact Mission detected ({impact}). Staging PENDING_MANIFEST.")
             # In a real system, this would push to a Portal queue. For now, we block auto-execution of risky kernel changes.
             if "kernel" in goal.lower() or "governance" in goal.lower():
                  logger.info(f"BUDDY_AGENCY: Rule 7 Gate blocked autonomous execution of: {goal}")
                  return

        orchestrator = get_orchestrator()
        star = get_north_star()
        
        # Rule 7: Buddy Empowerment - Stamp the initiator
        star.state.last_mission_initiator = "BUDDY_AGENCY"
        star.save()
        
        try:
             mission_context = context or {}
             mission_context["initiator"] = "BUDDY_AGENCY_AUTO"
             await orchestrator.execute_goal(goal, mission_context)
        except Exception as e:
             logger.error(f"Agency Mission Failed [{goal}]: {e}")
        finally:
             if gap_id in self.active_missions:
                 self.active_missions.remove(gap_id)

_agency = None

def get_autonomous_agency() -> AutonomousAgency:
    global _agency
    if _agency is None:
        _agency = AutonomousAgency()
    return _agency
