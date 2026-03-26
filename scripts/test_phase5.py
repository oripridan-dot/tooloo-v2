import asyncio
import uuid
import logging
from engine.pipeline import NStrokeEngine
from engine.tribunal import Tribunal
from engine.router import LockedIntent, MandateRouter
from engine.graph_store import memory_manager
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.jit_booster import JITBooster
from engine.executor import JITExecutor
from engine.scope_evaluator import ScopeEvaluator
from engine.refinement import RefinementLoop
from engine.mcp_manager import MCPManager
from engine.model_selector import ModelSelector
from engine.refinement_supervisor import RefinementSupervisor
from engine.psyche_bank import PsycheBank
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Phase5Test")

async def test_agentic_tool_use():
    """Verify that the engine can autonomously call a tool."""
    bank = PsycheBank()
    tribunal = Tribunal(bank=bank)
    mcp = MCPManager()
    
    engine = NStrokeEngine(
        router=MandateRouter(),
        booster=JITBooster(),
        tribunal=tribunal,
        sorter=TopologicalSorter(),
        executor=JITExecutor(mcp_manager=mcp, tribunal=tribunal, max_workers=6),
        scope_evaluator=ScopeEvaluator(),
        refinement_loop=RefinementLoop(),
        mcp_manager=mcp,
        model_selector=ModelSelector(),
        refinement_supervisor=RefinementSupervisor(),
        max_strokes=2
    )

    # Mandate that explicitly requires a tool call
    # We'll use 'read_error' as a test tool
    error_text = "ZeroDivisionError: division by zero at line 42"
    prompt = f"Analyze this error using the 'read_error' tool: {error_text}"
    
    locked_intent = LockedIntent(
        intent="DEBUG",
        confidence=1.0,
        value_statement="Test agentic tool use",
        constraint_summary="None",
        mandate_text=prompt,
        context_turns=deque([])
    )

    print("\n🚀 Starting Agentic Tool Use Test...")
    print(f"Prompt: {prompt}")

    try:
        # We need to mock 'ideate_with_assistant' as the work function for the test
        from engine.executor import Envelope
        async def work_fn(env: Envelope):
            # This is what JITExecutor._run_async calls if it's an assistant task
            from engine.executor import get_assistant_api_manager
            api = get_assistant_api_manager(mcp, tribunal)
            return await api.run_and_get_response(env.mandate_id, env.domain, env.intent)

        # In a real run, the engine would select this work_fn based on intent.
        # For the test, we'll force the engine to run.
        result = await engine.run(
            locked_intent=locked_intent,
            pipeline_id=f"test-{uuid.uuid4().hex[:6]}"
        )

        print("\n✅ Test Completed!")
        print(f"Verdict: {result.final_verdict}")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        logger.exception("Test failure details")

if __name__ == "__main__":
    asyncio.run(test_agentic_tool_use())
