import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO)
sys.path.insert(0, '.')

from tooloo_v4_hub.organs.vertex_organ.vertex_logic import get_vertex_logic

async def test():
    logic = await get_vertex_logic()
    print('\n--- Logic Intent ---')
    print(await logic.garden_route({'logic': 0.9, 'coding': 0.8}, priority=1.5))
    print('\n--- Speed Intent ---')
    print(await logic.garden_route({'speed': 0.9, 'logic': 0.2}, priority=1.0))

asyncio.run(test())
