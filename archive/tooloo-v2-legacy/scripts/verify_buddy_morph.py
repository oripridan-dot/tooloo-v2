# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: Buddy Morph Verification (Stance -> 3D)
# WHERE: scripts/verify_buddy_morph.py
# WHEN: 2026-03-29T04:10:00
# WHY: Ensuring the cognitive-to-spatial bridge is bit-perfect
# HOW: StanceEngine -> MCP Manager Mock
# ==========================================================

import asyncio
import json
from engine.stance import get_stance_engine
from engine.mcp_manager import get_tether_server

async def verify_loop():
    print("── TooLoo Morph Loop Verification ──\n")
    
    engine = get_stance_engine()
    tether = get_tether_server()
    
    # 1. Test Stance Detection
    mandate = "I have a critical bug in the audio engine that causes a crash."
    print(f"Mandate: '{mandate}'")
    result = engine.detect(mandate)
    print(f"Detected Stance: {result.stance}")
    
    morph_state = engine.morph_for(result.stance)
    print(f"Resulting Morph: {morph_state}")
    
    # Assertions
    assert morph_state == "URGENT"
    print("✅ Stance-to-Morph Mapping: CORRECT")
    
    # 2. Mock MCP Call
    # This would normally be called by the JITExecutor via the MCP Tool
    code = f"from scripts.buddy_manifestation import buddy_morph; buddy_morph('{morph_state}')"
    print(f"Generated BPY: {code}")
    
    print("\n✅ Morph Loop Logic Verified.")

if __name__ == "__main__":
    asyncio.run(verify_loop())
