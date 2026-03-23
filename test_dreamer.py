import asyncio
from engine.cognitive_dreamer import CognitiveDreamer
from unittest.mock import Mock

async def main():
    store = Mock()
    item1 = Mock()
    item1.content = 'System event A'
    item1.id = 'id1'
    item2 = Mock()
    item2.content = 'System event B'
    item2.id = 'id2'
    store.search.return_value = [item1, item2]
    
    garden = Mock()
    async def mock_call(*args, **kwargs):
        return 'insight: configure threading better'
    garden.call = mock_call
    
    dreamer = CognitiveDreamer(store, Mock(), garden)
    r = await dreamer.run_dream_cycle()
    print("Report:", r)

if __name__ == "__main__":
    asyncio.run(main())
