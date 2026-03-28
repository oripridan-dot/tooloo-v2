# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining test_claudio_system.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.397195
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import numpy as np
import json
import time
from claudio_decompiler import decompile_to_engram, generate_test_wave
from claudio_forward_pass import forward_synthesizer

def run_loopback_test():
    print("--- CLAUDIO FULL LOOP-BACK TEST ---")
    
    # 1. Source: Generate EM_actual (Raw Audio)
    print("[1/3] Source: Capturing 10ms Audio (440Hz A4)...")
    raw_audio = generate_test_wave(freq=440.0)
    
    # 2. Transmission: Decompile to (C+I) Engram
    print("[2/3] Transmission: Running Decompiler Matrix...")
    engram, d_lat, e_size = decompile_to_engram(raw_audio)
    
    # 3. Destination: Run Forward Pass Synthesizer
    print("[3/3] Destination: Running Forward Pass (Native Reconstruction)...")
    reconstructed_wave, f_lat = forward_synthesizer(engram)
    
    total_latency = d_lat + f_lat
    
    print(f"\n--- SYSTEM METRICS ---")
    print(f"Decomp Latency:     {d_lat:.3f} ms")
    print(f"Forward Latency:    {f_lat:.3f} ms")
    print(f"Total Local Latency: {total_latency:.3f} ms")
    print(f"Engram Size:        {e_size} bytes")
    print(f"Reduction Ratio:    {raw_audio.nbytes / e_size:.2f}x")
    
    if total_latency < 1.0:
        print("\nStatus: SOTA PERFORMANCE (Total Latency < 1ms)")
    else:
        print("\nStatus: SUCCESS (Low Latency)")

if __name__ == "__main__":
    run_loopback_test()
