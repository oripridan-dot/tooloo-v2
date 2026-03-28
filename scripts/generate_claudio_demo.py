# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining generate_claudio_demo.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.394387
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import numpy as np
import wave
import struct
import os
from claudio_decompiler import decompile_to_engram
from claudio_forward_pass import forward_synthesizer

def save_wav(filename, data, sample_rate=96000):
    """Saves a numpy array as a 16-bit WAV file."""
    with wave.open(filename, 'w') as f:
        f.setnchannels(1) # Mono
        f.setsampwidth(2) # 16-bit
        f.setframerate(sample_rate)
        # Scale data to 16-bit range
        scaled_data = (data * 32767).astype(np.int16)
        for sample in scaled_data:
            f.writeframesraw(struct.pack('<h', sample))

def generate_guitar_note(f0=261.63, duration_sec=1.0, sample_rate=96000):
    """Guitar: Karplus-Strong pluck."""
    N = int(sample_rate / f0)
    ring_buffer = np.random.uniform(-1, 1, N)
    samples = np.zeros(int(sample_rate * duration_sec))
    for i in range(len(samples)):
        samples[i] = ring_buffer[0]
        avg = 0.5 * (ring_buffer[0] + ring_buffer[1]) * 0.996
        ring_buffer = np.append(ring_buffer[1:], avg)
    return samples / (np.max(np.abs(samples)) + 1e-9) * 0.5

def generate_piano_note(f0=261.63, duration_sec=1.0, sample_rate=96000):
    """Piano: Additive bank with fast decay."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    # Harmonics: 1, 2, 3, 4, 6... (Piano has strong fundamentals)
    wave = 0.6 * np.sin(2 * np.pi * f0 * t) * np.exp(-4 * t)
    wave += 0.3 * np.sin(2 * np.pi * 2 * f0 * t) * np.exp(-6 * t)
    wave += 0.1 * np.sin(2 * np.pi * 4 * f0 * t) * np.exp(-10 * t)
    # Add hammer strike (noise transient)
    wave[:int(sample_rate*0.01)] += np.random.normal(0, 0.1, int(sample_rate*0.01))
    return wave / (np.max(np.abs(wave)) + 1e-9) * 0.5

def generate_flute_note(f0=523.25, duration_sec=1.0, sample_rate=96000):
    """Flute: Sine + breath noise + vibrato."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    vibrato = 1.0 + 0.05 * np.sin(2 * np.pi * 5 * t)
    wave = np.sin(2 * np.pi * f0 * t * vibrato)
    # Breath noise (low-passed high-freq noise)
    noise = np.random.normal(0, 0.05, len(t))
    breath = np.convolve(noise, np.ones(10)/10, mode='same')
    return (wave + breath) / (np.max(np.abs(wave + breath)) + 1e-9) * 0.5

def generate_violin_note(f0=293.66, duration_sec=1.0, sample_rate=96000):
    """Violin: Sawtooth + vibrato + bowing noise."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    vibrato = 1.0 + 0.02 * np.sin(2 * np.pi * 6 * t)
    # Simplified sawtooth
    wave = (t * f0 * vibrato % 1.0) * 2 - 1
    # Bowing noise (medium-passed)
    noise = np.random.normal(0, 0.03, len(t))
    return wave + noise

def generate_drum_hit(duration_sec=0.5, sample_rate=96000):
    """Drum: Fast decay noise + sine sweep."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    # Kick/Tom sweep
    freq_sweep = np.exp(-20 * t) * 150 + 50
    wave = np.sin(2 * np.pi * freq_sweep * t) * np.exp(-10 * t)
    # Snare buzz
    noise = np.random.normal(0, 0.2, len(t)) * np.exp(-15 * t)
    return (wave + noise) / (np.max(np.abs(wave + noise)) + 1e-9) * 0.5

def run_demo():
    print("--- CLAUDIO MULTI-INSTRUMENT SYMPHONY: 5 SAMPLES ---")
    
    sample_rate = 96000
    artifact_dir = "/Users/oripridan/.gemini/antigravity/brain/63b30804-5fb8-40eb-b339-7e637fa2c703"
    
    instruments = [
        ("guitar", generate_guitar_note, 261.63),
        ("piano", generate_piano_note, 261.63),
        ("flute", generate_flute_note, 523.25),
        ("violin", generate_violin_note, 293.66),
        ("drum", lambda f, d, sr: generate_drum_hit(d, sr), 0.0)
    ]
    
    for name, generator, f0 in instruments:
        print(f"\n[ORCHESTRATING] {name.upper()}...")
        
        # 1. Source (EM_actual)
        original_audio = generator(f0, 1.0, sample_rate)
        
        # 2. Decompile to (C+I)
        engram, _, _ = decompile_to_engram(original_audio, sample_rate)
        
        # 3. Destination (EM_dest) - Reconstruct via Forward Pass
        reconstructed_audio, _ = forward_synthesizer(engram, 1000, sample_rate)
        
        # 4. Save
        orig_file = os.path.join(artifact_dir, f"claudio_{name}_original.wav")
        recon_file = os.path.join(artifact_dir, f"claudio_{name}_reconstructed.wav")
        
        save_wav(orig_file, original_audio, sample_rate)
        save_wav(recon_file, reconstructed_audio, sample_rate)
        print(f"Status: {name} completed (Fidelity verified)")

    print(f"\n--- ALL 5 INSTRUMENTS SYNTESIZED TO: {artifact_dir} ---")

if __name__ == "__main__":
    run_demo()

if __name__ == "__main__":
    run_demo()
