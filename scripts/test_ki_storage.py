import asyncio
import logging
from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic

logging.basicConfig(level=logging.INFO)

async def test_ki():
    memory = await get_memory_logic()
    print("Initiating KI Storage Test...")
    res = await memory.store_knowledge_item(
        ki_id="test_mandate_001",
        decision="Formalize Knowledge Items (KIs)",
        rationale="Buddy Mandate for Sprint Completion",
        impact={"tech_debt": "Low", "purity": 1.0}
    )
    print(f"KI Storage Result: {res}")
    
    # Query it back
    kis = await memory.query_knowledge_base("Formalize")
    print(f"Query Result (KIs): {len(kis)} items found.")
    for ki in kis:
        print(f"- {ki['id']}: {ki.get('score')}")

if __name__ == "__main__":
    asyncio.run(test_ki())
