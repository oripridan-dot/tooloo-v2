# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_TEST_CALIBRATION.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tests/test_calibration.py
# WHEN: 2026-04-01T16:35:57.949786+00:00
# WHY: Heal STAMP_PURITY_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import asyncio
import os
import json
from pathlib import Path
from tooloo_v4_hub.kernel.cognitive.predictive_trainer import get_predictive_trainer
async def test_predictive_calibration_loop():
    # Setup temporary world model
    test_model_path = "tooloo_v4_hub/psyche_bank/test_world_model.json"
    if os.path.exists(test_model_path): os.remove(test_model_path)
    
    trainer = get_predictive_trainer()
    trainer.model_path = Path(test_model_path)
    trainer.world_model = {"version": "4.0.0-test", "weights": {"gemini-1.5-pro": {"v": 0.5}}}
    
    # 1. Ingest high-performance pulse (Low latency, High purity)
    # Expected: Actual V > Predicted V, so delta is negative. Weight should increase.
    await trainer.ingest_telemetry_pulse("gemini-1.5-pro", latency_ms=100, tokens=500, purity=1.0)
    
    # Wait for async persistence
    await asyncio.sleep(0.5)
    
    with open(test_model_path, "r") as f:
        updated_model = json.load(f)
    
    new_weight = updated_model["weights"]["gemini-1.5-pro"]["v"]
    print(f"Initial: 0.5 | New Weight: {new_weight}")
    
    assert new_weight > 0.5, "Weight should increase for high performance"
    
    # 2. Ingest low-performance pulse (High latency, Low purity)
    await trainer.ingest_telemetry_pulse("gemini-1.5-pro", latency_ms=10000, tokens=500, purity=0.2)
    await asyncio.sleep(0.5)
    
    with open(test_model_path, "r") as f:
        updated_model = json.load(f)
        
    final_weight = updated_model["weights"]["gemini-1.5-pro"]["v"]
    print(f"Post-Failure Weight: {final_weight}")
    
    assert final_weight < new_weight, "Weight should decrease for low performance"

    # Cleanup
    if os.path.exists(test_model_path): os.remove(test_model_path)

if __name__ == "__main__":
    asyncio.run(test_predictive_calibration_loop())