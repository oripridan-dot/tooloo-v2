import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Ensure tooloo_v4_hub works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tooloo_v4_hub.kernel.cognitive.skill_forge import get_skill_forge
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus

async def run_fast_forge():
    print("\n🔨 --- FAST SKILL FORGE TEST ---")
    forge = get_skill_forge()
    nexus = get_mcp_nexus()
    
    skill_name = "text_reverser"
    intent = "A highly secure tool that reverses text. It must be efficient."
    
    print(f"[TEST] Requesting forge for '{skill_name}'...")
    success = await forge.forge_skill(skill_name, intent)
    
    if success:
        print("[SUCCESS] Skill successfully written!")
        print("\n[TEST] Executing via MCP Nexus JIT gateway...")
        # Since MCP Nexus looks in KnowledgeGateway which now checks the local skills dir:
        res = await nexus.call_tool("jit_skill", skill_name, {"text": "Gravity and Ouroboros"})
        print(f"[TEST] Result: {res}")
    else:
        print("[FAIL] Skill forge failed or was rejected by Crucible.")

if __name__ == "__main__":
    asyncio.run(run_fast_forge())
