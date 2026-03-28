# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining get_roadmap.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.404647
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import asyncio
from engine.conversation import ConversationEngine
from engine.router import MandateRouter

async def run():
    print("\n--- Buddy's Thoughts ---")
    ce = ConversationEngine()
    router = MandateRouter()
    route = router.route_chat("tell me what is next and provide a roadmap for the system")
    try:
        reply = ce.process("tell me what is next and provide a roadmap for the system according to the latest developments (CognitiveDreamer, DeepIntrospector)", route, "system_session")
        print(vars(reply))
    except Exception as e:
        print(f"Error getting buddy trace: {e}")

asyncio.run(run())
