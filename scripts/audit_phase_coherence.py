# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining audit_phase_coherence.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.398431
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import numpy as np
import os
import wave
import struct

def check_phase_coherence(filename):
    """
    Audits the phase derivative at frame boundaries (every 10ms).
    """
    with wave.open(filename, 'rb') as f:
        params = f.getparams()
        frames = f.readframes(params.nframes)
        data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
        sample_rate = params.framerate
    
    # Analyze boundaries every 10ms (960 samples @ 96k)
    hop = int(sample_rate * 0.01)
    jumps = []
    
    for i in range(hop, len(data) - hop, hop):
        # Measure local delta across the boundary
        pre = data[i-1]
        at = data[i]
        post = data[i+1]
        
        # Continuity check: Is the derivative consistent?
        d1 = at - pre
        d2 = post - at
        delta_accel = abs(d2 - d1)
        jumps.append(delta_accel)
        
    avg_jump = np.mean(jumps)
    max_jump = np.max(jumps)
    
    print(f"--- PHASE COHERENCE AUDIT: {os.path.basename(filename)} ---")
    print(f"Average Boundary Delta: {avg_jump:.8f}")
    print(f"Max Boundary Jump: {max_jump:.8f}")
    
    # Target: Avg Jump < 0.005 (Standard for OLA)
    status = "CLEAN" if avg_jump < 0.005 else "DISCONTINUOUS"
    print(f"Status: {status}")
    return avg_jump

if __name__ == "__main__":
    artifact_dir = "/Users/oripridan/.gemini/antigravity/brain/63b30804-5fb8-40eb-b339-7e637fa2c703"
    check_phase_coherence(os.path.join(artifact_dir, "claudio_violin_reconstructed.wav"))
    check_phase_coherence(os.path.join(artifact_dir, "claudio_piano_reconstructed.wav"))
