# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: SCRIPT_FIRESTORE_DIAGNOSTIC | Version: 1.0.0
# WHERE: scripts/firestore_diagnostic.py
# WHEN: 2026-04-03T17:40:00.000000
# WHY: Rule 16/18 Verification of Cloud-Native Persistence
# ==========================================================

import asyncio
import os
import logging
from tooloo_v4_hub.organs.memory_organ.firestore_persistence import get_firestore_persistence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FirestoreDiag")

async def test_connectivity():
    print("\n" + "="*60)
    print(" SOVEREIGN HUB: FIRESTORE CONNECTIVITY DIAGNOSTIC")
    print("="*60)
    
    project_id = os.getenv("ACTIVE_SOVEREIGN_PROJECT", "too-loo-zi8g7e")
    region = os.getenv("ACTIVE_SOVEREIGN_REGION", "me-west1")
    
    print(f"Target Project: {project_id}")
    print(f"Target Region:  {region}")
    
    try:
        fs = get_firestore_persistence()
        print(f"[SUCCESS] Firestore Client Initialized. DB: {fs.db.database}")
        
        # Test write
        test_id = "diag_pulse_test"
        test_data = {"msg": "Sovereign Diagnostic Pulse", "status": "PURE"}
        print(f"Attempting test write to 'psyche_medium'...")
        await fs.store_engram(test_id, test_data, layer="medium")
        print("[SUCCESS] Write operation confirmed.")
        
        # Test read
        print(f"Attempting test read of '{test_id}'...")
        engram = await fs.retrieve_engram(test_id)
        if engram and engram.get("status") == "PURE":
            print("[SUCCESS] Read operation confirmed. Data matches.")
        else:
            print("[FAILURE] Read operation returned inconsistent data.")
            
        # Clean up
        print("Cleaning up diagnostic engram...")
        await fs.delete_engrams_by_prefix(test_id)
        print("[SUCCESS] Cleanup complete.")
        
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Firestore Communication Severed: {e}")
        print("Hint: Check ADC (gcloud auth application-default login) or Project Permissions.")
        
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_connectivity())
