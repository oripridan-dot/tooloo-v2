# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining training_camp.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.392900
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import numpy as np
import datetime
import json
import sys
import os
from pathlib import Path

# Add root directory to path so we can import engine
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from engine.evolution import Context6W, EmergenceVector, TribunalAudit
from engine.evolution_sota import SurrogateWorldModel, AdversarialGenerator

def run_training_camp(iterations: int = 120, batch_size: int = 10):
    print(f"--- TOOLOO TRAINING CAMP: Ouroboros Self-Improvement ---")
    print(f"Goal: Minimize Surprise Delta (\u0394) over {iterations} iterations.")
    
    model = SurrogateWorldModel()
    generator = AdversarialGenerator()
    audit = TribunalAudit()
    
    history = []
    
    for i in range(iterations):
        # 1. Generate Synthetic Mission (C + I)
        context, intent = generator.generate_mission(i)
        
        # 2. Prediction (Current World Model E_sim)
        em_pred_val = model.predict(context, intent)
        em_pred = EmergenceVector(
            context_vec=context.vectorize(),
            intent_vec=intent,
            env_matrix=np.ones(6), # placeholder
            val=em_pred_val
        )
        
        # 3. Reality (Ground Truth E_actual)
        engram_vec = context.vectorize() + intent
        em_actual_val = generator.ground_truth_environment(engram_vec, complexity=0.3)
        em_actual = EmergenceVector(
            context_vec=context.vectorize(),
            intent_vec=intent,
            env_matrix=np.ones(6), # placeholder
            val=em_actual_val
        )
        
        # 4. Measure Surprise (\u0394)
        delta = audit.calculate_delta(em_pred, em_actual)
        history.append(delta)
        
        # 5. Train (Batch Update)
        # For simplicity, we train on each sample (SGD) with a decaying learning rate
        lr = max(0.005, 0.1 * (0.98 ** i))
        loss = model.train_batch([(context, intent)], [em_actual_val], lr=lr)
        
        if (i + 1) % batch_size == 0:
            avg_delta = np.mean(history[-batch_size:])
            progress = (i + 1) / iterations * 100
            print(f"Iter {i+1:3d} [{progress:3.0f}%] | Avg \u0394: {avg_delta:.6f} | Loss: {loss:.6f}")

    # Final Verification
    print(f"\n--- TRAINING COMPLETE ---")
    initial_delta = np.mean(history[:batch_size])
    final_delta = np.mean(history[-batch_size:])
    improvement = (initial_delta - final_delta) / initial_delta * 100
    
    print(f"Initial Avg \u0394: {initial_delta:.6f}")
    print(f"Final Avg \u0394:   {final_delta:.6f}")
    print(f"Improvement:      {improvement:.2f}%")
    
    # Save results
    results = {
        "iterations": iterations,
        "history": [float(d) for d in history],
        "initial_delta": initial_delta,
        "final_delta": final_delta,
        "improvement": improvement,
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    os.makedirs("results", exist_ok=True)
    with open("results/training_camp_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    model.save_weights("results/e_sim_weights_sota.json")
    print(f"\nProgress report saved to: results/training_camp_results.json")
    print(f"SOTA World Model weights saved to: results/e_sim_weights_sota.json")

if __name__ == "__main__":
    run_training_camp()
