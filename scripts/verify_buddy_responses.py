# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: VERIFY_BUDDY_RESPONSES | Version: 1.0.0
# WHERE: scripts/verify_buddy_responses.py
# WHY: Demonstrate Buddy's reasoning quality under the new 12-Primitive Constitution.
# HOW: Orchestrated LLM reasoning pulse.
# ==========================================================

import asyncio
import logging
import os
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client

async def verify_buddy():
    print("\n" + "="*80)
    print("BUDDY REASONING VERIFICATION: 12-PRIMITIVE CONSTITUTION")
    print("="*80 + "\n")

    llm = get_llm_client()
    
    # Prompting Buddy to explain the shift and a specific primitive
    prompt = """
    We have just transitioned to the 'Engineering-First' 12-Primitive Constitution.
    Explain why 'Primitive 12: Agent Type System (Sharp Roles)' is critical for preventing 'Minion Cloning' and operational drift. 
    Also, how does the 'Simplicity Mandate' affect our architectural choices?
    """
    
    print("Buddy is thinking...")
    thought = await llm.generate_thought(
        prompt=prompt,
        system_instruction="You are Buddy, the Engineering-First Principal Systems Architect of TooLoo V4."
    )
    
    print("\n" + "-"*40)
    print("BUDDY'S RESPONSE:")
    print("-"*40)
    print(thought)
    print("-"*40 + "\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(verify_buddy())
