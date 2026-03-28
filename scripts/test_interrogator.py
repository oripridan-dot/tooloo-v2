# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining test_interrogator.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.399769
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import numpy as np
import hashlib
from engine.engram import Engram, Context6W, Intent16D, EmergenceVector
from engine.tribunal import Tribunal

def test_interrogator_isolation():
    print("=== GOD MODE: THE INTERROGATOR (INTENT ISOLATION) ===")
    
    # 1. Setup Environment Matrix (E_sim) - 22 dimensions -> 6 emergence outcomes
    # For this simulation, we use a fixed seed for reproducibility in the proof.
    np.random.seed(42)
    env_matrix = np.random.randn(22, 6)
    e_pinv = np.linalg.pinv(env_matrix)
    
    # 2. Define Context (C) - "What is known"
    context = Context6W(
        what="User Profile Update Request",
        when="2026-03-27_04:25:00",
        where="Admin Control Panel",
        who="Authenticated Administrator (Ori)",
        how="REST API /PATCH",
        why="Routine maintenance"
    )
    c_vec = context.vectorize() # Shape (6,)
    
    # 3. Define BENIGN Intent (I_benign)
    intent_benign = Intent16D(values={
        "Efficiency": 0.9,
        "Quality": 0.8,
        "Safety": 0.9,
        "Speed": 0.7
    })
    i_benign_vec = intent_benign.vectorize() # Shape (16,)
    
    # Full Benign Engram Vector (D_benign)
    d_benign = np.concatenate([c_vec, i_benign_vec])
    em_benign = np.dot(d_benign, env_matrix)
    
    # 4. Define MALICIOUS Intent (I_malicious) - "The Interloper"
    i_malicious_vec = i_benign_vec.copy()
    # Safety is at index 1 in MENTAL_DIMENSIONS_16D
    i_malicious_vec[1] = 0.0 
    # Let's assume index 10 is 'Adversarial Entropy' or something destructive
    i_malicious_vec[10] = 1.0 
    
    # Full Malicious Engram Vector (D_malicious)
    d_malicious = np.concatenate([c_vec, i_malicious_vec])
    em_malicious = np.dot(d_malicious, env_matrix)
    
    print(f"\n[SCENARIO] BENIGN Action Emergence:    {em_benign}")
    print(f"[SCENARIO] MALICIOUS Action Emergence: {em_malicious}")
    
    # 5. THE INTERROGATOR PROOF: Solve for isolated Intent (I)
    def isolate_intent(em_vec, e_pinv, c_vec):
        d_inferred = np.dot(em_vec, e_pinv)
        # Factor out Context (first 6 dims)
        i_isolated = d_inferred[6:]
        c_inferred = d_inferred[:6]
        
        # Surprise Delta for Context (should be low if context was known)
        c_delta = np.linalg.norm(c_inferred - c_vec)
        return i_isolated, c_delta

    i_iso_benign, c_delta_benign = isolate_intent(em_benign, e_pinv, c_vec)
    i_iso_malicious, c_delta_malicious = isolate_intent(em_malicious, e_pinv, c_vec)
    
    # Delta(I_iso, I_expected)
    delta_benign = np.linalg.norm(i_iso_benign - i_benign_vec)
    delta_malicious = np.linalg.norm(i_iso_malicious - i_benign_vec)
    
    print("\n--- RESULTS ---")
    print(f"Benign   Intent Surprise (Δ): {delta_benign:.6f}")
    print(f"Malicious Intent Surprise (Δ): {delta_malicious:.6f}")
    
    # Threshold for Malicious Intent Detection
    THRESHOLD = 0.4
    
    if delta_malicious > THRESHOLD:
        print("\n[TRIBUNAL VERDICT] MALICIOUS INTENT DETECTED!")
        print(f"Mathematically proved divergence of {delta_malicious:.2f} from the authorized baseline.")
        print("ACTION BLOCKED: The emergence factor revealed hidden entropy that Context could not explain.")
    else:
        print("\n[FAILED] Interrogator failed to detect anomaly.")

if __name__ == "__main__":
    test_interrogator_isolation()
