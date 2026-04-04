import asyncio
import sys
sys.path.insert(0, '.')
from tooloo_v4_hub.organs.system_organ.mcp_server import grep_search

async def run_test():
    print("Testing case-insensitive grep tool...")
    res = await grep_search("DeF GrEp_sEaRcH", "tooloo_v4_hub/organs/system_organ")
    print("\nCase Insensitive Result:")
    print(res)
    
    print("\nTesting case-sensitive grep tool...")
    res2 = await grep_search("DeF GrEp_sEaRcH", "tooloo_v4_hub/organs/system_organ", case_sensitive=True)
    print("\nCase Sensitive Result:")
    print(res2)

asyncio.run(run_test())
