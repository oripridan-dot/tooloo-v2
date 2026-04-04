# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TEST_CALIBRATION_FEEDBACK.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/test_calibration_feedback.py
# WHEN: 2026-03-31T14:26:13.339895+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: test, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import json
import pytest
import os
from tooloo_v4_hub.kernel.cognitive.calibration import get_calibration_engine
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus

@pytest.mark.anyio
async def test_calibration_mutation():
    """Verifies that resolution_winner engrams lead to weight mutations."""
    import sys
    engine = get_calibration_engine()
    nexus = get_mcp_nexus()
    
    # 0. Tether Memory Organ for the test loop
    await nexus.attach_organ("memory_organ", [sys.executable, "-m", "tooloo_v4_hub.organs.memory_organ.mcp_server"])
    
    bank_path = "tooloo_v4_hub/psyche_bank/world_model_v3.json"
    
    # 1. Capture Initial State
    with open(bank_path, "r") as f:
        initial_data = json.load(f)
        initial_val = initial_data["w1"][12][0] # Logic Index [12]
    
    # 2. Inject Resolver Evidence (Low Drift = 0.5)
    # This should trigger a positive shift of approximately (1.0 - 0.5) * gain
    await nexus.call_tool("memory_store", {
        "engram_id": "test_mutation_winner",
        "data": {
            "type": "resolution_winner",
            "drift_score": 0.5,
            "domain": "logic"
        }
    })
    
    # 3. Trigger Refinement
    drift = await engine.compute_drift()
    assert drift >= 0.5
    
    await engine.refine_weights("logic", drift * 0.1)
    
    # 4. Capture Final State
    with open(bank_path, "r") as f:
        final_data = json.load(f)
        final_val = final_data["w1"][12][0]
    
    assert final_val != initial_val
    assert final_val > initial_val
    print(f"Mutation Verified: {initial_val:.6f} -> {final_val:.6f}")