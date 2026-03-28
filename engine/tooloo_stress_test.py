# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining tooloo_stress_test.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.919089
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import os
import sys
import glob
import logging

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.claudio_governor import ClaudioGovernor

# Suppress noisy logs during stress test
logging.basicConfig(level=logging.INFO, format="%(message)s")

def tooloo_stress_test(corpus_dir="./audio_corpus"):
    """TooLoo's automated benchmarking suite for Claudio's algorithms."""
    print("\n[TOOLOO] Initiating Massive Audio Stress Test...\n")
    print("Goal: Enforce Absolute Mathematical Identity (Delta RMS = 0.0) Across All Assets.\n")
    
    test_files = glob.glob(os.path.join(corpus_dir, "*.wav"))
    if not test_files:
        print(f"[ERROR] No test assets found in '{corpus_dir}'. Run tooloo_corpus_scraper.py first.")
        return []
        
    results_log = []
    governor = ClaudioGovernor(tolerance=1e-12) # Tightening for SOTA
    
    for file in test_files:
        basename = os.path.basename(file)
        print(f"[TESTING] Ingesting: {basename}")
        
        # Output to temp for audit
        recon_path = f"/tmp/bench_{basename}"
        
        # TooLoo fires the audio through Claudio's Parallel Pathway logic
        try:
            result = governor.execute_proof_loop(file, recon_path)
            
            delta_rms = result.get('delta_rms', 1.0)
            pathway = result.get('pathway', 'N/A')
            resolution = result.get('resolution', 'N/A')
            
            log_entry = {
                'file': basename,
                'pathway': pathway,
                'resolution': resolution,
                'delta_rms': delta_rms
            }
            results_log.append(log_entry)
            
            if delta_rms <= governor.tolerance:
                marker = f" (via {resolution})" if pathway == "B" else ""
                print(f"✅ PASS: Mathematical Identity Achieved via Pathway {pathway}{marker}")
                print(f"   Delta RMS: {delta_rms:.16f}\n")
            else:
                print(f"❌ FAIL: Delta detected ({delta_rms:.16f}). Engine adjustment required.")
                print(f"   Winning Pathway: {pathway} ({resolution})\n")
                
        except Exception as e:
            print(f"🚨 CRITICAL ERROR processing {basename}: {e}\n")
            
    # Summary Report
    pass_count = sum(1 for r in results_log if r['delta_rms'] <= governor.tolerance)
    print(f"--- STRESS TEST SUMMARY ---")
    print(f"Total Assets Tested: {len(test_files)}")
    print(f"Total Passed:        {pass_count}")
    print(f"Total Failed:        {len(test_files) - pass_count}")
    print(f"Survival Rate:       {(pass_count / len(test_files)) * 100:.2f}%")
    
    return results_log

if __name__ == "__main__":
    # Ensure we use absolute path if necessary or defaults to current workspace
    tooloo_stress_test()
