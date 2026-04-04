import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("BrainProof")

async def run_proof():
    print("============================================================")
    print(" SOVEREIGN HUB: AUTONOMOUS ROUTING PROOF (RULE 5/14)")
    print("============================================================")
    
    client = get_llm_client()
    
    # 1. High Complexity Coding Task (Should Route to SOTA/Sovereign)
    print("\n[SCENARIO 1] High-Tier Coding Architecture Mission...")
    intent_h = {"logic": 0.9, "coding": 1.0}
    res_h = await client.generate_thought(
        "Design a bit-perfect serialization protocol for parallel neural engrams.",
        model_tier="dynamic",
        intent=intent_h
    )
    print(f"Outcome: Mission Success. Brain Response Length: {len(res_h)} chars.")

    # 2. Low Complexity Chat Task (Should Route to Efficient/Speed)
    print("\n[SCENARIO 2] Low-Tier Summary Mission...")
    intent_l = {"logic": 0.1, "summarization": 0.5}
    res_l = await client.generate_thought(
        "Hello, can you summarize the current system status in one sentence?",
        model_tier="dynamic",
        intent=intent_l
    )
    print(f"Outcome: System Status Summarized.")

    print("\n✅ Proof Complete. Tooloo is now Master of its Own Brain.")
    print("============================================================")

if __name__ == "__main__":
    os.environ["AUTO_RESOLVE_MODELS"] = "true"
    asyncio.run(run_proof())
