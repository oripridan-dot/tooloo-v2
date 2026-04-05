"""
test_memory_tiers.py
WHO : TooLoo Sovereign Hub
WHAT: Validates the 3-tier memory system (Hot / Warm / Cold) for both TooLoo and Buddy.
WHY : Rule 0 — no ghost code. Every tier must demonstrably work before it ships.

Tiers under test:
  T1 HOT  — in-process dict (GlobalContext.state for TooLoo, private dict for Buddy)
  T2 WARM — session-scoped TTL store (WarmStore)
  T3 COLD — file-backed KnowledgeBank (knowledge_lessons.json)
"""

import asyncio
import time
import os
import json
import sys
import logging
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tooloo.core.memory import MemorySystem, WarmStore
from src.tooloo.core.mega_dag import (
    ContinuousMegaDAG, DagNode, NodeType, AbstractOperator,
    NodeResult, GlobalContext, KnowledgeBank
)

logging.basicConfig(level=logging.WARNING, format="%(name)s - %(levelname)s - %(message)s")

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
HDR  = "\033[94m"
RST  = "\033[0m"

_all_passed = True

def check(label: str, condition: bool):
    global _all_passed
    status = PASS if condition else FAIL
    print(f"  {status}  {label}")
    if not condition:
        _all_passed = False


# ---------------------------------------------------------------------------
# Unit: WarmStore (Tier 2)
# ---------------------------------------------------------------------------
def test_warm_store():
    print(f"\n{HDR}── WarmStore (Tier 2) ──{RST}")
    ws = WarmStore()

    ws.write("alpha", 42, ttl_seconds=10)
    check("read existing key", ws.read("alpha") == 42)
    check("read missing key returns None", ws.read("missing") is None)

    ws.write("beta", "ephemeral", ttl_seconds=0.01)
    time.sleep(0.05)
    check("expired key returns None", ws.read("beta") is None)

    ws.write("gamma", [1, 2, 3], ttl_seconds=60)
    evicted = ws.evict_expired()
    check("evict_expired removes nothing live", evicted == 0)

    ws.write("dead1", "x", ttl_seconds=0.01)
    ws.write("dead2", "y", ttl_seconds=0.01)
    time.sleep(0.05)
    evicted = ws.evict_expired()
    check("evict_expired removes 2 stale entries", evicted == 2)

    snap = ws.snapshot()
    check("snapshot only contains live entries", set(snap.keys()) == {"alpha", "gamma"})


# ---------------------------------------------------------------------------
# Unit: MemorySystem cascade read (T1 → T2 → T3)
# ---------------------------------------------------------------------------
def test_memory_system_cascade():
    print(f"\n{HDR}── MemorySystem cascade read ──{RST}")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({"test:cold_key": "from_cold"}, f)
        cold_path = f.name

    try:
        hot = {}
        mem = MemorySystem.__new__(MemorySystem)
        mem.namespace = "test"
        mem._hot = hot
        from src.tooloo.core.memory import WarmStore
        mem._warm = WarmStore()
        from src.tooloo.core.mega_dag import KnowledgeBank
        mem._cold = KnowledgeBank(storage_path=cold_path)

        # T3 hit
        check("T3 cold read", mem.read("cold_key") == "from_cold")

        # T2 shadows T3
        mem.warm_write("cold_key", "from_warm", ttl_seconds=30)
        check("T2 warm shadows T3", mem.read("cold_key") == "from_warm")

        # T1 shadows T2
        mem.hot_write("cold_key", "from_hot")
        check("T1 hot shadows T2 and T3", mem.read("cold_key") == "from_hot")

        # Miss
        check("complete miss returns None", mem.read("nonexistent") is None)

        # Diagnostics dict is well-formed
        diag = mem.diagnostics()
        check("diagnostics has expected keys", all(k in diag for k in [
            "namespace", "tier1_hot_keys", "tier2_warm_keys", "tier3_cold_keys", "cold_lessons_total"
        ]))
        check("diagnostics T1 hot count >= 1", diag["tier1_hot_keys"] >= 1)
    finally:
        os.unlink(cold_path)


# ---------------------------------------------------------------------------
# Integration: TooLoo DAG memory attached on ignite()
# ---------------------------------------------------------------------------
class _NoOpOperator(AbstractOperator):
    """Silent no-op planner that terminates after one step."""
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        # Write a hot key through TooLoo's memory
        if context.memory:
            context.memory.hot_write("test_run_flag", True)
            context.memory.warm_write("dag_goal_snippet", context.goal[:50], ttl_seconds=120)
        return NodeResult(outcome={"status": "noop"})


