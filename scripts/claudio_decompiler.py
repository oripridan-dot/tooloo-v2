# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining claudio_decompiler.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.403547
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import numpy as np
import json
import time

def generate_test_wave(sample_rate=96000, duration_ms=10, freq=440.0):
    """Simulates a 10ms raw audio buffer (EM_actual) from a studio interface."""
    t = np.linspace(0, duration_ms / 1000.0, int(sample_rate * (duration_ms / 1000.0)), False)
    # Generate a sine wave (fundamental) + a harmonic to simulate an instrument
    wave = 0.5 * np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * (freq * 2) * t)
    return wave

def decompile_to_engram(audio_buffer, sample_rate=96000):
    """
    The Mathematical Inverse: EM_actual * E_local^-1 = (C+I)
    Extracts the Intent (Pitch & Velocity) and Context from the raw wave.
    """
    start_time = time.perf_counter()

    # 1. Extract Intent: Velocity (Amplitude/RMS to dB)
    rms = np.sqrt(np.mean(audio_buffer**2))
    velocity_db = 20 * np.log10(rms + 1e-9) # Avoid log(0)

    # 2. Extract Intent: Pitch (f0_hz) via Autocorrelation
    corr = np.correlate(audio_buffer, audio_buffer, mode='full')
    corr = corr[len(corr)//2:]
    zero_crossings = np.where(np.diff(np.sign(corr)))[0]
    f0_hz = 0.0
    if len(zero_crossings) > 0:
        first_zc = zero_crossings[0]
        peak_idx = np.argmax(corr[first_zc:]) + first_zc
        f0_hz = sample_rate / peak_idx if peak_idx > 0 else 0.0

    # 3. Phase 8: Sub-Block Analysis (2.5ms Resolution)
    # Target: >99.9% Musical Fidelity via high-speed tracking
    num_subblocks = 4 if len(audio_buffer) >= (sample_rate * 0.01) else 1
    subblock_size = len(audio_buffer) // num_subblocks
    subblocks_data = []
    
    for b in range(num_subblocks):
        start = b * subblock_size
        end = (b + 1) * subblock_size
        block = audio_buffer[start:end]
        
        # Sub-block RMS and Transient
        sub_rms = np.sqrt(np.mean(block**2))
        sub_transient = float(np.max(np.abs(block)))
        
        # Spectral Peaks for this sub-block
        fft_sub = np.fft.rfft(block, n=1024)
        mags_sub = np.abs(fft_sub)
        p_idx = np.argmax(mags_sub)
        sub_f0 = p_idx * sample_rate / 1024
        
        subblocks_data.append({
            "rms": float(sub_rms),
            "transient": sub_transient,
            "f0": float(sub_f0)
        })

    extraction_time_ms = (time.perf_counter() - start_time) * 1000

    # 5. Construct the (C+I) Engram Payload (High-Resolution)
    amplitudes = [sb["rms"] for sb in subblocks_data]
    transient_score = float(np.max(np.diff(amplitudes)) if len(amplitudes) > 1 else 0.0)

    # 5. Extract Initial Phase for PLL Alignment
    n_fft = 2048
    window = np.hanning(len(audio_buffer))
    fft_data = np.fft.rfft(audio_buffer * window, n=n_fft)
    
    # 2. Fundamental Frequency (f0) extraction via Parabolic Interpolation
    flux = np.mean(np.abs(np.diff(np.abs(fft_data[:256]))))
    
    # Accurate f0 index
    bin_idx = np.argmax(np.abs(fft_data[:256]))
    # Parabolic Interpolation for sub-bin accuracy
    if 0 < bin_idx < len(fft_data) - 1:
        y0, y1, y2 = np.abs(fft_data[bin_idx-1:bin_idx+2])
        p = 0.5 * (y0 - y2) / (y0 - 2*y1 + y2 + 1e-9)
        f0_hz = (bin_idx + p) * sample_rate / n_fft
        # Interpolated Phase
        phase_init = float(np.angle(fft_data[bin_idx]))
    else:
        f0_hz = bin_idx * sample_rate / n_fft
        phase_init = float(np.angle(fft_data[bin_idx]))

    # 3. Extract Harmonic Gains (The 'Identity') - Upgraded to 32D
    harmonic_gains = []
    for h in range(1, 33):
        target_f = f0_hz * h
        idx = int(target_f * n_fft / sample_rate)
        if 0 <= idx < len(fft_data):
            # Peak search around the target harmonic bin
            search_window = 2
            start_search = max(0, idx - search_window)
            end_search = min(len(fft_data), idx + search_window + 1)
            gain = np.max(np.abs(fft_data[start_search:end_search])) / (n_fft / 2)
            harmonic_gains.append(float(gain))
        else:
            harmonic_gains.append(0.0)

    engram = {
        "context": {
            "version": "2.0", # Upgraded to 2.0 (32D)
            "sample_rate": sample_rate,
            "latency_target_ms": 10
        },
        "intent": {
            "subblocks": subblocks_data,
            "f0_global": float(f0_hz),
            "phase_alignment": phase_init, # For PLL
            "spectral_flux": float(flux),  # For Grit
            "transient_trigger": transient_score, # For Pluck
            "harmonic_gains": harmonic_gains
        }
    }
    
    return engram, extraction_time_ms, len(json.dumps(engram))

# --- Run the Test ---
if __name__ == "__main__":
    print("Capturing 10ms Audio Buffer (EM_actual)...")
    raw_audio = generate_test_wave(freq=440.0) # A4 Note
    
    print("Running Decompiler Matrix (E_local^-1)...\n")
    engram_payload, latency, size_bytes = decompile_to_engram(raw_audio)
    
    print(f"--- EXTRACTED ENGRAM (C+I) ---")
    print(json.dumps(engram_payload, indent=2))
    print(f"------------------------------")
    print(f"Extraction Latency:  {latency:.3f} ms")
    print(f"Network Payload Size: {size_bytes} bytes")
    print(f"Original Audio Size:  {raw_audio.nbytes} bytes")
    print(f"Bandwidth Savings:   {raw_audio.nbytes / size_bytes:.2f}x reduction")
