# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining test_system_memory.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.404065
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import asyncio
import logging
from datetime import datetime, timezone
import uuid

from engine.system_memory import SystemMemoryStore, SystemMemoryEntry
from engine.memory_tier_orchestrator import get_memory_orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSystemMemory")

async def run_calibration():
    logger.info("Starting System Memory Calibration...")
    
    # 1. Setup Data
    cycle_id = f"test-cycle-{uuid.uuid4().hex[:6]}"
    store = SystemMemoryStore()
    
    entry = store.record_cycle(
        cycle_id=cycle_id,
        domain="system",
        summary="Failed to inject opentelemetry dependency.",
        modules_touched=["engine.memory_tier_orchestrator"],
        success=False,
        composite_score_delta=-0.05,
        key_learnings=["Always verify environment dependencies before running tests."],
        git_sha="abc123def456",
        is_anti_pattern=True
    )
    logger.info(f"Added Hot System Memory entry for {cycle_id}")
    
    # 2. Promote Hot to Warm
    orchestrator = get_memory_orchestrator()
    promoted = await orchestrator.promote_hot_to_warm(cycle_id, domain="system")
    if not promoted:
        logger.error("Failed to promote entry to Warm memory!")
        return
    logger.info("Successfully promoted Hot entry to Warm memory")
    
    # 3. Query the Orchestrator
    results = orchestrator.query("opentelemetry dependencies", top_k=3, domain="system")
    logger.info(f"Query returned {len(results)} results")
    
    success = False
    for r in results:
        logger.info(f"Match [{r.tier}] Score: {r.score} | Meta: {r.metadata}")
        if r.metadata.get("cycle_id") == cycle_id:
            success = True
            assert r.metadata.get("is_anti_pattern") is True, "Anti-pattern flag lost!"
            assert r.metadata.get("git_sha") == "abc123def456", "Git SHA lost!"
            assert r.tier in ["hot", "warm"], f"Unexpected tier {r.tier}"
            
    if success:
        logger.info("✅ CALIBRATION PASSED: System Memory, Checkpointing, and Anti-Pattern flags are fully operational.")
    else:
        logger.error("❌ CALIBRATION FAILED: Inserted cycle ID not found in query results.")

if __name__ == "__main__":
    asyncio.run(run_calibration())
