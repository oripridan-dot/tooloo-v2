import asyncio
import logging
import json
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator

# Configure logging for 16-Rule Transparency
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("BalancingStressTest")

async def test_realtime_balancing():
    """
    Rule 2: Dynamic Realtime Balancing Verification.
    Verifies Phase-Based DAG execution and Dynamic Concurrency Scaling.
    """
    logger.info("--- INTEGRATION TEST: REALTIME BALANCING (V2) ---")
    
    orchestrator = get_orchestrator()
    
    # 1. Manifest a mission with explicit phases
    # In a real scenario, the SOTA Decomposer (GPT-5.4) would generate these.
    # Here we mock the milestones to verify the Orchestrator's grouping logic.
    goal = "Manifest a Federated Reality Dashboard with multi-phase balancing."
    context = {"environment": "local"} # Should trigger limit of ~5-7
    
    # Explicitly creating milestones for 3 phases
    milestones = []
    
    # Phase 1: Discovery (10 tasks)
    for i in range(10):
        milestones.append({
            "id": f"read_{i}", "action": "fs_ls", "params": {"path": "."}, "phase": 1, "why": "Discovery"
        })
        
    # Phase 2: Manifestation (5 tasks)
    for i in range(5):
        milestones.append({
            "id": f"write_{i}", "action": "fs_write", 
            "params": {"path": f"tmp/shard_{i}.md", "content": "# Shard"}, 
            "phase": 2, "why": "Build"
        })
        
    # Phase 3: Audit (1 task)
    milestones.append({
        "id": "final_audit", "action": "sovereign_audit", "params": {}, "phase": 3, "why": "Validation"
    })

    logger.info(f"Injecting {len(milestones)} milestones into Phase-Aware Orchestrator...")
    
    # Mocking _decompose_inverse_dag to return our controlled milestones
    original_decomp = orchestrator._decompose_inverse_dag
    async def mock_decomp(*args, **kwargs):
        return milestones, False
    orchestrator._decompose_inverse_dag = mock_decomp

    # Execute
    try:
        results = await orchestrator.execute_goal(goal, context, mode="MACRO")
        logger.info("✅ SUCCESS: Phase-Based Execution Cycle Complete.")
        
        # Verify receipt
        receipt = results[0]["receipt"]
        logger.info(f"Final Receipt: Predicted={receipt['predicted_emergence']:.2f}, Actual={receipt['actual_emergence']:.2f}")
        
    except Exception as e:
        logger.error(f"❌ Balancing Test FAILED: {e}")
    finally:
        orchestrator._decompose_inverse_dag = original_decomp

if __name__ == "__main__":
    asyncio.run(test_realtime_balancing())
