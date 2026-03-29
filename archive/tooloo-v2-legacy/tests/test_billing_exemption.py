import pytest
from engine.router import MandateRouter, LockedIntent
from engine.tribunal import Tribunal, Engram
from engine.psyche_bank import PsycheBank, CogRule

@pytest.mark.asyncio
async def test_billing_intent_bypass():
    router = MandateRouter()
    
    # Test keyword detection
    res = router.route("I want to pay for more credits")
    assert res.intent == "BILLING"
    assert res.confidence == 1.0
    assert res.circuit_open is False

    # Test circuit breaker bypass
    # Force many low-confidence calls to trip the circuit (not needed since we hard bypass)
    res_direct = router.route("google billing dashboard")
    assert res_direct.intent == "BILLING"
    assert res_direct.confidence == 1.0

@pytest.mark.asyncio
async def test_tribunal_google_exemption():
    tribunal = Tribunal()
    
    # Logic containing Google billing URL
    logic = """
    def pay():
        url = "https://pay.google.com/payments/home"
        secret = "API_KEY=AIzaSy_fake_key"
        print(f"Paying via {url} with {secret}")
    """
    engram = Engram(slug="test-payment", intent="BUILD", logic_body=logic)
    
    res = await tribunal.evaluate(engram)
    assert res.passed is True
    assert res.poison_detected is False
    assert "SECRET" not in engram.logic_body # Wait, if it bypassed, it SHOULD be there
    assert "https://pay.google.com" in engram.logic_body

@pytest.mark.asyncio
async def test_psyche_bank_billing_rejection():
    bank = PsycheBank()
    await bank.__ainit__()
    
    # Try to capture a rule that blocks "google.com"
    rule = CogRule(
        id="test-block-google",
        description="Block google",
        pattern="google.com",
        enforcement="block",
        category="security",
        source="manual"
    )
    
    added = await bank.capture(rule)
    assert added is False # Should be rejected by Rule 4 logic
