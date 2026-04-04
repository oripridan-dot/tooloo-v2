# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_TEST_CLOUD_V4.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/kernel/reality_check/test_cloud_v4.py
# WHEN: 2026-04-01T16:35:57.985074+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: TEST_CLOUD_V4 | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/reality_check/test_cloud_v4.py
# WHY: Rule 16 - Verifying the Cloud Manifestation of the Sovereign Hub.
# PURITY: 1.00
# ==========================================================

import requests
import json
import os

HUB_URL = "https://too-loo-v4-hub-gru3xdvw6a-uc.a.run.app"
SOVEREIGN_KEY = os.getenv("SOVEREIGN_KEY", "SOVEREIGN_HUB_2026_V3")

def run_tests():
    print(f"--- INITIATING CLOUD VERIFICATION PULSE: {HUB_URL} ---")
    
    # 1. Connectivity Test
    try:
        res = requests.get(f"{HUB_URL}/health")
        print(f"Connectivity Check: {res.status_code} | {res.json()}")
    except Exception as e:
        print(f"Connectivity Check FAILED: {e}")
        return

    # 2. Security Test (Unauthorized Access)
    res = requests.get(f"{HUB_URL}/vitality")
    print(f"Security Check (No Key): {res.status_code} | (Expected: 422/403)")

    # 3. Functional Test (Authorized Access)
    headers = {"X-Sovereign-Key": SOVEREIGN_KEY}
    res = requests.get(f"{HUB_URL}/vitality", headers=headers)
    print(f"Functional Check (Authorized): {res.status_code}")
    if res.status_code == 200:
        print(f" Vitality Index: {res.json()}")
    else:
        print(f" Error details: {res.text}")

    # 4. Execution Check (Simple Goal)
    payload = {
        "goal": "Verify Sovereign Identity Pulse in the cloud.",
        "context": {"environment": "cloud", "jit_boosted": False},
        "mode": "MACRO"
    }
    res = requests.post(f"{HUB_URL}/execute", headers=headers, json=payload)
    print(f"Execution Check: {res.status_code}")
    if res.status_code == 200:
        print(f" Execution Results: {json.dumps(res.json(), indent=2)}")
    else:
        print(f" Error details: {res.text}")

if __name__ == "__main__":
    run_tests()
