# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_TEST_CLAUDE_4_6.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tests/test_claude_4_6.py
# WHEN: 2026-04-01T16:35:57.946496+00:00
# WHY: Heal STAMP_PURITY_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import asyncio
import os
import sys
from tooloo_v4_hub.organs.anthropic_organ.anthropic_logic import VertexAnthropicLogic

async def test_thinking_pulse():
    print("--- 🧠 Claude 4.6 SOTA Thinking Pulse ---")
    
    project_id = "too-loo-zi8g7e" # Stable node
    region = "us-east5"
    
    # Ensure credentials are set
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/service-account.json"
    
    print(f"Node: {project_id} @ {region}")
    logic = VertexAnthropicLogic(project_id=project_id, region=region)
    
    messages = [
        {"role": "user", "content": "Analyze the impact of Rule 12 (Self-Healing) on the autopoietic stability of the TooLoo Sovereign Hub."}
    ]
    
    print("Pulse SENT. Thinking Phase ACTIVE...")
    try:
        res = await logic.thinking_chat(
            messages=messages,
            thinking_budget=2048,
            model="claude-sonnet-4-6@default"
        )
        
        if res["status"] == "success":
            print("\n--- 🧠 THINKING ---\n")
            print(res["thinking"][:500] + "...")
            print("\n--- 💬 RESPONSE ---\n")
            print(res["content"])
            print("\n✅ Claude 4.6 SOTA: VERIFIED.")
        else:
            print(f"❌ Fault: {res.get('error')}")
            
    except Exception as e:
        print(f"❌ Execution Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_thinking_pulse())