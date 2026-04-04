# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_TEST_REGIONAL_SOVEREIGNTY.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tests/test_regional_sovereignty.py
# WHEN: 2026-04-01T16:35:57.947303+00:00
# WHY: Heal STAMP_PURITY_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import asyncio
import os
import sys
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus

async def test_sovereign_alignment():
    print("--- 🚀 Sovereign Alignment Verification Pulse ---")
    
    # 1. Init Hub Infrastructure
    llm = get_llm_client()
    await llm.initialize()
    
    active_project = os.getenv("ACTIVE_SOVEREIGN_PROJECT")
    print(f"Hub Active Project: {active_project}")
    
    # 2. Init Nexus and tether organs
    nexus = get_mcp_nexus()
    await nexus.initialize_default_organs()
    
    # 3. Test Anthropic Organ (Claude 3.7)
    print("Testing Anthropic Organ (Thinking Pulse)...")
    try:
        res = await nexus.call_tool("anthropic_organ", "thinking_chat", {
            "prompt": "Identify your model version.",
            "thinking_budget": 1024
        })
        print(f"Anthropic Response: {res[0]['text'][:300]}...")
        print("✅ Anthropic Organ: Online/Aligned.")
    except Exception as e:
        print(f"❌ Anthropic Organ: Failed to pulse: {e}")

    # 4. Test Vertex Organ (Gemini 3.1 Pro)
    print("Testing Vertex Organ (Gemini Pulse)...")
    try:
        res = await nexus.call_tool("vertex_organ", "provider_chat", {
            "prompt": "Identify your model version.",
            "model": "gemini-3.1-pro-preview",
            "provider": "google"
        })
        print(f"Vertex Response: {res}...")
        print("✅ Vertex Organ: Online/Aligned.")
    except Exception as e:
        print(f"❌ Vertex Organ: Failed to pulse: {e}")

if __name__ == "__main__":
    asyncio.run(test_sovereign_alignment())