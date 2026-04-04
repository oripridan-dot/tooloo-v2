import asyncio
import os
from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic, SovereignConstitutionException

async def test_zero_trust():
    print("Testing Zero-Trust Ingestion Protocol...")
    logic = await get_memory_logic()
    
    # 1. Invalid Data (Missing Stamp)
    invalid_data = {"text": "Ghost content"}
    try:
        print("Test 1: Attempting to store engram without 6W stamp...")
        await logic.store_engram("ghost_001", invalid_data)
        print("FAILED: Ingested ghost data without stamp.")
    except SovereignConstitutionException as e:
        print(f"SUCCESS: Rejected missing stamp: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected exception: {e}")

    # 2. Invalid Data (Generic 'Hub' stamp - Rule 10 breach)
    invalid_stamp = {
        "data": {"text": "Generic content"},
        "stamp": {"who": "Hub", "what": "Internal", "where": "logic.py", "why": "test", "how": "direct"}
    }
    try:
        print("\nTest 2: Attempting to store engram with generic 'Hub' stamp...")
        await logic.store_engram("ghost_002", invalid_stamp["data"])
        print("FAILED: Ingested ghost data with generic stamp.")
    except SovereignConstitutionException as e:
        print(f"SUCCESS: Rejected generic stamp: {e}")

    # 3. Valid Data
    valid_data = {
        "text": "Validated architecture engram",
        "source": "manual_validation_test",
        "stamp": {
            "who": "Architect-Harness",
            "what": "VALIDATION_TEST",
            "where": "test_zero_trust.py",
            "why": "Verify Rule 10 Enforcement",
            "how": "Unit Test"
        }
    }
    try:
        print("\nTest 3: Attempting to store valid engram...")
        res = await logic.store_engram("valid_001", valid_data)
        print(f"SUCCESS: Ingested valid data: {res['status']}")
    except Exception as e:
        print(f"FAILED: Rejected valid data: {e}")

if __name__ == "__main__":
    asyncio.run(test_zero_trust())
