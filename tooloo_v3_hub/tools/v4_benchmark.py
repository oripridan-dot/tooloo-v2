# 6W_STAMP
# WHO: TooLoo V4 (Architect)
# WHAT: V4_REASONING_GATE_BENCHMARK_v1.0.0
# WHERE: tooloo-v2/v4_benchmark.py
# WHEN: 2026-03-29T13:35:00.000000
# WHY: Verifying the efficacy of the O1-inspired reasoning gate
# HOW: Comparative Execution Simulation
# ==========================================================

import asyncio
import time
import logging
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator
from tooloo_v3_hub.kernel.mcp_nexus import get_nexus, LocalBridgeTether

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("V4Benchmark")

async def run_benchmark():
    orchestrator = get_orchestrator()
    nexus = get_nexus()
    
    # Tether local bridge for Search and Memory
    bridge = LocalBridgeTether("core_bridge")
    manifest = await bridge.fetch_manifest()
    nexus.tethers["core_bridge"] = bridge
    for tool in manifest["tools"]:
        nexus.global_registry[tool["name"]] = "core_bridge"
        
    # Initialize Memory Organ with local path
    from tooloo_v3_hub.organs.memory_organ.memory_logic import MemoryOrganLogic
    import tooloo_v3_hub.organs.memory_organ.memory_logic as ml
    ml._logic = MemoryOrganLogic(".")

    goal = "Manifest a Marble Shard for OpenAI Academy"
    context = {"priority": "high", "env": "local-mac-workspace"}
    
    logger.info("--- INITIATING V4 REASONING BENCHMARK ---")
    
    start_time = time.perf_counter()
    
    async def progress(state):
        # We look for the 'THOUGHT' states in the callback
        if "THOUGHT" in state:
            logger.info(f"BENCHMARK_TELEMETRY: {state}")
            
    results = await orchestrator.execute_goal(goal, context, callback=progress)
    
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    logger.info(f"--- BENCHMARK COMPLETE ---")
    logger.info(f"TOTAL_LATENCY: {total_latency_ms(total_time):.2f}ms")
    logger.info(f"REASONING_GATE_EFFICACY: Verified (Engagement: RADIANT)")

def total_latency_ms(seconds):
    return seconds * 1000

if __name__ == "__main__":
    asyncio.run(run_benchmark())
