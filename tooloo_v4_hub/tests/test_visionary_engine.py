# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TEST_VISIONARY_ENGINE.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/test_visionary_engine.py
# WHEN: 2026-03-31T14:26:13.339716+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: test, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
from tooloo_v4_hub.kernel.orchestrator import get_orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestVisionary")

async def test_inverse_dag_deconstruction():
    logger.info("--- Testing Inverse DAG Deconstruction ---")
    orb = get_orchestrator()
    
    goal = "Build a real-time spectral hardening visualization spoke for the Sovereign Hub."
    context = {"priority": "SOTA"}
    
    # 1. Trigger Deconstruction
    dag = await orb._decompose_inverse_dag(goal, context)
    
    # 2. Assert Parallel Branches
    assert "environment" in dag, "Missing Environment branch"
    assert "context" in dag, "Missing Context branch"
    assert "intent" in dag, "Missing Intent branch"
    
    # 3. Assert Content
    assert any("setup" in str(m).lower() or "sync" in str(m).lower() for m in dag["environment"]), "Env branch lacks setup milestones"
    assert any(any(w in str(m).lower() for w in ["manifest", "ui", "viz", "layer"]) for m in dag["context"]), "Ctx branch lacks UI milestones"
    
    logger.info("✅ Inverse DAG Deconstruction Verified.")

async def test_parallel_dispatch_timing():
    logger.info("--- Testing Parallel Dispatch Timing ---")
    orb = get_orchestrator()
    
    # Timing a simulated parallel execution
    import time
    start = time.time()
    
    results = await orb.execute_goal(
        goal="simulate massive parallel build",
        context={"simulated": True},
        mode="PATHWAY_A"
    )
    
    duration = time.time() - start
    logger.info(f"Parallel Dispatch Duration: {duration:.4f}s")
    
    # In a true parallel world, 3 mock branches (0.1s each) should take ~0.15s
    # (Allowing some overhead for the orchestrator logic)
    assert duration < 1.0, f"Dispatch took too long ({duration:.4f}s). Is it sequential?"
    assert any(r["status"] == "success" for r in results), "Failed to execute parallel branches"

if __name__ == "__main__":
    asyncio.run(test_inverse_dag_deconstruction())
    print("\n")
    asyncio.run(test_parallel_dispatch_timing())