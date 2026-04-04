# 6W_STAMP
# WHO: TooLoo V4.6.0 (Sovereign Architect)
# WHAT: AUDIO_LOGIC.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/audio_organ/audio_logic.py
# WHEN: 2026-04-03T13:36:00.000000
# WHY: Rule 13 - Physical Decoupling. High-fidelity FFI bridge to Claudio C++ Core.
# HOW: ctypes-managed pointer orchestration for 512-sample blocks.
# PURITY: 1.00
# TIER: T3:architectural-purity
# ==========================================================

import ctypes
import os
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("Claudio-Logic")

class ClaudioDSPBridge:
    """The Sovereign FFI Bridge to the Claudio Audio Engine (Physics)."""
    
    def __init__(self, lib_path: Optional[str] = None):
        self.lib_path = lib_path or str(Path(__file__).parent / "bin" / "libClaudioEngine.dylib")
        if not os.path.exists(self.lib_path):
             logger.error(f"Claudio: Binary missing at {self.lib_path}")
             raise FileNotFoundError(f"Claudio engine not found at {self.lib_path}")
        
        self.lib = ctypes.CDLL(self.lib_path)
        self._setup_ctypes()
        
        # 1. Initialize Engine Components
        self.synth = self.lib.claudio_synth_create()
        self.decomp = self.lib.claudio_decomp_create(ctypes.c_double(44100.0))
        self.gear = self.lib.claudio_gear_create()
        
        # 2. Prepare Synth for 512-sample blocks
        self.lib.claudio_synth_prepare(self.synth, ctypes.c_double(44100.0), 512)
        logger.info("Claudio: Sovereign DSP Bridge AWAKENED.")

    def _setup_ctypes(self):
        """Rule 10: Strict binary interface definition."""
        self.lib.claudio_synth_create.restype = ctypes.c_void_p
        self.lib.claudio_synth_prepare.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_int]
        self.lib.claudio_synth_update_engram.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_float]
        self.lib.claudio_synth_process.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_float)), ctypes.c_int]
        
        self.lib.claudio_decomp_create.restype = ctypes.c_void_p
        self.lib.claudio_decomp_process.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_float)), ctypes.c_int]
        self.lib.claudio_decomp_get_latest_engram.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]
        
        self.lib.claudio_gear_create.restype = ctypes.c_void_p
        self.lib.claudio_gear_process.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(ctypes.c_float)), ctypes.c_int]
        self.lib.claudio_gear_set_warming.argtypes = [ctypes.c_void_p, ctypes.c_float]

    async def extract_engram(self, audio_chunk: np.ndarray) -> Dict[str, Any]:
        """Rule 16: Extracts a Sovereign Engram from raw audio signal."""
        # Ensure block size alignment (512)
        samples = audio_chunk[:512].astype(np.float32)
        
        # Map to pointer array (Stereo simulated via dual-pointers to same mono source)
        ptr_array = (ctypes.POINTER(ctypes.c_float) * 2)()
        ptr_array[0] = samples.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        ptr_array[1] = samples.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        
        # Process Decompiler
        self.lib.claudio_decomp_process(self.decomp, ptr_array, 512)
        
        # Fetch Engram
        f0 = ctypes.c_float(0.0)
        vel = ctypes.c_float(0.0)
        timbre = (ctypes.c_float * 16)()
        self.lib.claudio_decomp_get_latest_engram(self.decomp, ctypes.byref(f0), ctypes.byref(vel), timbre)
        
        return {
            "f0_hz": round(f0.value, 2),
            "velocity_db": round(vel.value, 2),
            "timbre_vector": [round(t, 4) for t in timbre],
            "stamping": {
                "who": "ClaudioDecompiler",
                "what": "Sovereign Engram Extraction",
                "when": "Real-time Pulse"
            }
        }

    async def process_neural_warmth(self, audio_chunk: np.ndarray, intensity: float = 0.5) -> np.ndarray:
        """Rule 13: Applies Gear Simulation (Neural Analog Warmth)."""
        samples_l = audio_chunk[:512].astype(np.float32).copy()
        samples_r = samples_l.copy()
        
        ptr_array = (ctypes.POINTER(ctypes.c_float) * 2)()
        ptr_array[0] = samples_l.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        ptr_array[1] = samples_r.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        
        # Apply Warming & Process
        self.lib.claudio_gear_set_warming(self.gear, ctypes.c_float(intensity))
        self.lib.claudio_gear_process(self.gear, ptr_array, 512)
        
        # Return merged mono for simplicity in this bridge layer
        return samples_l

_bridge = None
def get_claudio_bridge() -> ClaudioDSPBridge:
    global _bridge
    if _bridge is None:
        _bridge = ClaudioDSPBridge()
    return _bridge
