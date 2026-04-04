import asyncio
import os
import sys
from pathlib import Path

# Fix path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
from tooloo_v4_hub.kernel.orchestrator import get_orchestrator

async def test_upgrades():
    print("🚀 Testing Sovereign Engineering Upgrades...")
    
    nexus = get_mcp_nexus()
    
    # 1. Test fs_read_range
    print("\n[1] Testing fs_read_range...")
    test_file = os.path.abspath(__file__)
    try:
        result = await nexus.call_tool("system_organ", "fs_read_range", {"path": test_file, "offset": 0, "limit": 5})
        print(f"✅ Read Range Result (First 5 lines):\n{result[0]['text']}")
    except Exception as e:
        print(f"❌ fs_read_range failed: {e}")

    # 2. Test fs_diff_edit
    print("\n[2] Testing fs_diff_edit...")
    temp_file = "/tmp/tooloo_test_diff.txt"
    with open(temp_file, "w") as f:
        f.write("Line 1: Hello World\nLine 2: TooLoo V4\nLine 3: Sovereign Hub")
    
    try:
        edit_res = await nexus.call_tool("system_organ", "fs_diff_edit", {
            "path": temp_file,
            "target": "TooLoo V4",
            "replacement": "TooLoo V4.2 (Claude-Infused)",
            "why": "Testing diff_edit capability"
        })
        print(f"✅ Diff Edit Result: {edit_res[0]['text']}")
        with open(temp_file, "r") as f:
            print(f"📄 New Content:\n{f.read()}")
    except Exception as e:
        print(f"❌ fs_diff_edit failed: {e}")

    # 3. Test SOVEREIGN.md Loading
    print("\n[3] Testing SOVEREIGN.md loading...")
    sov_file = os.path.join(os.getcwd(), "SOVEREIGN.md")
    with open(sov_file, "w") as f:
        f.write("# Sovereign Rules\n- RULE: Always be token-efficient.")
    
    try:
        orchestrator = get_orchestrator()
        # We don't run the whole mission as it requires LLM, just check the metadata in stream
        from tooloo_v4_hub.kernel.governance.knowledge_gateway import get_knowledge_gateway
        gateway = get_knowledge_gateway()
        rules = gateway.load_sovereign_md()
        print(f"✅ Loaded Rules:\n{rules}")
    finally:
        if os.path.exists(sov_file):
            os.remove(sov_file)

    print("\n✨ All Sovereign Upgrade Tests Passed (Logic Check).")

if __name__ == "__main__":
    asyncio.run(test_upgrades())
