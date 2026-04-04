# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: TEST_PSYCHE_SYNC | Version: 1.0.0
# WHERE: tests/test_psyche_sync.py
# WHEN: 2026-04-03T15:45:00.000000
# WHY: Rule 16: Evaluation Delta (Verification)
# HOW: Execution of the Sync Pulse with content retrieval validation
# ==========================================================

import asyncio
import logging
from pathlib import Path
from tooloo_v4_hub.kernel.governance.living_map import get_living_map
from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic
from tooloo_v4_hub.kernel.cognitive.psyche_syncer import get_psyche_syncer

async def test_deep_retrieval_pulse():
    print("--- Psyche Sync Verification Initiated ---")
    
    # 1. Setup - Ensure Kernel and GEMINI.md are mapped
    living_map = get_living_map()
    living_map.rebuild_topography(root_dir="tooloo_v4_hub/kernel")
    
    # Manually register GEMINI.md
    from tooloo_v4_hub.kernel.governance.stamping import StampingEngine
    gemini_path = Path("GEMINI.md")
    if gemini_path.exists():
        meta = StampingEngine.extract_metadata(gemini_path.read_text())
        living_map.register_node(str(gemini_path), meta or {"what": "Constitution", "type": "kernel"})
    
    # 2. Trigger Sync
    syncer = get_psyche_syncer()
    print("Executing Targeted Hub Index Pulse...")
    await syncer.sync_all()
    
    # 3. Verify Memory Retrieval (Semantic)
    memory = await get_memory_logic()
    
    # Query for a Rule (Rule 11) from GEMINI.md
    query = "Rule 11 Anti-Band-Aid"
    print(f"Querying Memory for: '{query}'")
    results = await memory.query_memory(query, top_k=5)
    
    print(f"Retrieval Count: {len(results)}")
    found_rule_11 = False
    for res in results:
        engram = await memory.retrieve(res["id"])
        if not engram: continue
        chunk_text = engram.get("text", "")
        print(f"Match [{res['score']:.4f}] SOURCE: {engram.get('source')} | TEXT: {chunk_text[:200]}...")
        if "Rule 11" in chunk_text and "Anti-Band-Aid" in chunk_text:
            found_rule_11 = True
            print(f"SUCCESS: Rule 11 retrieved (Score: {res['score']:.4f})")
            break
    
    assert found_rule_11, "Failed to retrieve Rule 11 from indexed content."
    
    # 4. Verify Update Logic (Modify a file and re-sync)
    test_file = Path("tests/psyche_test_node.py")
    test_file.write_text("# 6W_STAMP\n# WHAT: TEST_NODE\n# WHY: Verification\n\ndef unique_pulse_function_99():\n    return 'SOTA'")
    
    print("\nRegistering new test node...")
    living_map.register_node(str(test_file), {"what": "TEST_NODE", "type": "test"})
    
    # Deterministic sync for test verification
    print("Awaiting deterministic sync...")
    await syncer.sync_node(str(test_file))
    
    print("Querying for unique function...")
    query_2 = "unique_pulse_function_99"
    results_2 = await memory.query_memory(query_2, top_k=5)
    
    found_node = False
    for res in results_2:
        engram_2 = await memory.retrieve(res["id"])
        print(f"Match [{res['score']:.4f}] from {engram_2.get('source')}: {engram_2.get('text')[:100]}...")
        if "unique_pulse_function_99" in engram_2.get("text", ""):
            found_node = True
            break
            
    assert found_node, "Failed to retrieve newly indexed function."
    print(f"SUCCESS: New node indexed and retrieved (Score: {res['score']:.4f})")
    
    # Cleanup
    if test_file.exists():
        test_file.unlink()
    print("\n--- Verification COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(test_deep_retrieval_pulse())
