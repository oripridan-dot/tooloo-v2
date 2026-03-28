# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining test_predictive_loop.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.406672
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import asyncio
import httpx
import json
import numpy as np
import sys
import os
from pathlib import Path
from typing import Any, Dict

# Add root directory to path so we can import engine
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

import engine.evolution
from engine.evolution import Context6W, EmergenceVector, TribunalAudit, EvolutionaryController

API_URL = "https://too-loo-v2-gru3xdvw6a-zf.a.run.app"
MANDATE_TEXT = "Evaluate the current system's memory-efficiency rules in PsycheBank."

async def run_simulation():
    print(f"--- PREDICTIVE-CORRECTION LOOP SIMULATION ---")
    print(f"Goal: {MANDATE_TEXT}")
    
    # 1. Define Prediction (Planner's World Model)
    # C + I
    context_pred = Context6W(
        what="EVALUATE_MEMORY_RULES",
        when="2026-03-27T00:00:00Z",
        where="too-loo-v2-me-west1",
        who="too-loo-v2-planner",
        how="SYMBOLIC_SCAN",
        why="L1_MANDATE_STABILIZATION"
    )
    # Intent Vector (e.g., Target confidence 0.95, Low risk)
    intent_vec = np.array([0.95, 0.05, 0.1, 0.0, 0.0, 0.0])
    # E_sim (Idealized: Efficient tool use, Low latency)
    e_sim = np.array([1.0, 0.9, 1.0, 1.0, 1.0, 0.8])
    
    em_pred = EmergenceVector.synthesize(context_pred, intent_vec, e_sim)
    print(f"\n[PREDICTION] EM_pred generated.")
    
    # 2. Execute Reality (Concrete Forward Pass)
    print(f"\n[REALITY] Executing mandate via Cloud Run API...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_URL}/v2/mandate",
            json={"text": MANDATE_TEXT}
        )
        
    if response.status_code != 200:
        print(f"Execution failed: {response.status_code} - {response.text}")
        return

    res_data = response.json()
    print(f"[REALITY] Execution successful. Latency: {res_data.get('latency_ms')}ms")
    
    # 3. Vectorize Reality (EM_actual)
    # We extract real context from the result
    route = res_data.get("route", {})
    refinement = res_data.get("refinement", {})
    
    context_actual = Context6W(
        what=route.get("intent", "UNKNOWN"),
        when=route.get("ts", "NOW"),
        where="cloud-run-me-west1",
        who="too-loo-v2-api",
        how="HYBRID_DAG_EXEC",
        why=res_data.get("mandate_id", "m-unknown")
    )
    # Intent Met (Confidence > 0.01)
    intent_met = route.get("confidence", 0) > 0.01
    # Actual Reality vector (Derived from real latency and refinement pass rate)
    lat_normalized = min(1.0, res_data.get("latency_ms", 10000) / 10000.0)
    pass_rate = refinement.get("success_rate", 0)
    actual_vec = np.array([pass_rate, lat_normalized, 0.5, 0.5, 0.5, 0.5])
    
    em_actual = EmergenceVector.synthesize(context_actual, actual_vec, e_sim)
    print(f"[REALITY] EM_actual generated.")

    # 4. Gap Detection (Tribunal Audit)
    delta = TribunalAudit.calculate_delta(em_pred, em_actual)
    print(f"\n[AUDIT] Gap Detected: Δ = {delta:.4f}")
    
    # 5. Evolutionary Decider
    controller = EvolutionaryController(surprise_threshold=0.1)
    ev_result = controller.evaluate_outcome(delta, intent_met)
    
    print(f"\n--- RESULTS ---")
    print(f"Verdict: {ev_result['verdict']}")
    print(f"Pathway: {ev_result['pathway']}")
    print(f"Reason:  {ev_result['reason']}")
    print(f"Action:  {ev_result['action']}")
    
    # Final Output as JSON for details
    final_report = {
        "mandate": MANDATE_TEXT,
        "em_pred": em_pred.to_dict(),
        "em_actual": em_actual.to_dict(),
        "delta": delta,
        "evolution": ev_result
    }
    
    with open("results/predictive_loop_report.json", "w") as f:
        json.dump(final_report, f, indent=2)
    print(f"\nDetailed report saved to: results/predictive_loop_report.json")

if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    asyncio.run(run_simulation())
