# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining claudio_stress_generator.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.402572
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import numpy as np
import soundfile as sf
import os

def generate_phase_stress(output_path, sr=48000, duration=5.0):
    """
    SOTA Stereo Stress Test:
    - Left: 440Hz Sine.
    - Right: 440Hz Sine with 180 degree phase shift (Anti-phase).
    - Middle: Linear phase sweep to in-phase.
    This tests the engine's ability to maintain spatial coherence under extreme cancellation.
    """
    t = np.linspace(0, duration, int(sr * duration), False)
    
    # Left Channel: Baseline
    left = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    
    # Right Channel: Phase Inversion Sweep
    # Phase starts at pi (180 deg) and sweeps to 0.
    phase_sweep = np.linspace(np.pi, 0, len(t))
    right = 0.5 * np.sin(2 * np.pi * 440.0 * t + phase_sweep)
    
    stereo_signal = np.stack([left, right], axis=1).astype(np.float32)
    
    sf.write(output_path, stereo_signal, sr)
    print(f"[TOOLOO] Generated Physics Stress Asset: {output_path}")

if __name__ == "__main__":
    output_dir = "audio_corpus"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    generate_phase_stress(os.path.join(output_dir, "stereo_phase_stress.wav"))
