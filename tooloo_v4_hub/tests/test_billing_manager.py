# import pytest (removed for standalone simulation)
from tooloo_v4_hub.kernel.governance.billing_manager import get_billing_manager

# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: TEST_BILLING_MANAGER.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/test_billing_manager.py
# WHY: Rule 14 - Financial Accountability Verification
# HOW: Mock resource pulses and session summary validation
# ==========================================================

def test_token_cost_calculation():
    billing = get_billing_manager()
    start_cost = billing.total_cost_usd
    
    # 5000 tokens for text-embedding-004
    billing.record_usage("vertex_token", 5000)
    
    expected_cost = (5000 / 1000.0) * billing.COST_PER_1K_TOKENS
    assert billing.total_cost_usd == start_cost + expected_cost
    print(f"✅ Token Cost Calculation: ${expected_cost:.6f} VERIFIED.")

def test_firestore_write_cost():
    billing = get_billing_manager()
    start_cost = billing.total_cost_usd
    
    billing.record_usage("firestore_write", 10)
    
    expected_cost = 10 * billing.COST_PER_FS_WRITE
    assert round(billing.total_cost_usd - start_cost, 8) == round(expected_cost, 8)
    print(f"✅ Firestore Write Cost: ${expected_cost:.6f} VERIFIED.")

def test_session_summary_formatting():
    billing = get_billing_manager()
    summary = billing.get_session_summary()
    assert "total_cost_usd" in summary
    assert "tokens_consumed" in summary
    assert "financial_vitality" in summary
    assert summary["tokens_consumed"] >= 5000
    print("✅ Financial Session Summary: VERIFIED.")

if __name__ == "__main__":
    print("💰 Auditing Sovereign Financial Pulse (Rule 14)...")
    test_token_cost_calculation()
    test_firestore_write_cost()
    test_session_summary_formatting()
    print("✨ FINANCIAL IMMUNITY: ACTIVE.")
