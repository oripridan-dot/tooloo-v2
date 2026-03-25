
import asyncio
import json
import logging
from collections import deque
from typing import Any

from engine.pipeline import NStrokeEngine
from engine.router import MandateRouter, LockedIntent
from engine.jit_booster import JITBooster
from engine.tribunal import Tribunal
from engine.graph import TopologicalSorter
from engine.executor import JITExecutor
from engine.scope_evaluator import ScopeEvaluator
from engine.refinement import RefinementLoop
from engine.mcp_manager import MCPManager
from engine.model_selector import ModelSelector
from engine.refinement_supervisor import RefinementSupervisor

# Configure logging to see the engine's internal broadcasts
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ClaudioMandate")

async def execute_mandate():
    logger.info("INITIATING 16D PRODUCTION MANDATE: Claudio Real-Time Sync Architecture")
    
    # 1. Setup the Engine
    # We use real components to properly stress-test the async/sync bridges
    engine = NStrokeEngine(
        router=MandateRouter(),
        booster=JITBooster(),
        tribunal=Tribunal(),
        sorter=TopologicalSorter(),
        executor=JITExecutor(),
        scope_evaluator=ScopeEvaluator(),
        refinement_loop=RefinementLoop(),
        mcp_manager=MCPManager(),
        model_selector=ModelSelector(),
        refinement_supervisor=RefinementSupervisor(),
        broadcast_fn=lambda msg: logger.info(f"[BROADCAST] {msg.get('type')}: {msg.get('msg', '') or msg.get('score', '') or ''}")
    )

    # 2. Define the Mandate
    mandate_text = (
        "Architect a WebSocket/WebRTC synchronization protocol for high-fidelity audio collaboration "
        "on the Claudio platform. Ensure zero-tolerance latency (<20ms glass-to-glass) and robust "
        "security via OWASP-aligned auditing. Use the 6W Cognitive Coordinate system for all metadata."
    )
    
    locked_intent = LockedIntent(
        intent="BUILD",
        confidence=0.98,
        value_statement="Achieve ultra-low latency audio sync for professional collaboration.",
        constraint_summary="Latency < 20ms, WebRTC/WebSocket hybrid, OWASP security compliance.",
        mandate_text=mandate_text,
        context_turns=deque([{"role": "user", "content": mandate_text}])
    )

    # 3. Run the Engine
    logger.info("Executing N-Stroke loop...")
    result = await engine.run(locked_intent)

    # 4. Final Report
    logger.info("MANDATE EXECUTION COMPLETE")
    logger.info(f"Pipeline ID: {result.pipeline_id}")
    logger.info(f"Final Verdict: {result.final_verdict}")
    logger.info(f"Satisfied: {result.satisfied}")
    logger.info(f"Total Strokes: {result.total_strokes}")
    logger.info(f"Latency: {result.latency_ms:.2f}ms")
    
    # Verify 6W Metadata in the result (if stored in strokes or final summary)
    # The engine logs this via antigravity_execution
    
    if result.satisfied:
        print("\n[SUCCESS] Claudio Real-Time Sync Architecture Validated.")
    else:
        print("\n[FAILURE] Mandate did not reach satisfaction threshold.")

if __name__ == "__main__":
    asyncio.run(execute_mandate())
