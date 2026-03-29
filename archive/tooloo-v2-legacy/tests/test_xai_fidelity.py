import sys
import os

# Add root to sys.path
root = "/Users/oripridan/ANTIGRAVITY/tooloo-v2"
if root not in sys.path:
    sys.path.insert(0, root)

from engine.router import MandateRouter

def test_xai():
    print("🧪 Testing Surgical XAI Fidelity...")
    router = MandateRouter()
    
    # Test message with clear keywords
    mandate = "audit the security and check for bugs"
    result = router.route(mandate)
    
    print(f"  · Mandate: '{mandate}'")
    print(f"  · Intent: {result.intent} (Confidence: {result.confidence})")
    
    # Get explanation
    explanation = router.explain_decision(result)
    
    if explanation:
        print(f"  · Narrative: {explanation.narrative}")
        print(f"  · Local Contribution (LIME-style): {explanation.local_explanation_lime}")
    else:
        print("  ❌ No explanation generated.")

if __name__ == "__main__":
    test_xai()
