# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: claudio_bridge.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/claudio_bridge.py
# WHEN: 2026-04-03T16:08:23.395299+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import ctypes
import os
import platform
import numpy as np

class ClaudioBridge:
    def __init__(self, lib_path=None):
        if lib_path is None:
            # SOTA: Auto-locate the compiled engine
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            ext = ".dylib" if platform.system() == "Darwin" else ".so"
            lib_path = os.path.join(project_root, "isolated_claudio_engine", f"libClaudioEngine{ext}")

        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"ClaudioEngine not found at {lib_path}. Run build first.")

        self.lib = ctypes.CDLL(lib_path)
        self._setup_ctypes()
        
        # Initialize Native Organs
        self.synth = self.lib.claudio_synth_create()
        self.decomp = self.lib.claudio_decomp_create(ctypes.c_double(44100.0))
        self.pulse = self.lib.claudio_pulse_create()
        self.gear = self.lib.claudio_gear_create()

    def _setup_ctypes(self):
        # Synth
        self.lib.claudio_synth_create.restype = ctypes.c_void_p
        self.lib.claudio_synth_prepare.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_int]
        self.lib.claudio_synth_update_engram.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_float]
        
        # Decompiler
        self.lib.claudio_decomp_create.restype = ctypes.c_void_p
        self.lib.claudio_decomp_get_latest_engram.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]

        # Pulse
        self.lib.claudio_pulse_create.restype = ctypes.c_void_p
        self.lib.claudio_pulse_start.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.lib.claudio_pulse_connect.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.claudio_pulse_send_engram.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.POINTER(ctypes.c_float)]

        # Gear
        self.lib.claudio_gear_create.restype = ctypes.c_void_p
        self.lib.claudio_gear_set_warming.argtypes = [ctypes.c_void_p, ctypes.c_float]

    def prepare_synth(self, sample_rate=44100.0, block_size=128):
        self.lib.claudio_synth_prepare(self.synth, ctypes.c_double(sample_rate), ctypes.c_int(block_size))

    def update_synth(self, f0, spectral_16d, noise_floor=0.01):
        spec_arr = (ctypes.c_float * 16)(*spectral_16d)
        phases = (ctypes.c_float * 32)(*([0.0]*32))
        self.lib.claudio_synth_update_engram(self.synth, ctypes.c_float(f0), spec_arr, phases, ctypes.c_float(noise_floor))

    def start_collaboration(self, port=15000):
        self.lib.claudio_pulse_start(self.pulse, ctypes.c_int(port))

    def connect_to_peer(self, address, port=15000):
        self.lib.claudio_pulse_connect(self.pulse, address.encode('utf-8'), ctypes.c_int(port))

    def send_intent(self, f0, velocity, timbre_16d):
        timbre_arr = (ctypes.c_float * 16)(*timbre_16d)
        self.lib.claudio_pulse_send_engram(self.pulse, ctypes.c_float(f0), ctypes.c_float(velocity), timbre_arr)

    def set_gear_warming(self, factor):
        self.lib.claudio_gear_set_warming(self.gear, ctypes.c_float(factor))

    def __del__(self):
        # Cleanup native memory
        if hasattr(self, 'lib'):
            self.lib.claudio_synth_destroy(self.synth)
            self.lib.claudio_decomp_destroy(self.decomp)
