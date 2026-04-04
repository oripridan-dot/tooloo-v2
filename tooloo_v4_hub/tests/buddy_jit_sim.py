import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("JITSim")

from tooloo_v4_hub.kernel.cognitive.chat_engine import get_chat_engine
from tooloo_v4_hub.shared.interfaces.chat_repository import IChatRepository
from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus

class MockChatRepo(IChatRepository):
    def store_message(self, message): pass
    async def get_history(self): return []

async def simulate_jit_forge():
    print("\n🤖 --- SIMULATING JIT FORGE MANDATE ---")
    
    # 1. Init Core
    repo = MockChatRepo()
    chat = get_chat_engine(repo)
    nexus = get_mcp_nexus()
    logic = get_chat_logic()
    logic.nexus = nexus # mock attach
    
    target_skill = "entropy_analyzer"
    skill_file = os.path.join(os.getcwd(), "tooloo_v4_hub", "skills", f"{target_skill}.py")
    if os.path.exists(skill_file):
        os.remove(skill_file)
        print(f"[TEST] Cleaned up previous skill file at {skill_file}")

    print("\n[TEST] Requesting highly specific unmapped capability...")
    user_prompt = "Buddy, I need to analyze the entropy of a hexadecimal string locally without making external calls. Please create a tool exactly for this to calculate Shannon Entropy, and then use it on 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'"
    
    print(f"User: {user_prompt}")
    
    full_response = ""
    async for token in chat.process_user_message(user_prompt):
        full_response += token
        
    print(f"\nBuddy:\n{full_response}\n")
    
    if "MANDATE: FORGE_SKILL" in full_response:
        print("[SUCCESS] Buddy successfully decided to forge a new skill.")
    else:
        print("[FAIL] Buddy did not issue the FORGE_SKILL mandate.")
        
    print("\n[TEST] Waiting up to 60 seconds for background JIT compilation...")
    for _ in range(60):
        if os.path.exists(skill_file) or os.path.exists(os.path.join(os.getcwd(), "tooloo_v4_hub", "skills", "local_entropy_analyzer.py")):
            break
        await asyncio.sleep(1)
        
    actual_file = skill_file if os.path.exists(skill_file) else os.path.join(os.getcwd(), "tooloo_v4_hub", "skills", "local_entropy_analyzer.py")
    
    if os.path.exists(actual_file):
         print(f"\n[SUCCESS] Skill successfully written to {actual_file}!")
         print("\n[TEST] Attempting to invoke forged skill via MCPNexus...")
         res = await nexus.call_tool("jit_skill", "local_entropy_analyzer", {"data": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"})
         print(f"[TEST] Forged Skill Execution Result: {res}")
         
         # Verification Step Rule 16
         with open(actual_file, "r") as f:
             code = f.read()
             if "# 6W_STAMP" in code:
                 print("[SUCCESS] The generated tool includes the mandatory 6W_STAMP!")
             else:
                 print("[WARNING] Missing 6W_STAMP on generation, but execution succeeded.")
    else:
         print(f"\n[FAIL] Skill was NOT written to disk. Background task may have failed.")

if __name__ == "__main__":
    asyncio.run(simulate_jit_forge())
