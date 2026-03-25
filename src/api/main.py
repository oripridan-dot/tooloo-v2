"""
src/api/main.py — TooLoo V2 API Gateway.

The entry point for external applications to interact with the TooLoo V2 engine.
Features:
- Session-mapped Cognitive Memory (CognitiveGraph persistence).
- Compliance-audited execution via the Tribunal.
- Multi-stroke autonomous reasoning.
- SSE Streaming (Phase 4 ongoing).
"""
from __future__ import annotations

import logging
import uuid
import time
import asyncio
from typing import Any, AsyncGenerator
from collections import deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from engine.pipeline import NStrokeEngine
from engine.tribunal import Tribunal, Engram
from engine.router import LockedIntent, MandateRouter
from engine.memory import memory_manager
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.jit_booster import JITBooster
from engine.executor import JITExecutor
from engine.scope_evaluator import ScopeEvaluator
from engine.refinement import RefinementLoop
from engine.mcp_manager import MCPManager
from engine.model_selector import ModelSelector
from engine.refinement_supervisor import RefinementSupervisor
from engine.psyche_bank import PsycheBank

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TooLooGateway")

# ── Pydantic Models ───────────────────────────────────────────────────────────

class EngramRequest(BaseModel):
    """External request to the TooLoo engine."""
    prompt: str = Field(..., description="The user's prompt or mandate.")
    session_id: str = Field(default_factory=lambda: f"session-{uuid.uuid4().hex[:8]}")
    intent: str = Field("IDEATE", description="The high-level intent (IDEATE, BUILD, DEBUG, etc.)")
    domain: str = "backend"

class EngramResponse(BaseModel):
    """Final response from the engine."""
    response: str
    session_id: str
    violations: list[str] = []
    latency_ms: float

# ── Engine Initialization ─────────────────────────────────────────────────────

def create_engine() -> NStrokeEngine:
    """Canonical NStrokeEngine factory with dependency injection."""
    bank = PsycheBank()
    tribunal = Tribunal(bank=bank)
    mcp = MCPManager()
    return NStrokeEngine(
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
        max_strokes=3
    )

# Shared engine instance
engine = create_engine()

app = FastAPI(
    title="TooLoo V2 API Gateway",
    description="The secure, cognitive interface for the TooLoo Autonomous Engine.",
    version="2.0.0",
)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/v2/execute", response_model=EngramResponse)
async def execute_engram(request: EngramRequest) -> EngramResponse:
    """Execute a single engram turn with full multi-stroke reasoning."""
    t0 = time.monotonic()
    
    # 1. Load Session Memory (CognitiveGraph)
    graph = memory_manager.load_graph(request.session_id) or CognitiveGraph()
    logger.info(f"Loaded graph for session {request.session_id} (Nodes: {len(graph.nodes())})")
    
    # 2. Prepare LockedIntent
    locked_intent = LockedIntent(
        intent=request.intent,
        confidence=1.0,  # External requests are explicitly mandated
        value_statement="External API Mandate",
        constraint_summary="None",
        mandate_text=request.prompt,
        context_turns=deque([])
    )
    
    # 3. Run Pipeline
    try:
        pipeline_id = f"api-{uuid.uuid4().hex[:6]}"
        result = await engine.run(
            locked_intent=locked_intent,
            pipeline_id=pipeline_id
        )
        
        # 4. Save Session Memory
        memory_manager.save_graph(request.session_id, graph)
        
        # 5. Extract Final Outcome
        # Note: In a real implementation, we'd extract the actual text from the result.
        # For now, we simulate the aggregation.
        response_text = f"Processed mandate: {result.final_verdict}"
        
        # 6. Check for violations via Tribunal (Post-execution audit)
        audit_engram = Engram(
            slug=f"{pipeline_id}-audit",
            intent=request.intent,
            logic_body=response_text,
            domain=request.domain
        )
        audit_result = await engine._tribunal.evaluate(audit_engram)
        
        return EngramResponse(
            response=response_text,
            session_id=request.session_id,
            violations=audit_result.violations,
            latency_ms=(time.monotonic() - t0) * 1000.0
        )
        
    except Exception as e:
        logger.exception("Pipeline execution failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health-check endpoint."""
    return {"status": "healthy", "engine": "TooLoo V2"}

# ── Phase 4: Streaming (SSE) ──────────────────────────────────────────────────

@app.post("/v2/stream")
async def stream_engram(request: EngramRequest):
    """Stream response tokens using Server-Sent Events (SSE)."""
    
    async def event_generator() -> AsyncGenerator[str, None]:
        # Simulated streaming for Phase 4 proof-of-concept
        yield f"data: [START_SESSION] {request.session_id}\n\n"
        
        # In Phase 5, this will be connected to the true LLM stream
        words = f"Received mandate: {request.prompt}. Initializing N-Stroke cycle...".split()
        for word in words:
            yield f"data: {word} \n\n"
            await asyncio.sleep(0.1)
            
        yield "data: [END_SESSION]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
