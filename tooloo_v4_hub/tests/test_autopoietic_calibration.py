import asyncio
# import pytest (removed for standalone simulation)
from tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse import get_self_evaluator
from tooloo_v4_hub.kernel.governance.billing_manager import get_billing_manager

# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: TEST_AUTOPOIETIC_CALIBRATION.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/test_autopoietic_calibration.py
# WHY: Rule 16 - Autopoietic Vitality Verification
# HOW: Mocked resource consumption and evaluation pulse report validation
# ==========================================================

# @pytest.mark.asyncio (removed for standalone simulation)
async def test_autopoietic_pulse_report():
    """Verify that the evaluation report includes financial metrics."""
    evaluator = get_self_evaluator()
    billing = get_billing_manager()
    
    # 1. Induce "Financial Health" (Add some cost)
    billing.record_usage("vertex_token", 10000)
    
    # 2. Run Cycle
    report = await evaluator.run_evaluation_cycle()
    
    # 3. Verify Structure
    assert "hub_vitality" in report
    assert "financial_vitality" in report
    assert "session_cost_usd" in report
    assert report["session_cost_usd"] > 0.0
    
    print(f"✅ Autopoietic Audit: Vitality={report['hub_vitality']:.4f} | Cost=${report['session_cost_usd']:.6f}")
    assert report["status"] == "SOVEREIGN_AUDIT_COMPLETE"
    print("✨ SOTA AUTOPOIETIC LOOP: VERIFIED.")

if __name__ == "__main__":
    import asyncio
    print("🌀 Auditing Sovereign Autopoiesis (Rule 16)...")
    asyncio.run(test_autopoietic_pulse_report())
    print("✅ AUTOPOIETIC CALIBRATION: ACTIVE.")
