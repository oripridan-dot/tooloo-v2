# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_TEST_COGNITIVE_DYNAMICS.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tests/test_cognitive_dynamics.py
# WHEN: 2026-04-03T10:37:24.394291+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append("/Users/oripridan/ANTIGRAVITY/tooloo-v2")

from tooloo_v4_hub.kernel.cognitive.chat_engine import get_chat_engine
from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry

async def test_dynamics():
    print("--- TESTING COGNITIVE DYNAMICS ---")
    engine = get_chat_engine()
    registry = get_cognitive_registry()
    
    # Test 1: EXPLORE intent
    print("\n[Test 1] EXPLORE Intent...")
    response = await engine.process_user_message("Why is Rule 11 important for the Sovereign Hub?")
    state = registry.get_state()
    print(f"Detected Intent: {state.intent_vector}")
    print(f"Cognitive Load: {state.cognitive_load:.2f}")
    
    # Test 2: EXECUTE intent
    print("\n[Test 2] EXECUTE Intent...")
    response = await engine.process_user_message("Build a new component for the design studio.")
    state = registry.get_state()
    print(f"Detected Intent: {state.intent_vector}")
    
    # Test 3: CRITIQUE intent
    print("\n[Test 3] CRITIQUE Intent...")
    response = await engine.process_user_message("This is wrong, the Purity score should be higher.")
    state = registry.get_state()
    print(f"Detected Intent: {state.intent_vector}")
    print(f"Resonance: {state.resonance:.2f}")

if __name__ == "__main__":
    asyncio.run(test_dynamics())
