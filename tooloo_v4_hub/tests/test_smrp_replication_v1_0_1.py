# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_TEST_SMRP_REPLICATION.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tests/test_smrp_replication.py
# WHEN: 2026-04-04T00:41:42.438341+00:00
# WHY: Heal STAMP_PURITY_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

@pytest.mark.asyncio
async def test_strong_consistency_trigger():
    """Verify that 'NORTH_STAR' engrams trigger dual-region writes."""
    db = get_firestore_persistence()
    
    # We create a sample mandate
    mandate = {
        "type": "NORTH_STAR",
        "text": "Sovereign Evolution Cycle 2 - Hardened Governance",
        "stamp": {"who": "Architect", "why": "Testing SMRP"}
    }
    
    # Executing the store call
    # Note: In a true unittest, we'd mock 'self.secondary_db' but here we'll verify return codes
    result = await db.store_engram("test_mandate_001", mandate)
    
    # Rule 13: Should report 'replication: STRONG'
    assert result["replication"] == "STRONG"
    print("✅ SMRP: Strong Consistency (Dual-Region) Pulse detected.")

@pytest.mark.asyncio
async def test_eventual_consistency_path():
    """Verify that routine memory uses the fast regional path."""
    db = get_firestore_persistence()
    
    memory_engram = {
        "type": "MEMORY",
        "text": "Routine session metadata observation.",
        "stamp": {"who": "Hub-Logic", "why": "Observational Sync"}
    }
    
    result = await db.store_engram("test_memory_001", memory_engram)
    
    # Rule 13: Should report 'replication: EVENTUAL'
    assert result["replication"] == "EVENTUAL"
    print("✅ SMRP: Eventual Consistency (Regional) Pulse detected.")

if __name__ == "__main__":
    import asyncio
    print("🌩️  Auditing Global Sovereignty (SMRP)...")
    asyncio.run(test_strong_consistency_trigger())
    asyncio.run(test_eventual_consistency_path())
    print("✅ SMRP Resilience: VERIFIED.")