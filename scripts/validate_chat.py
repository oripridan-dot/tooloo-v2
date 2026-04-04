import asyncio
import logging
import os

# Ensure the updated .env is physically loaded
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key.strip()] = val.strip().strip("'\"")

from tooloo_v4_hub.kernel.cognitive.chat_engine import get_chat_engine
from tooloo_v4_hub.shared.interfaces.chat_repository import IChatRepository
from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage
from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry
from typing import List

logging.getLogger().setLevel(logging.ERROR)

class DummyRepo(IChatRepository):
    def __init__(self):
        self.messages = []
    
    async def store_message(self, message: SovereignMessage):
        self.messages.append(message)

    async def get_history(self) -> List[SovereignMessage]:
        return self.messages
        
    async def fetch_recent(self, limit=20) -> List[dict]:
        return [{"role": getattr(m, 'role', 'assistant'), "content": getattr(m, 'content', '')} for m in self.messages[-limit:]]

async def validate():
    print("=== INITIALIZING BUDDY CHAT ENGINE ===")
    repo = DummyRepo()
    reg = get_cognitive_registry()
    reg.update_state("default", "Architectural Review")
    engine = get_chat_engine(repo)
    
    print("\n[User]: Buddy, analyze our current portal state.")
    print("[Buddy]: ", end="")
    async for token in engine.process_user_message("Buddy, analyze our current portal state."):
        print(token, end="", flush=True)
    print("\n")
    
    print("=== INFLATING HISTORY TO TRIGGER SDK COMPACTION ===")
    for i in range(16):
        dummy_msg = SovereignMessage(role="user", content=f"This is a bulky history turn number {i}. Contains verbose information we do not need to keep fully active.")
        engine.history.append(dummy_msg)
        
    print("\n[User]: Buddy, please evaluate the architecture.")
    print("[Buddy]: ", end="")
    async for token in engine.process_user_message("Buddy, please evaluate the architecture."):
        print(token, end="", flush=True)
    print("\n")
    
    print("=== POST-COMPACTION METRICS ===")
    print(f"Total History Elements: {len(engine.history)}")
    for i, msg in enumerate(engine.history):
        role = getattr(msg, 'role', 'assistant')
        content = getattr(msg, 'content', '')
        print(f"[{i}] {role.upper()}: {content[:100]}...")

if __name__ == "__main__":
    asyncio.run(validate())
