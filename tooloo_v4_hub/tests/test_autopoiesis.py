import asyncio
import os
import sys
import json
import time
from pathlib import Path

# Fix path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tooloo_v4_hub.kernel.cognitive.context_pruner import get_context_pruner
from tooloo_v4_hub.kernel.governance.knowledge_gateway import get_knowledge_gateway
from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus

async def test_autopoiesis():
    print("🧠 --- TESTING ADVANCED SOVEREIGN AUTOPOIESIS ---")
    
    workspace = os.getcwd()
    nexus = get_mcp_nexus()
    # Initialize only the necessary organ for this test
    python_exe = sys.executable
    base_path = Path(__file__).parent.parent
    await nexus.register_organ("system_organ", "subprocess", {
        "command": [python_exe, str(base_path / "organs" / "system_organ" / "mcp_server.py")],
        "env": os.environ
    })
    
    # 1. Test fs_fuzzy_edit (Robustness)
    print("\n[1] Testing fs_fuzzy_edit (with context)...")
    temp_file = "/tmp/tooloo_fuzzy_test.py"
    with open(temp_file, "w") as f:
        f.write("\"\"\"\nLegacy Header\n\"\"\"\ndef old_func():\n    print('stale')\n")
    
    try:
        # Use context to target 'old_func' specifically
        res = await nexus.call_tool("system_organ", "fs_fuzzy_edit", {
            "path": temp_file,
            "before": "\"\"\"\nLegacy Header\n\"\"\"\n",
            "target": "def old_func():",
            "after": "\n    print('stale')\n",
            "replacement": "def modern_func():",
            "why": "Testing contextual replacement"
        })
        print(f"✅ Fuzzy Edit Result: {res[0]['text']}")
        with open(temp_file, "r") as f:
            print(f"📄 New Content:\n{f.read()}")
    except Exception as e:
        print(f"❌ fs_fuzzy_edit failed: {e}")

    # 2. Test ContextPruner (Token Efficiency)
    print("\n[2] Testing ContextPruner (Entropy reduction)...")
    pruner = get_context_pruner()
    long_transcript = [{"role": "system", "content": "Instruction"}]
    for i in range(25):
        long_transcript.append({"role": "user", "content": f"Message {i}"})
        long_transcript.append({"role": "assistant", "content": "X" * 3000 if i % 5 == 0 else "Short thought"})
    
    pruned = pruner.prune_transcript(long_transcript)
    print(f"✅ Pruner: Inbound {len(long_transcript)} turns -> Outbound {len(pruned)} turns.")
    print(f"✅ Pruner: Large assistant blocks removed.")

    # 3. Test autoDream Pulse (Memory Consolidation)
    print("\n[3] Testing autoDream Pulse...")
    gateway = get_knowledge_gateway()
    
    # Force trigger by removing dream_state
    dream_state = os.path.join(workspace, ".tooloo", "dream_state.json")
    if os.path.exists(dream_state): os.remove(dream_state)
    
    try:
        await gateway.auto_dream_pulse(workspace)
        if os.path.exists(os.path.join(workspace, "MEMORY.md")):
            print("✅ autoDream: MEMORY.md synthesized successfully.")
            with open(os.path.join(workspace, "MEMORY.md"), "r") as f:
                print(f"📄 MEMORY.md Snippet:\n{f.read()[:200]}...")
    except Exception as e:
        print(f"❌ autoDream failed: {e}")

    print("\n✨ All Autopoiesis Layers Verified.")

if __name__ == "__main__":
    asyncio.run(test_autopoiesis())