def test_tooloo_dag_memory():
    print(f"\n{HDR}── TooLoo DAG memory integration ──{RST}")

    async def _run():
        dag = ContinuousMegaDAG(max_iterations=3, max_depth=1)
        dag.register_operator(NodeType.PLANNING, _NoOpOperator())
        result = await dag.ignite("Test memory wiring", initial_state={})

        mem = dag.tooloo_memory
        check("tooloo_memory is a MemorySystem", isinstance(mem, MemorySystem))
        check("namespace is 'tooloo'", mem.namespace == "tooloo")
        check("context.memory is same as tooloo_memory", dag.context.memory is mem)

        # T1: key written by _NoOpOperator via context.memory.hot_write should be in hot store
        check("T1 hot key written by operator readable", mem.read("test_run_flag") is True)

        # T2: warm key survives in the session store
        check("T2 warm key written by operator readable", mem.read("dag_goal_snippet") is not None)

        # Diagnostics
        diag = mem.diagnostics()
        check("T1 hot keys >= 1 after run", diag["tier1_hot_keys"] >= 1)
        check("T2 warm keys >= 1 after run", diag["tier2_warm_keys"] >= 1)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Integration: Buddy memory — init, warm model cache, hot Q&A cache
# ---------------------------------------------------------------------------
def test_buddy_memory():
    print(f"\n{HDR}── Buddy memory integration ──{RST}")
    from src.tooloo.core.buddy import BuddyOperator

    buddy = BuddyOperator()

    check("buddy_memory is MemorySystem", isinstance(buddy.buddy_memory, MemorySystem))
    check("buddy namespace is 'buddy'", buddy.buddy_memory.namespace == "buddy")

    # Warm tier: active_model should be set at init
    active_model = buddy.buddy_memory.read("active_model")
    check("T2 warm 'active_model' set at init", active_model is not None)
    check("T2 active_model matches buddy.model", active_model == buddy.model)

    # Simulate hot write (as if answer_question ran)
    buddy.buddy_memory.hot_write("last_question", "What is the system doing?")
    buddy.buddy_memory.hot_write("last_answer", "The system is idle.")
    check("T1 hot 'last_question' readable", buddy.buddy_memory.read("last_question") == "What is the system doing?")
    check("T1 hot 'last_answer' readable", buddy.buddy_memory.read("last_answer") == "The system is idle.")

    # Cold write
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({}, f)
        cold_path = f.name

    try:
        buddy.buddy_memory._cold = KnowledgeBank(storage_path=cold_path)
        buddy.buddy_memory.cold_write("test_lesson", "Always check T2 before T3.")
        loaded = KnowledgeBank(storage_path=cold_path)
        check("T3 cold lesson persisted to file", "buddy:test_lesson" in loaded.lessons)
        check("T3 cold lesson value correct", loaded.lessons["buddy:test_lesson"] == "Always check T2 before T3.")
    finally:
        os.unlink(cold_path)

    # Diagnostics
    diag = buddy.buddy_memory.diagnostics()
    check("buddy diagnostics T1 >= 2", diag["tier1_hot_keys"] >= 2)
    check("buddy diagnostics T2 >= 1", diag["tier2_warm_keys"] >= 1)


# ---------------------------------------------------------------------------
# Integration: #memory shortcut on answer_question (no LLM call, pure logic)
# ---------------------------------------------------------------------------
def test_buddy_memory_shortcut():
    print(f"\n{HDR}── Buddy #memory shortcut ──{RST}")
    from src.tooloo.core.buddy import BuddyOperator

    async def _run():
        buddy = BuddyOperator()
        ctx = GlobalContext(goal="Test shortcut")
        # Attach a fresh MemorySystem to context so Buddy can read DAG diag
        from src.tooloo.core.memory import MemorySystem
        ctx.memory = MemorySystem(namespace="tooloo")

        answer = await buddy.answer_question("#memory", ctx)
        check("#memory shortcut returns string", isinstance(answer, str))
        check("#memory contains 'Buddy Memory'", "Buddy Memory" in answer)
        check("#memory contains 'TooLoo DAG Memory'", "TooLoo DAG Memory" in answer)
        check("#memory contains tier labels", "Hot keys" in answer and "Warm keys" in answer)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"\n{'='*55}")
    print("  SOVEREIGN 3-TIER MEMORY SYSTEM — TEST SUITE")
    print(f"{'='*55}")

    test_warm_store()
    test_memory_system_cascade()
    test_tooloo_dag_memory()
    test_buddy_memory()
    test_buddy_memory_shortcut()

    print(f"\n{'='*55}")
    if _all_passed:
        print(f"  \033[92m ALL TESTS PASSED\033[0m")
    else:
        print(f"  \033[91m SOME TESTS FAILED — see above\033[0m")
    print(f"{'='*55}\n")
    sys.exit(0 if _all_passed else 1)
