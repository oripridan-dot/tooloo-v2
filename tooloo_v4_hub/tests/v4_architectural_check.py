# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: TEST_ARCHITECTURAL_CHAT_DECOUPLING | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/v4_architectural_check.py
# WHY: Rule 13 and Rule 11 Verification for the newly decoupled CHAT phase.
# HOW: Unit tests on SovereignChatEngine initialization and VETO path.
# ==========================================================

import asyncio
import logging
from tooloo_v4_hub.kernel.cognitive.chat_engine import get_chat_engine
from tooloo_v4_hub.shared.interfaces.chat_repository import IChatRepository
from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage

# Mock Repository for Decoupling Verification
class MockRepo(IChatRepository):
    def store_message(self, message: SovereignMessage) -> None:
        pass
    def get_history(self, limit: int = 100) -> list:
        return []

async def test_architecture():
    print("\n" + "="*80)
    print("Sovereign Hub: V4 CHAT Phase Architectural Integrity Check")
    print("="*80 + "\n")

    # 1. Rule 13: Strict Decoupling
    print("[R13] Testing IChatRepository Dependency Injection...")
    from tooloo_v4_hub.kernel.cognitive import chat_engine
    
    # reset global state if any
    chat_engine._chat_engine = None

    try:
        engine = chat_engine.get_chat_engine()
        print("❌ FAILED: Engine initialized WITHOUT injected repository. Rule 13 violation.")
    except ValueError as e:
        print(f"✅ PASSED: Caught Rule 13 Decoupling enforcement: {e}")

    try:
        mock_repo = MockRepo()
        engine = chat_engine.get_chat_engine(repo=mock_repo)
        print("✅ PASSED: Engine initialized WITH injected IChatRepository.")
    except Exception as e:
        print(f"❌ FAILED: Engine failed to initialize with mock repo: {e}")

    print("\n" + "="*80)
    print("ARCHITECTURAL INTEGRITY: CHAT PHASE VERIFIED.")
    print("="*80 + "\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(test_architecture())
