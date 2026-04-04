# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_TEST_FULL_SYSTEM_REAL_MODE.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/kernel/reality_check/test_full_system_real_mode.py
# WHEN: 2026-04-01T16:35:57.984295+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import asyncio
import sys
import os
import time

# Environment Setup
sys.path.insert(0, os.getcwd())

# NOTE: Orchestrator's __init__ currently calls get_nexus()
# Since get_nexus() is now async, I need to ensure the orchestrator is ready.
# I'll modify the orchestrator to have an async initialize() or similar.
# For now, I'll just ensure the test script prepares the nexus.
from tooloo_v4_hub.kernel.mcp_nexus import get_nexus
from tooloo_v4_hub.kernel.orchestrator import SovereignOrchestrator

async def run_full_system_verification():
    print("\n" + "="*60)
    print("TOO LOO V3: FULL-SYSTEM REAL-MODE VERIFICATION")
    print("="*60)
    
    # Pre-initialize Nexus
    await get_nexus()
    
    orchestrator = SovereignOrchestrator()
    
    # 1. Execute High-Value Industrialization Goal
    # This goal will trigger: Reasoning -> SOTA Ingestion -> Memory Storing -> Resolution Winning
    goal = "Industrialize the Federated Memory via SOTA search"
    print(f"Executing Goal: {goal}")
    
    async def status_callback(msg):
        print(f"  [STATUS] {msg}")
        
    results = await orchestrator.execute_goal(goal, {}, mode="PATHWAY_B", callback=status_callback)
    
    # 2. Verify Result Purity
    all_pure = all(r.get("status") == "success" for r in results)
    print(f"\nExecution Count: {len(results)}")
    print(f"Overall Purity: {'1.00 (GROUNDED)' if all_pure else 'DRIFT DETECTED'}")
    
    # 3. Perform Deep Audit & Vitality Index
    from tooloo_v4_hub.kernel.governance.audit import get_auditor
    auditor = get_auditor()
    
    print("\nInitiating Cryptographic Audit...")
    audit_report = await auditor.perform_audit()
    
    print(f"Audit Score: {audit_report['score']:.4f} ({audit_report['verified']}/{audit_report['total']} verified)")

    print("\nComputing Hub Vitality Index...")
    vitality_report = await auditor.calculate_vitality_index()
    print(f"Vitality Score: {vitality_report['vitality']:.4f}")
    print(f"  - Grounding: {vitality_report['grounding']:.2f}")
    print(f"  - Health: {vitality_report['health']:.2f}")

    if all_pure and vitality_report['vitality'] >= 0.9:
         print("\n✅ SYSTEM STATUS: SOVEREIGN (Level 5 Awakened)")
    else:
         print("\n⚠️ SYSTEM STATUS: STABILIZING")

    # 4. Generate Traceability Report for the Goal
    print("\nGenerating Traceability Report...")
    trace_report = await auditor.get_traceability_report(goal)
    print(f"Grounded Engrams Detected: {len(trace_report)}")
    for i, engram in enumerate(trace_report[:3]):
         print(f"  [{i+1}] ID: {engram['id']} | Relevance: {engram['score']:.2f}")

    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(run_full_system_verification())
