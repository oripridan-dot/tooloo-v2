# WHO: TooLoo V4.2.0 (Sovereign Architect)
# WHAT: MODULE_ORCHESTRATOR | Version: 2.1.0
# WHERE: tooloo_v4_hub/kernel/orchestrator.py
# WHY: Primitives 1 & 8: Simplicity, 2-Level Verification, and Accountability
# HOW: Deterministic Execution via LivingMap -> MegaDAG -> Crucible
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import gc
import json

from tooloo_v4_hub.kernel.governance.stamping import StampingEngine, SixWProtocol
from tooloo_v4_hub.kernel.cognitive.crucible_validator import get_crucible_validator
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.kernel.cognitive.mission_manager import get_mission_manager
from tooloo_v4_hub.kernel.cognitive.recovery_pulse import get_recovery_pulse
from tooloo_v4_hub.kernel.mega_dag import get_mega_dag

logger = logging.getLogger("SovereignOrchestrator")

class BuddyDelegator:
    """Round 5: Sovereign Delegation. Empowers Buddy to spawn specialist sub-missions."""
    def __init__(self, orchestrator: "SovereignOrchestrator"):
        self.orchestrator = orchestrator

    async def delegate_sub_mission(self, label: str, goal: str, context: Dict[str, Any]):
        """Delegates a specific sub-task to a specialist reasoning node or organ."""
        logger.info(f"Buddy Delegation [{label}]: Initiating Sub-Mission -> {goal}")
        context["delegator_label"] = label
        context["parent_mission"] = True
        
        # Rule 12: Recursive Execution
        results = await self.orchestrator.execute_goal(goal, context, mode="DIRECT")
        return results

class SovereignOrchestrator:
    """
    The Deterministic Orchestrator for TooLoo V4.2.0.
    Enforces practical purpose execution without simulated mathematical abstraction.
    """

    def __init__(self):
        from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
        self._nexus = get_mcp_nexus()
        self._parallel_limit: Optional[asyncio.Semaphore] = None
        self.delegator = BuddyDelegator(self)
        logger.info("Sovereign Orchestrator V4.2.0 (Deterministic / High-Agency) Awakened.")

    async def execute_goal(self, goal: str, context: Dict[str, Any], mode: str = "DIRECT") -> List[Dict[str, Any]]:
        logger.info(f"Orchestrator V4.2: Initiating Sovereign Mission -> {goal}")
        
        # 0. MISSION INITIALIZATION
        mm = get_mission_manager()
        m_id = mm.create_mission(goal)
        
        # Rule 1: Load Project Constitution
        from tooloo_v4_hub.kernel.governance.knowledge_gateway import get_knowledge_gateway
        gateway = get_knowledge_gateway()
        sovereign_rules = gateway.load_sovereign_md()
        
        await mm.stream_telemetry(m_id, f"MISSION_INITIALIZED", level="START", metadata={
            "goal": goal,
            "has_sovereign_md": bool(sovereign_rules)
        })
        
        # Ouroboros Heartbeat
        get_recovery_pulse().update_context(mission=goal)
        
        start_time = time.time()

        # 1. PHASE 0: ECOSYSTEM INVENTORY (Rule 6)
        from tooloo_v4_hub.kernel.governance.living_map import get_living_map
        living_map = get_living_map()
        existing = living_map.query_capabilities(goal)
        
        if existing and mode != "FORCE":
            logger.info(f"Map Query: Reusing component '{existing[0]['id']}' (Alignment: PERFECT).")
            return [{"status": "success", "reused": True, "node": existing[0]["id"]}]
            
        # 1.5 OMNI-DIRECTIONAL MULTI-AGENT HANDOFF (OpenAI Paradigm)
        # Instead of monolithic execution, we route context to specialized agents.
        persona = "GeneralSpecialist"
        goal_lower = goal.lower()
        if "architect" in goal_lower or "design" in goal_lower or "plan" in goal_lower:
            persona = "ArchitectAgent"
        elif "code" in goal_lower or "build" in goal_lower or "implement" in goal_lower:
            persona = "CoderAgent"
        elif "verify" in goal_lower or "test" in goal_lower or "audit" in goal_lower:
            persona = "VerifierAgent"
            
        logger.info(f"Orchestrator V4.2: Handoff -> Routing mission to {persona}")
        await mm.stream_telemetry(m_id, f"AGENT_HANDOFF: Routed to {persona}", level="PROCESS")
        
        # Grounding Injection (Google Cloud Paradigm)
        grounding_data = await gateway.get_dynamic_grounding(goal)
        context["agent_persona"] = persona
        context["dynamic_grounding"] = grounding_data
        
        # 2. OMNI-DIRECTIONAL MEGA DAG (Execution Phase)
        await mm.stream_telemetry(m_id, "STRATEGY: MEGA (V4.2 Matrix Parallel)", level="PROCESS")
        
        # Rule 7: Parallel Optimization (Claude-Style)
        # If goal contains multiple sub-tasks (heuristic), we can potentially parallelize.
        mega = get_mega_dag()
        
        # Enhanced Execution: Split and Execute
        # For now, we use the MegaDAG which handles the DAG structure.
        # We wrap it in a semaphore to prevent over-concurrency (Rule 5).
        if not self._parallel_limit:
            self._parallel_limit = asyncio.Semaphore(5) # max 5 parallel tool flows
            
        async with self._parallel_limit:
            mega_results = await mega.execute_mega_goal(goal, context)
            
        if mega_results.get("status") == "HALTED":
            return [{"status": "halted", "findings": mega_results.get("findings"), "mission_id": m_id}]

        execution_latency = mega_results.get("latency", (time.time() - start_time) * 1000)
        results = mega_results.get("results", [])

        # 3. AUDIT & RECEIPT (Primitive 8: 2-Level Verification)
        crucible = get_crucible_validator()
        audit_result = await crucible.audit_plan(goal, results)
        
        if audit_result.status == "FAIL":
             logger.error(f"CRUCIBLE REJECTION: {audit_result.findings}")
             await mm.stream_telemetry(m_id, "MISSION_FAILED_AUDIT", level="ERROR", metadata={"findings": audit_result.findings})
             return [{"status": "fail", "findings": audit_result.findings, "mission_id": m_id}]
        
        receipt = {
            "strategy": "MEGA_SMD_V4",
            "audit_status": audit_result.status,
            "purity_score": audit_result.purity_score,
            "latency_ms": execution_latency,
            "results_count": len(results)
        }

        # 4. STORE OUTCOME (Real metrics, no simulated deltas)
        from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic
        memory = await get_memory_logic()
        await memory.log_execution_receipt(m_id, receipt)
        
        mm.complete_mission(m_id, results)
        await mm.stream_telemetry(m_id, "MISSION_SUCCESS: Sovereign Hub Evolution Confirmed.", level="END")
        
        # Rule 15: Zero-Footprint Exit
        gc.collect()
        
        return [{"status": "success", "receipt": receipt, "results": results, "mission_id": m_id}]

_orchestrator = None

def get_orchestrator() -> SovereignOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SovereignOrchestrator()
    return _orchestrator