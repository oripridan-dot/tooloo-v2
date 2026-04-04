# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: test_jit_grounding.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/reality_check/test_jit_grounding.py
# WHEN: 2026-04-03T16:08:23.413953+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
import sys
import os

# Environment Setup
sys.path.insert(0, os.getcwd())
logging.basicConfig(level=logging.INFO, format="%(message)s")

from tooloo_v4_hub.kernel.cognitive.knowledge_crawler import get_crawler

async def audit_jit_rescue():
    print("\n" + "="*60)
    print("TOO LOO V3: JIT GROUNDING HEARTBEAT")
    print("="*60)
    
    crawler = get_crawler()
    
    # 1. Test rescue for a SOTA topic
    # In this standalone test, it will fail to call 'search_web' and should trigger the fallback
    print("Triggering JIT Rescue for 'Federated MCP Purity'...")
    t0 = asyncio.get_event_loop().time()
    result = await crawler.jit_rescue("Federated MCP Purity")
    elapsed = asyncio.get_event_loop().time() - t0
    
    print(f"\nStatus: {result.get('status')}")
    print(f"Time Taken: {elapsed:.2f}s")
    
    findings = result.get('recovered_context', {}).get('findings', 'NONE')
    print(f"Recovered Findings: {findings[:100]}...")
    
    # Check if fallback logic was used
    if "Internal SOTA Matrix" in findings or "Architecture: Pure Sovereign Hub" in findings:
         print("✅ Fallback: Internal SOTA Matrix successfully engaged.")
    
    if result.get('status') == 'success':
        print("\n✅ JIT Grounding HEARTBEAT: STABLE.")
    else:
        print("\n❌ JIT Grounding HEARTBEAT: FAULT DETECTED.")

    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(audit_jit_rescue())
