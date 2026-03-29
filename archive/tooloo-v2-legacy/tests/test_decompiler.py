import sys
import os
import numpy as np
import bs4

# Ensure engine is in path
sys.path.append(os.getcwd())

from engine.decompiler import Decompiler
from engine.engram import Engram

def test_deconstruction_pipeline():
    # 1. Provide a Legacy Support Center HTML
    legacy_html = """
    <html>
        <head><title>Zendesk Legacy Support Portal</title></head>
        <body>
            <div id="customer_header">Welcome, Customer</div>
            <form id="ticket_submission">
                <input type="text" name="subject" placeholder="What's the issue?">
                <textarea name="description"></textarea>
                <button type="submit">Submit Ticket</button>
            </form>
            <div class="footer">Standard Support © 2012</div>
        </body>
    </html>
    """
    url = "https://support.legacy-retailer.com"

    # 2. Decompile to Engram
    decompiler = Decompiler()
    engram = decompiler.decompile_html(legacy_html, url)
    
    print("=== PHASE 1: DECONSTRUCTION ===")
    print(f"6W Context (What): {engram.context.what}")
    print(f"6W Context (Who): {engram.context.who}")
    print(f"Inferred Emergence (Success): {engram.em_actual.val[0]}")
    print(f"Inferred Intent (Efficiency): {engram.intent.values['Efficiency']}")
    
    # Verify vector dimensions
    vec = engram.vectorize()
    assert vec.shape == (22,)
    print(f"Successfully vectorized engram to 22D: {vec[:5]}...")

    # 3. Phase 2: Create Baseline Clone (Simulated)
    # Probing the engram for 1:1 reconstruction
    # E.g., verifying that if we "processed" this engram through the same E_sim, 
    # we get the same EM_actual.
    em_pred = engram.process(decompiler.env_matrix)
    print("\n=== PHASE 2: BASELINE CLONE VERIFICATION ===")
    print(f"Actual Emergence:    {engram.em_actual.val}")
    print(f"Predicted Emergence: {em_pred.val}")
    
    # Since EM = D * E and D = EM * pinv(E), predicted should match actual exactly (if span permits)
    np.testing.assert_array_almost_equal(engram.em_actual.val, em_pred.val, decimal=5)
    print("Proof: Baseline Clone (C+I) perfectly reproduces the observed Legacy Emergence.")

    # 4. Phase 3: The TooLoo Upgrade
    upgraded_engram = decompiler.generate_upgrade_engram(engram)
    print("\n=== PHASE 3: TOOLOO STAMPED UPGRADE ===")
    print(f"Upgraded Intent (Efficiency): {upgraded_engram.intent.values['Efficiency']}")
    print(f"Upgraded Context (How):        {upgraded_engram.context.how}")
    
    # Process through E_sim to see predicted results
    em_upgraded = upgraded_engram.process(decompiler.env_matrix)
    print(f"Predicted Upgraded Emergence: {em_upgraded.val}")
    
    print("\nSUCCESS: The Decompiler Matrix has successfully deconstructed, cloned, and upgraded the legacy system.")

if __name__ == "__main__":
    test_deconstruction_pipeline()
