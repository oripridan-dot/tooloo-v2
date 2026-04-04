# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: FS_WRITE:test_dsp_limiter.py | Version: 1.3.0
# WHERE: /Users/oripridan/ANTIGRAVITY/tooloo-v2/tooloo_v4_hub/shared/dsp/test_dsp_limiter.py
# WHEN: 2026-04-04T00:51:38.892679+00:00
# WHY: Autonomous Mission Manifestation
# HOW: Sovereign Hub fs_write Pulse
# TRUST: T4:zero-trust
# DOMAINS: fs, mcp, reality
# PURITY: 1.00
# ==========================================================

import unittest
import numpy as np
from dsp_limiter import DSPLimiter

class TestDSPLimiter(unittest.TestCase):
    def setUp(self):
        self.sample_rate = 44100
        self.limiter = DSPLimiter(threshold_db=-6.0, attack_ms=1.0, release_ms=100.0, sample_rate=self.sample_rate)
        self.threshold_linear = 10**(self.limiter.threshold_db / 20.0)

    def test_initialization(self):
        self.assertAlmostEqual(self.limiter.threshold_db, -6.0)
        self.assertAlmostEqual(self.limiter.attack_ms, 1.0)
        self.assertAlmostEqual(self.limiter.release_ms, 100.0)
        self.assertEqual(self.limiter.sample_rate, 44100)

    def test_no_limiting_below_threshold(self):
        # Input well below threshold (-20dB) for 1 second
        audio_input = np.full(self.sample_rate, 10**(-20/20.0), dtype=np.float32)
        output = self.limiter.process_chunk(audio_input)
        self.assertTrue(np.allclose(audio_input, output, atol=1e-5))

    def test_limiting_above_threshold(self):
        # Input significantly above threshold (+0dB) for 1 second
        audio_input = np.full(self.sample_rate, 1.0, dtype=np.float32)
        output = self.limiter.process_chunk(audio_input)
        # Max output should be very close to the threshold
        self.assertLessEqual(np.max(np.abs(output)), self.threshold_linear * 1.001)
        self.assertGreater(np.max(np.abs(output)), self.threshold_linear * 0.99)

    def test_attack_time(self):
        # Test that a sudden peak is limited after attack time
        pre_peak = np.full(int(self.sample_rate * 0.1), 0.1, dtype=np.float32) # below threshold
        peak = np.full(int(self.sample_rate * 0.01), 0.8, dtype=np.float32) # above threshold
        audio_input = np.concatenate((pre_peak, peak))

        output = self.limiter.process_chunk(audio_input)
        # The first part of the peak might not be fully limited, but later parts should be
        # More robust testing would analyze the envelope progression
        self.assertLessEqual(np.max(np.abs(output[-int(self.sample_rate * 0.005):])), self.threshold_linear * 1.001)

    def test_release_time(self):
        # Test that gain returns to 1.0 after the signal drops below threshold
        peak = np.full(int(self.sample_rate * 0.01), 0.8, dtype=np.float32)
        post_peak = np.full(int(self.sample_rate * 0.2), 0.1, dtype=np.float32)
        audio_input = np.concatenate((peak, post_peak))

        output = self.limiter.process_chunk(audio_input)
        # After release time, output should match input again for low signal
        self.assertTrue(np.allclose(output[-int(self.sample_rate * 0.05):], post_peak[-int(self.sample_rate * 0.05):], atol=1e-3))

if __name__ == '__main__':
    unittest.main()