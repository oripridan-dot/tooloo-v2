import asyncio
import os
import sys

# Add project root to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tooloo_v4_hub.kernel.governance.knowledge_gateway import get_knowledge_gateway
from tooloo_v4_hub.kernel.governance.sota_benchmarker import get_benchmarker
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
from tooloo_v4_hub.kernel.cognitive.design_knowledge_injector import get_design_injector

async def test():
    print("🚀 [1] Gateway Fetch...")
    gateway = get_knowledge_gateway()
    try:
        data = await gateway.fetch_json("sota_registry")
        print(f"Data fetched: {data}")
    except Exception as e:
        print(f"Fetch failed: {e}")

    print("\n[2] Benchmarker Audit...")
    bench = get_benchmarker()
    try:
        report = await bench.run_full_audit()
        print(f"Audit Complete. SVI={report.get('svi')}")
    except Exception as e:
        print(f"Audit Failed: {e}")

    print("\n[3] Design Injector...")
    injector = get_design_injector()
    try:
        ctx = await injector.get_design_context()
        print(f"Context: {ctx[:60]}...")
    except Exception as e:
        print(f"Injector Failed: {e}")

    print("\n[4] MCP Nexus Intercept...")
    nexus = get_mcp_nexus()
    try:
        await nexus.call_tool("jit_skill", "unknown_missing", {})
    except Exception as e:
        print(f"Intercept Exception (Expected): {e}")

if __name__ == "__main__":
    asyncio.run(test())
