# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: CALIBRATION_PULSE.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/tools/calibration_pulse.py
# WHEN: 2026-03-31T14:26:13.336519+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: tool, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from tooloo_v3_hub.kernel.cognitive.calibration import get_calibration_engine
from tooloo_v3_hub.kernel.mcp_nexus import get_mcp_nexus

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Calibration-Visualizer")

def get_weight_snapshot(bank_path: str) -> list:
    """Returns the first 20 vectors of the w1 layer for comparison."""
    if not os.path.exists(bank_path):
        return []
    with open(bank_path, "r") as f:
        data = json.load(f)
        return [v[0] for v in data.get("w1", [])[:20]]

def render_heatmap(before: list, after: list):
    """Prints a CLI heatmap showing Delta directions."""
    print(f"\n{'Vector ID':<10} | {'Before':>10} | {'After':>10} | {'Shift'}")
    print("-" * 50)
    
    for i in range(len(before)):
        b = before[i]
        a = after[i]
        delta = a - b
        
        # Color coding: Green for positive shift, Red for negative
        color = "\033[92m▲\033[0m" if delta > 0.0001 else "\033[91m▼\033[0m" if delta < -0.0001 else "•"
        
        print(f"[{i:02d}]        | {b:>10.4f} | {a:>10.4f} | {color} ({delta:+.5f})")

async def run_visualizer():
    print("\n" + "="*60)
    print("   SOVEREIGN HUB: 22D WORLD MODEL CALIBRATION PULSE")
    print("="*60 + "\n")
    
    bank_path = "tooloo_v3_bank/world_model_v3.json"  # Adjusted for consistency
    if not os.path.exists(bank_path):
        bank_path = "tooloo_v3_hub/psyche_bank/world_model_v3.json"
        
    engine = get_calibration_engine()
    nexus = get_mcp_nexus()
    
    # 0. Tether Federated Organs for the Pulse
    print("[0/4] Tethering Federated Memory Organ...")
    await nexus.attach_organ("memory_organ", [sys.executable, "-m", "tooloo_v3_hub.organs.memory_organ.mcp_server"])
    
    # 1. Capture 'Before' State
    print("[1/4] Capturing Baseline Tensors...")
    before = get_weight_snapshot(bank_path)
    
    # 2. Mock Federated Evidence (Pathway B Winners)
    print("[2/4] Injecting Federated Evidence (Pathway B Outcomes)...")
    # We store a few "high drift" engrams to force a noticeable shift
    for i in range(3):
        await nexus.call_tool("memory_store", {
            "engram_id": f"lab_drift_winner_{i}",
            "data": {
                "type": "resolution_winner",
                "drift_score": 0.82 - (i * 0.05), # Simulating worsening alignment
                "total_score": 9.5,
                "domain": "logic"
            }
        })
    
    # 3. Trigger Active Refinement
    print("[3/4] Triggering Cognitive Refinement Cycle...")
    drift = await engine.compute_drift()
    await engine.refine_weights("logic", drift * 0.5) # Forced high gain for visualization
    
    # 4. Compare and Render
    print("[4/4] Generating Differential Heatmap...")
    after = get_weight_snapshot(bank_path)
    
    render_heatmap(before, after)
    
    print("\n" + "="*60)
    print("   CALIBRATION PULSE COMPLETE. Bank Tensors Updated.")
    print("="*60 + "\n")

if __name__ == "__main__":
    if not os.path.exists("tooloo_v3_hub/psyche_bank/world_model_v3.json"):
        print("Error: world_model_v3.json not found. Run from project root.")
        sys.exit(1)
    asyncio.run(run_visualizer())