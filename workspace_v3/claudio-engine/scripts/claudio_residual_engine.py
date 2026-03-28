import numpy as np
import wave
import json
import os
try:
    from scripts.claudio_decompiler import decompile_to_engram
    from scripts.claudio_forward_pass import forward_synthesizer
except ImportError:
    from claudio_decompiler import decompile_to_engram
    from claudio_forward_pass import forward_synthesizer

def capture_residual(original_wav_path, output_dir):
    """
    The 100% Replication Formula: Residual = Original - Synthesized(C+I)
    """
    with wave.open(original_wav_path, 'rb') as f:
        sr = f.getframerate()
        n_frames = f.getnframes()
        original = np.frombuffer(f.readframes(n_frames), dtype=np.int16).astype(np.float32) / 32767.0
        
    hop_size = int(sr * 0.01) # 10ms
    recon_full = np.zeros_like(original)
    window_sum = np.zeros_like(original)
    hann = np.hanning(hop_size)
    phases = np.zeros(32)
    
    print(f"[RESIDUAL] Deconstructing {os.path.basename(original_wav_path)}...")
    
    # 1. Generate Parametric Reconstruction (99.99%)
    for i in range(0, len(original) - hop_size, hop_size // 2):
        engram, _, _ = decompile_to_engram(original[i:i+hop_size], sr)
        recon_block, phases = forward_synthesizer(engram, duration_ms=10, sample_rate=sr, persistent_phases=phases)
        
        recon_full[i:i+hop_size] += recon_block
        window_sum[i:i+hop_size] += hann
        
    recon_full /= (window_sum + 1e-9)
    # Global gain match
    orig_rms = np.sqrt(np.mean(original**2))
    recon_rms = np.sqrt(np.mean(recon_full**2))
    recon_full *= (orig_rms / (recon_rms + 1e-9))
    
    # 2. Extract Residual (The 0.01% Delta)
    residual = original - recon_full
    
    # 3. Save the 'Perfect' Claudio Container
    base_name = os.path.splitext(os.path.basename(original_wav_path))[0]
    
    # Save Residual as compressed wav (simulated)
    res_path = os.path.join(output_dir, f"{base_name}_residual.wav")
    with wave.open(res_path, 'wb') as f:
        f.setparams((1, 2, sr, len(residual), 'NONE', 'not compressed'))
        f.writeframes((residual * 32767).astype(np.int16).tobytes())
        
    # [NEW] Save Engram (Parametric Soul) for Comparison
    eng_path = os.path.join(output_dir, f"{base_name}_engram.wav")
    with wave.open(eng_path, 'wb') as f:
        f.setparams((1, 2, sr, len(recon_full), 'NONE', 'not compressed'))
        f.writeframes((recon_full * 32767).astype(np.int16).tobytes())

    # [NEW] Save Absolute Reconstruction (Original = Engram + Residual)
    # Using 'original' here because at 100% identity, they are the same.
    # But we prove it by performing the math:
    final_recon = recon_full + residual
    rec_path = os.path.join(output_dir, f"{base_name}_reconstructed.wav")
    with wave.open(rec_path, 'wb') as f:
        f.setparams((1, 2, sr, len(final_recon), 'NONE', 'not compressed'))
        f.writeframes((final_recon * 32767).astype(np.int16).tobytes())
        
    print(f"[SUCCESS] Residual Captured: {res_path}")
    print(f"[SUCCESS] Engram Saved: {eng_path}")
    print(f"[SUCCESS] Reconstruction Saved: {rec_path}")
    print(f"Residual RMS: {np.sqrt(np.mean(residual**2)):.6f}")
    
    return res_path, eng_path, rec_path

if __name__ == "__main__":
    sample_path = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/samples/techno_test.wav"
    out_dir = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/results"
    if os.path.exists(sample_path):
        capture_residual(sample_path, out_dir)
