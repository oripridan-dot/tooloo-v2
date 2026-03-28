# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.claudio_governor.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

import asyncio
import time
import subprocess
import re
import datetime
import logging
import numpy as np
import soundfile as sf
import os
import traceback
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from numba import njit
except ImportError:
    def njit(f): return f

from scripts.claudio_upscaler import tooloo_prove_identity

# --- SOTA JIT Kernels (Top-Level for ProcessPool Compatibility) ---

@njit
def _jit_resample_linear_governor(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """SOTA JIT-Accelerated Linear Resampler for Governor Audit."""
    ratio = float(orig_sr) / float(target_sr)
    orig_len = audio.shape[0]
    new_len = int(orig_len / ratio)
    
    if audio.ndim == 1:
        output = np.zeros(new_len, dtype=np.float64)
        for i in range(new_len):
            pos = i * ratio
            idx = int(pos)
            frac = pos - idx
            if idx + 1 < orig_len:
                output[i] = audio[idx] * (1 - frac) + audio[idx + 1] * frac
            else:
                output[i] = audio[idx]
        return output
    else:
        channels = audio.shape[1]
        output_multi = np.zeros((new_len, channels), dtype=np.float64)
        for i in range(new_len):
            pos = i * ratio
            idx = int(pos)
            frac = pos - idx
            if idx + 1 < orig_len:
                for c in range(channels):
                    output_multi[i, c] = audio[idx, c] * (1 - frac) + audio[idx + 1, c] * frac
            else:
                for c in range(channels):
                    output_multi[i, c] = audio[idx, c]
        return output_multi

def _run_variant_worker(file_path: str, strategy: dict, hardening_args: List[str] = []) -> Optional[dict]:
    """Parallel Variant Agent (Pathway B)."""
    try:
        tmp_output = f"/tmp/variant_{strategy['name']}_{os.path.basename(file_path)}"
        
        # Inject hardening context into the proof identity call
        params = strategy.get("params", {}).copy()
        
        # Call the SOTA Upscaler
        tooloo_prove_identity(file_path, tmp_output, params=params)
        
        # Audit Identity locally within the worker
        orig_sig, orig_sr = sf.read(file_path)
        recon_sig, recon_sr = sf.read(tmp_output)
        
        if orig_sr != recon_sr:
            orig_sig = _jit_resample_linear_governor(orig_sig, orig_sr, recon_sr)
            
        # Shape Alignment
        if orig_sig.shape != recon_sig.shape:
            if orig_sig.ndim == 1: orig_sig = orig_sig.reshape(-1, 1)
            if recon_sig.ndim == 1: recon_sig = recon_sig.reshape(-1, 1)
            c1, c2 = orig_sig.shape[1], recon_sig.shape[1]
            if c1 != c2:
                if c1 == 2 and c2 == 1: recon_sig = np.column_stack([recon_sig, recon_sig])
                elif c1 == 1 and c2 == 2: orig_sig = np.column_stack([orig_sig, orig_sig])
        
        min_len = min(orig_sig.shape[0], recon_sig.shape[0])
        delta_sig = orig_sig[:min_len] - recon_sig[:min_len]
        delta_rms = float(np.sqrt(np.mean(delta_sig**2)))
        
        return {
            "name": strategy["name"],
            "delta_rms": delta_rms,
            "tmp_path": tmp_output,
            "params": params
        }
    except Exception as e:
        print(f"[ERROR] Variant {strategy['name']} failed: {e}")
        return None

class ClaudioProbe:
    """Sensing the host physics to determine SOTA headroom."""
    def benchmark(self) -> str:
        """Runs a 100ms grain benchmark to determine optimal 32D profile."""
        start = time.perf_counter()
        # Mocking a heavy 32D FFT load
        for _ in range(1000):
            _ = np.fft.fft(np.random.rand(1024))
        elapsed = time.perf_counter() - start
        
        if elapsed < 0.05: return "ULTRA"
        if elapsed < 0.15: return "BALANCED"
        return "ECO"

class ClaudioGovernor:
    """
    SOTA Claudio Governor.
    Governs the Absolute Identity Proof via Async Rule Discovery (PsycheBank)
    and Parallel Pathway B resolution.
    """
    def __init__(self, tolerance: float = 1e-7):
        self.tolerance = tolerance
        from engine.psyche_bank import PsycheBank
        self.bank = PsycheBank()
        self._initialized = False
        self.probe = ClaudioProbe()
        self.active_profile = "BALANCED"

    async def _ensure_bank(self):
        if not self._initialized:
            await self.bank.__ainit__()
            self.active_profile = self.probe.benchmark()
            logging.info(f"[GOVERNOR] Environment Probed: {self.active_profile} Mode Selected.")
            self._initialized = True

    def get_profile_params(self) -> dict:
        """Returns SOTA params for the detected environment."""
        profiles = {
            "ULTRA": {"hop_size": 0.001, "harmonics": 32},
            "BALANCED": {"hop_size": 0.002, "harmonics": 32},
            "ECO": {"hop_size": 0.005, "harmonics": 16}
        }
        return profiles.get(self.active_profile, profiles["BALANCED"])

    async def _get_active_rules(self, asset_name: str) -> list:
        """Regex-based rule selection for pattern-aware hardening."""
        await self._ensure_bank()
        rules = await self.bank.rules_by_category("claudio_hardening")
        active = []
        for r in rules:
            if re.search(r.pattern, asset_name):
                active.append(r)
        return active

    def execute_proof_sync(self, file_path: str, output_path: str, params: dict = None) -> dict:
        """Synchronous bridge for UI stability."""
        import asyncio
        # We create a new loop if one doesn't exist, or run in the existing one
        try:
            return asyncio.run(self.execute_proof_loop(file_path, output_path, params))
        except Exception as e:
            # Fallback to direct call if loop is already running
            logging.warning(f"[GOVERNOR] asyncio.run failed, attempting loop run: {e}")
            loop = asyncio.new_event_loop()
            return loop.run_until_complete(self.execute_proof_loop(file_path, output_path, params))

    async def execute_proof_loop(self, file_path: str, output_path: str, params: dict = None, iteration: int = 1) -> dict:
        """Pathway A: Direct Governance + Iterative Improvement."""
        asset_name = os.path.basename(file_path)
        await self._ensure_bank()
        
        # 0. Rule Discovery + Environmental Tuning
        if params is None:
            rules = await self._get_active_rules(asset_name)
            if rules:
                params = rules[0].metadata.get("params") if rules[0].metadata else {}
            else:
                params = self.get_profile_params() # Default to Environmental Profile
        
        # 0b. Iterative Nudging (SOTA: Shrinking Grain)
        if iteration > 1:
            params["hop_size"] = max(0.0005, params.get("hop_size", 0.002) * 0.75)
            logging.info(f"[GOVERNOR] Iteration {iteration}: Nudging Hop Size -> {params['hop_size']}")

        logging.info(f"[GOVERNOR] Cycle {iteration} | Mode: {self.active_profile} | Params: {params}")

        try:
            tooloo_prove_identity(file_path, output_path, params=params)
            delta_rms = self._calculate_delta(file_path, output_path)
            
            if delta_rms <= self.tolerance:
                return {"success": True, "pathway": "A", "delta_rms": delta_rms, "profile": self.active_profile, "iterations": iteration}
            elif iteration < 3:
                logging.info(f"[GOVERNOR] Delta {delta_rms:.2e} > Tolerance. Looping for improvement...")
                return await self.execute_proof_loop(file_path, output_path, params=params, iteration=iteration + 1)
            else:
                return await self.trigger_pathway_b(file_path, output_path, current_delta=delta_rms, iteration=iteration)
        except Exception as e:
            logging.error(f"[GOVERNOR] Pathway A Error: {e}")
            return await self.trigger_pathway_b(file_path, output_path, error=str(e))

    async def trigger_pathway_b(self, file_path: str, output_path: str, current_delta: float = None, error: str = None, iteration: int = 1) -> dict:
        """Pathway B: Multi-Variant Parallel Competition."""
        logging.info("[GOVERNOR] Initiating Parallel Pathway B...")
        
        strategies = [
            {"name": "StandardHardening", "params": {"hop_size": 0.002}},
            {"name": "HighTemporalRes", "params": {"hop_size": 0.001}},
            {"name": "SpectralSync", "params": {"hop_size": 0.0025}}
        ]
        
        results = []
        # Run variants in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            loop = asyncio.get_event_loop()
            futures = [loop.run_in_executor(executor, _run_variant_worker, file_path, s) for s in strategies]
            for f in await asyncio.gather(*futures):
                if f: results.append(f)

        if not results:
            return {"success": False, "error": f"Resolution failure: {error}"}
            
        winner = min(results, key=lambda x: x["delta_rms"])
        os.replace(winner["tmp_path"], output_path)
        
        # 4. Meta-Learning: Persist win to PsycheBank for future assets
        await self._learn_from_win(file_path, winner)
        
        return {
            "success": True, "pathway": "B", "delta_rms": winner["delta_rms"],
            "resolution": winner["name"], "params": winner["params"],
            "profile": self.active_profile, "iterations": iteration
        }

    async def _learn_from_win(self, file_path: str, winner: dict):
        """Immortalizes the winning hardening profile in PsycheBank."""
        from engine.psyche_bank import CogRule
        rule = CogRule(
            id=f"harden-{os.path.basename(file_path)}-{datetime.datetime.now().strftime('%Y%j')}",
            description=f"Auto-generated hardening rule for {os.path.basename(file_path)}",
            pattern=os.path.basename(file_path),
            enforcement="warn",
            category="claudio_hardening",
            source="tribunal",
            metadata={"params": winner["params"], "achieved_delta": winner["delta_rms"]}
        )
        await self.bank.capture(rule)

    def _calculate_delta(self, original: str, reconstructed: str) -> float:
        """Standarized Multi-Channel Audit."""
        orig_sig, orig_sr = sf.read(original)
        recon_sig, recon_sr = sf.read(reconstructed)
        if orig_sr != recon_sr:
            orig_sig = _jit_resample_linear_governor(orig_sig, orig_sr, recon_sr)
        
        if orig_sig.shape != recon_sig.shape:
            if orig_sig.ndim == 1: orig_sig = orig_sig.reshape(-1, 1)
            if recon_sig.ndim == 1: recon_sig = recon_sig.reshape(-1, 1)
            c1, c2 = orig_sig.shape[1], recon_sig.shape[1]
            if c1 != c2:
                if c1 == 2 and c2 == 1: recon_sig = np.column_stack([recon_sig, recon_sig])
                elif c1 == 1 and c2 == 2: orig_sig = np.column_stack([orig_sig, orig_sig])
        
        min_len = min(orig_sig.shape[0], recon_sig.shape[0])
        delta_sig = orig_sig[:min_len] - recon_sig[:min_len]
        return float(np.sqrt(np.mean(delta_sig**2)))
