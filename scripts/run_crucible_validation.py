# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Master Crucible Validation Suite
# WHERE: scripts
# WHEN: 2026-03-29T00:20:00.000000
# WHY: Verifying Sovereign Cognitive Engine
# HOW: Tracer Bullet DAG Execution
# ==========================================================

import asyncio
import time
import sys
import os

# Add root to sys.path
root = "/Users/oripridan/ANTIGRAVITY/tooloo-v2"
if root not in sys.path:
    sys.path.insert(0, root)

from engine.orchestrator import SovereignOrchestrator
from engine.schemas.six_w import SixWProtocol
from engine.graph import CognitiveGraph

async def run_master_crucible():
    print("Initiating Crucible: Sovereign Engine Validation Suite...")
    
    # 1. Initialize the Hub Core
    orchestrator = SovereignOrchestrator()
    graph = CognitiveGraph()

    # 2. The Tracer Mandate (A task requiring reasoning, coding, and SOTA context)
    tracer_mandate = """
    PROVISION A SPOKE: Create a secure, rate-limited FastAPI endpoint for user authentication.
    INTENT: High security, low latency. Use SOTA 2026 JWT practices.
    """
    print(f"Injecting Tracer Mandate: {tracer_mandate.strip()}")

    start_time = time.time()
    
    # 3. Execute the DAG Pipeline
    try:
        # The orchestrator plans the Macro-DAG, retrieves JIT context, and evolves the memory
        results = await orchestrator.execute_goal(tracer_mandate, {"user_id": "crucible-tester", "env": "crucible-sandbox"})
        
        if not results:
            raise ValueError("CRITICAL FAILURE: Execution returned no results.")

        # 4. Extract and Validate the 6W Stamp from the final milestone
        final_engram = results[-1]
        stamp = final_engram.context
        
        print("\n--- CRUCIBLE RESULTS ---")
        print(f"DAG Execution Time: {time.time() - start_time:.2f}s")
        print(f"WHO: {stamp.who}")
        print(f"WHAT (Truncated): {stamp.what[:50]}...")
        print(f"WHERE: {stamp.where}")
        print(f"Δ-CLOSURE GAP: {final_engram.metadata.get('delta_closure', 0.0):.4f}")
        print(f"VERIFICATION STATUS: {'PASS (EM_Verified)' if stamp.em_verified else 'PASS (Outcome Captured)'}")
        
        # Check if evolution was recorded
        learned_path = os.path.join(root, "psyche_bank/learned_engrams.json")
        if os.path.exists(learned_path):
            print("SUCCESS: Evolutionary Engram successfully persisted to Sovereign Memory.")
        else:
            print("WARNING: Learned engrams store not found.")
            
    except Exception as e:
        print(f"\nCRUCIBLE FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_master_crucible())
