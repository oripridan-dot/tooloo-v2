import os
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt
from scripts.claudio_upscaler import tooloo_prove_identity

# Define the target ensemble file and output paths
INPUT_FILE = "56682c5d9a363489498cc117627db56d1d2619ed80c8d7af9e354609.wav"
OUTPUT_DIR = "results"
OUTPUT_FILE = f"{OUTPUT_DIR}/ensemble_reconstructed_proof.wav"
PLOT_FILE = f"{OUTPUT_DIR}/phase_coherence_audit.png"

def run_phase_coherence_audit():
    print("--- Initiating Mission Absolute Audit ---")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Execute the Strict Engram + Residual Bottleneck
    host_sr = tooloo_prove_identity(INPUT_FILE, OUTPUT_FILE)
    
    # 2. Load the Audio for Mathematical Verification
    print("[AUDIT] Loading waveforms for Phase-Coherence analysis...")
    orig_sig, sr_orig = sf.read(INPUT_FILE)
    recon_sig, sr_recon = sf.read(OUTPUT_FILE)
    
    # Sanity check the Nyquist Lock
    assert sr_orig == sr_recon == host_sr, "CRITICAL: Sample rate mismatch detected!"
    
    # Ensure array lengths match (OLA boundary safety)
    min_len = min(len(orig_sig), len(recon_sig))
    orig_sig = orig_sig[:min_len]
    recon_sig = recon_sig[:min_len]
    
    # 3. Calculate the Delta (Error) Signal
    delta_sig = orig_sig - recon_sig
    delta_rms = np.sqrt(np.mean(delta_sig**2))
    
    print(f"\n[RESULTS] Delta RMS: {delta_rms:.12f}")
    if delta_rms < 1e-7:
        print("[RESULTS] PASS: 100.00% Absolute Mathematical Identity Confirmed. \u2705")
    else:
        print("[RESULTS] FAIL: Mathematical deviation detected. \ud83d\udd34")
        
    # 4. Generate the Visual Proof (The Tribunal Plot)
    print("[AUDIT] Rendering visual proof...")
    time_axis = np.linspace(0, min_len / host_sr, num=min_len)
    
    fig, axs = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    fig.suptitle('Phase-Coherence Audit: Traditional Ensemble', fontsize=16, fontweight='bold')
    
    # Ground Truth
    axs[0].plot(time_axis, orig_sig, color='#1f77b4', alpha=0.8)
    axs[0].set_title('Original Source (Ground Truth)')
    axs[0].grid(True, linestyle='--', alpha=0.6)
    
    # Reconstructed
    axs[1].plot(time_axis, recon_sig, color='#2ca02c', alpha=0.8)
    axs[1].set_title(f'Absolute Identity Reconstruction (Locked to {host_sr} Hz)')
    axs[1].grid(True, linestyle='--', alpha=0.6)
    
    # The Math (Delta)
    axs[2].plot(time_axis, delta_sig, color='#d62728', alpha=0.9)
    axs[2].set_title(f'Delta (Error) Signal | RMS: {delta_rms:.12f}')
    axs[2].set_xlabel('Time (seconds)')
    axs[2].set_ylim([-1.0, 1.0]) # Lock scale to show just how flat the error line is
    axs[2].grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300)
    print(f"[AUDIT] Visual proof saved to: {PLOT_FILE}")
    
    # Display the plot
    # plt.show() # Headless environment, disabled.

if __name__ == "__main__":
    run_phase_coherence_audit()
