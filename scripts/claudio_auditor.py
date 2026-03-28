# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining claudio_auditor.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.408198
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import numpy as np
import wave
import os
import sys
from claudio_residual_engine import capture_residual

class AudioAssertionError(Exception):
    """Raised when an audio fidelity expectation is not met."""
    pass

class AudioExpectation:
    def __init__(self, name, value, auditor):
        self.name = name
        self.value = value
        self.auditor = auditor

    def to_be_above(self, threshold):
        if self.value < threshold:
            raise AudioAssertionError(f"Expected {self.name} to be above {threshold}, but got {self.value:.2f}")
        print(f"[PASS] {self.name}: {self.value:.2f} >= {threshold}")

    def to_be_below(self, threshold):
        if self.value > threshold:
            raise AudioAssertionError(f"Expected {self.name} to be below {threshold}, but got {self.value:.12f}")
        print(f"[PASS] {self.name}: {self.value:.12f} <= {threshold}")

class ClaudioAuditor:
    """
    SOTA 'Audio Playwright' for Claudio.
    Learns the numbers and gaps, and adjusts accordingly.
    """
    def __init__(self, input_wav, results_dir="/Users/oripridan/ANTIGRAVITY/tooloo-v2/results"):
        self.input_wav = input_wav
        self.results_dir = results_dir
        self.original = None
        self.reconstructed = None
        self.residual = None
        self.sr = 0
        self._load_original()

    def _load_original(self):
        with wave.open(self.input_wav, 'rb') as f:
            self.sr = f.getframerate()
            self.original = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32767.0

    def run_pass(self):
        """Executes one full deconstruction/reconstruction pass."""
        res_path, eng_path, rec_path = capture_residual(self.input_wav, self.results_dir)
        with wave.open(rec_path, 'rb') as f:
            self.reconstructed = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32767.0
        with wave.open(res_path, 'rb') as f:
            self.residual = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32767.0
        return self

    def expect_snr(self):
        delta_rms = np.sqrt(np.mean((self.original - self.reconstructed)**2))
        snr = 20 * np.log10(np.std(self.original) / (delta_rms + 1e-12))
        return AudioExpectation("SNR (dB)", snr, self)

    def expect_identity(self):
        # Bit-level identity check: Original == (Synthesized + Residual)
        delta = self.original - (self.reconstructed) # Since rec = synthesized + residual technically
        # We check the delta RMS of the absolute reconstruction
        delta_rms = np.sqrt(np.mean((self.original - self.reconstructed)**2))
        return AudioExpectation("Identity Delta RMS", delta_rms, self)

    def find_gaps(self, threshold=0.1):
        """Identifies time ranges with high spectral error (gaps/numbers)."""
        error = np.abs(self.original - self.reconstructed)
        gaps = np.where(error > threshold)[0]
        if len(gaps) == 0:
            return []
        
        # Cluster gaps into ranges
        ranges = []
        if len(gaps) > 0:
            start = gaps[0]
            for i in range(1, len(gaps)):
                if gaps[i] > gaps[i-1] + self.sr * 0.05: # 50ms gap between clusters
                    ranges.append((start / self.sr, gaps[i-1] / self.sr))
                    start = gaps[i]
            ranges.append((start / self.sr, gaps[-1] / self.sr))
        
        return ranges

    def audit(self, snr_target=150):
        """Automated audit loop with auto-tuning suggestion."""
        print(f"\n--- CLAUDIO AUDITOR START: {os.path.basename(self.input_wav)} ---")
        self.run_pass()
        
        try:
            self.expect_snr().to_be_above(snr_target)
            self.expect_identity().to_be_below(1e-7)
            print("[SUCCESS] Audio Playwright verification passed.")
        except AudioAssertionError as e:
            print(f"[FAILURE] {e}")
            gaps = self.find_gaps()
            if gaps:
                print(f"[REMEDIATION] Detected {len(gaps)} fidelity gaps at: {gaps}")
                print(f"[ACTION] Recommended: Reduce hop_size to 5ms or increase spectral resolution.")
            return False
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 claudio_auditor.py <input.wav>")
        sys.exit(1)
        
    auditor = ClaudioAuditor(sys.argv[1])
    auditor.audit()
