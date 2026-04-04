import os
import subprocess
import re
import sys
from pathlib import Path

# WHO: TooLoo Principal Systems Architect
# WHAT: SOTA_CYCLE.PY | Version: 1.0.1
# WHERE: tooloo_v4_hub/scripts/sota_cycle.py
# WHY: Rule 13 (Physics over Syntax) - Benchmark Proof

PROJECT_ROOT = Path(__file__).parent.parent.parent
BUILD_DIR = PROJECT_ROOT / "build"
EXTRACTOR = BUILD_DIR / "claudio_batch_processor"
AUDIO_PROOFS = PROJECT_ROOT / "audio_proofs"

def build_engine():
    print("🛠️  BUILDING CLAUDIO SOTA ENGINE...")
    if not BUILD_DIR.exists():
        BUILD_DIR.mkdir()
    
    # 1. Configure with Unix Makefiles (Safe choice for this environment)
    cmd_config = ["cmake", "-B", "build", "-G", "Unix Makefiles", "-DCMAKE_BUILD_TYPE=Release"]
    result_config = subprocess.run(cmd_config, cwd=PROJECT_ROOT)
    if result_config.returncode != 0:
        raise Exception("CMake configuration failed.")
    
    # 2. Build the specific target
    cmd_build = ["cmake", "--build", "build", "--target", "claudio_batch_processor", "-j", "4"]
    result_build = subprocess.run(cmd_build, cwd=PROJECT_ROOT)
    if result_build.returncode != 0:
        raise Exception("CMake build failed.")

def run_sota_cycle():
    print("🌀 STARTING SOTA VERIFICATION CYCLE...")
    
    wav_files = list(AUDIO_PROOFS.glob("*.wav"))
    if not wav_files:
        print("❌ NO WAV FILES FOUND IN audio_proofs/")
        return

    results = []
    
    for wav in wav_files:
        print(f"🎬 PROCESSING: {wav.name}")
        try:
            # Run the batch processor
            process = subprocess.run([str(EXTRACTOR), str(wav), "0.6"], 
                                     capture_output=True, text=True, check=True)
            output = process.stdout
            
            # Parse SOTA Report
            purity = re.search(r"Purity Score: ([\d.]+)", output)
            latency = re.search(r"Performance: ([\d.]+)", output)
            
            if purity and latency:
                results.append({
                    "file": wav.name,
                    "purity": float(purity.group(1)),
                    "latency_per_block": float(latency.group(1))
                })
                print(f"✅ DONE: Purity {float(purity.group(1)):.2f} | Latency {float(latency.group(1)):.3f}ms")
            else:
                print(f"⚠️  COULD NOT PARSE SOTA REPORT FOR {wav.name}")
                
        except Exception as e:
            print(f"❌ ERROR PROCESSING {wav.name}: {e}")

    # Generate Final SOTA Audit
    if not results:
        print("❌ NO SUCCESSFUL RESULTS TO REPORT.")
        return

    print("\n--- 📊 FINAL SOTA AUDIT REPORT ---")
    avg_purity = sum(r['purity'] for r in results) / len(results)
    avg_latency = sum(r['latency_per_block'] for r in results) / len(results)
    
    status = "SOTA_VALIDATED" if avg_purity > 0.90 and avg_latency < 1.0 else "SUB_PAR"
    
    print(f"Status: {status}")
    print(f"Average Purity Score: {avg_purity:.4f}")
    print(f"Average Block Latency: {avg_latency:.4f}ms")
    print(f"Total Predicted E2E Round Trip: {avg_latency * 2.5:.2f}ms")
    print(f"E2E Target Budget: < 15ms")
    print(f"Confidence Level: {avg_purity * 100:.1f}%")
    print("-----------------------------------")

if __name__ == "__main__":
    try:
        build_engine()
        run_sota_cycle()
    except Exception as e:
        print(f"FATAL SOTA ERROR: {e}")
        sys.exit(1)
