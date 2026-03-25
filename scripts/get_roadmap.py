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
