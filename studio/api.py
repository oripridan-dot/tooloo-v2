"""
studio/api.py — TooLoo V2 Governor Dashboard API.

Routes:
  GET  /                    serve index.html
  GET  /v2/health           liveness + component status
  POST /v2/mandate          route + plan + execute a mandate text
  GET  /v2/dag              current DAG node/edge snapshot
  GET  /v2/psyche-bank      all .cog.json rules
  GET  /v2/router-status    circuit-breaker state
  POST /v2/router-reset     reset circuit-breaker
  GET  /v2/events           SSE event stream
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.config import settings
from engine.conversation import ConversationEngine
from engine.executor import Envelope, JITExecutor
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.jit_booster import JITBooster
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.router import MandateRouter
from engine.scope_evaluator import ScopeEvaluator
from engine.tribunal import Engram, Tribunal

# ── Singletons ────────────────────────────────────────────────────────────────
_router = MandateRouter()
_graph = CognitiveGraph()
_bank = PsycheBank()
_tribunal = Tribunal(bank=_bank)
_executor = JITExecutor()
_sorter = TopologicalSorter()
_scope_evaluator = ScopeEvaluator()
_refinement_loop = RefinementLoop()
_conversation_engine = ConversationEngine()
_jit_booster = JITBooster()

_STATIC = Path(__file__).parent / "static"

# ── SSE broadcast queue ───────────────────────────────────────────────────────
_sse_queues: list[asyncio.Queue[str]] = []


def _broadcast(event: dict[str, Any]) -> None:
    data = json.dumps(event)
    for q in list(_sse_queues):
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass


# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="TooLoo V2 Governor Dashboard", version="2.0.0")


# ── Routes ───────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(str(_STATIC / "favicon.ico"))


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index() -> HTMLResponse:
    html = (_STATIC / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/v2/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "2.0.0",
        "components": {
            "router": "up",
            "graph": f"{len(_graph.nodes())} nodes",
            "psyche_bank": f"{len(_bank.all_rules())} rules",
            "tribunal": "up",
            "executor": "up",
            "jit_booster": "up",
        },
    }


class MandateRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    text: str
    session_id: str = ""


@app.post("/v2/mandate")
async def route_mandate(req: MandateRequest) -> dict[str, Any]:
    t0 = time.monotonic()
    mandate_id = f"m-{uuid.uuid4().hex[:8]}"

    # 1. Route
    route = _router.route(req.text)
    _broadcast({"type": "route", "mandate_id": mandate_id,
               "route": route.to_dict()})

    # Open-circuit → return early only when the breaker is globally tripped
    if route.intent == "BLOCKED":
        return {
            "mandate_id": mandate_id,
            "route": route.to_dict(),
            "jit_boost": None,
            "plan": [],
            "execution": [],
            "latency_ms": round((time.monotonic() - t0) * 1000, 2),
        }

    # 2. JIT SOTA boost (mandatory — runs before tribunal and plan)
    jit_result = _jit_booster.fetch(route)
    _router.apply_jit_boost(route, jit_result.boosted_confidence)
    _broadcast({"type": "jit_boost", "mandate_id": mandate_id,
               "jit_boost": jit_result.to_dict()})

    # 3. Build a minimal engram for tribunal check
    engram = Engram(
        slug=mandate_id,
        intent=route.intent,
        logic_body=req.text,
        domain="backend",
        mandate_level="L2",
    )
    tribunal_result = _tribunal.evaluate(engram)
    _broadcast({"type": "tribunal", "mandate_id": mandate_id,
               "result": tribunal_result.to_dict()})

    # 4. Build a toy DAG plan from route
    spec: list[tuple[str, list[str]]] = [
        (f"{mandate_id}-recon", []),
        (f"{mandate_id}-plan", [f"{mandate_id}-recon"]),
        (f"{mandate_id}-generate", [f"{mandate_id}-plan"]),
        (f"{mandate_id}-validate", [f"{mandate_id}-generate"]),
    ]
    plan = _sorter.sort(spec)
    _broadcast({"type": "plan", "mandate_id": mandate_id, "waves": plan})

    # 4. Action scope evaluation — understand full plan before allocating resources
    scope = _scope_evaluator.evaluate(plan, intent=route.intent)
    _broadcast({"type": "scope", "mandate_id": mandate_id,
               "scope": scope.to_dict()})

    # 5. Fan-out execution (workers sized by scope recommendation)
    envelopes = [
        Envelope(
            mandate_id=f"{mandate_id}-{i}",
            intent=route.intent,
            domain="backend",
            metadata={"wave": i, "nodes": wave},
        )
        for i, wave in enumerate(plan)
    ]

    def _work(env: Envelope) -> str:
        return f"wave-{env.metadata['wave']}-done"

    exec_results = _executor.fan_out(
        _work, envelopes, max_workers=scope.recommended_workers
    )
    flat = [r.to_dict() for r in exec_results]
    _broadcast({"type": "execution", "mandate_id": mandate_id, "results": flat})

    # 6. Refinement loop — evaluate results, surface recommendations
    refinement = _refinement_loop.evaluate(exec_results)
    _broadcast({"type": "refinement", "mandate_id": mandate_id,
                "report": refinement.to_dict()})

    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "mandate_id": mandate_id,
        "route": route.to_dict(),
        "jit_boost": jit_result.to_dict(),
        "scope": scope.to_dict(),
        "plan": plan,
        "execution": flat,
        "refinement": refinement.to_dict(),
        "latency_ms": latency_ms,
    }


@app.post("/v2/chat")
async def buddy_chat(req: ChatRequest) -> dict[str, Any]:
    t0 = time.monotonic()
    mandate_id = f"c-{uuid.uuid4().hex[:8]}"
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"

    # 1. Route (conversational path — does not touch circuit-breaker counters)
    route = _router.route_chat(req.text)

    # 2. JIT SOTA boost (mandatory — validates and enriches before generation)
    jit_result = _jit_booster.fetch(route)
    _router.apply_jit_boost(route, jit_result.boosted_confidence)

    # 3. Tribunal scan
    engram = Engram(
        slug=mandate_id,
        intent=route.intent,
        logic_body=req.text,
        domain="conversation",
        mandate_level="L1",
    )
    tribunal_result = _tribunal.evaluate(engram)

    # 4. Conversational planning + generation (receives JIT-validated route)
    conv_result = _conversation_engine.process(
        req.text, route, session_id, jit_result=jit_result)

    # 4. SSE broadcast
    _broadcast({
        "type": "conversation",
        "mandate_id": mandate_id,
        "session_id": session_id,
        "route": route.to_dict(),
        "jit_boost": jit_result.to_dict(),
        "tribunal_result": tribunal_result.to_dict(),
        "conversation": conv_result.to_dict(),
    })

    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "mandate_id": mandate_id,
        "session_id": session_id,
        "route": route.to_dict(),
        "jit_boost": jit_result.to_dict(),
        "tribunal_result": tribunal_result.to_dict(),
        "conversation": conv_result.to_dict(),
        "latency_ms": latency_ms,
    }


@app.get("/v2/session/{session_id}")
async def session_history(session_id: str) -> dict[str, Any]:
    history = _conversation_engine.session_history(session_id)
    session = _conversation_engine.get_session(session_id)
    return {
        "session_id": session_id,
        "turn_count": len(history),
        "turns": history,
        "summary": session.to_dict() if session else None,
    }


@app.delete("/v2/session/{session_id}")
async def clear_session(session_id: str) -> dict[str, Any]:
    cleared = _conversation_engine.clear_session(session_id)
    return {"session_id": session_id, "cleared": cleared}


@app.get("/v2/dag")
async def dag_snapshot() -> dict[str, Any]:
    nodes = _graph.nodes()
    edges = [{"from": u, "to": v} for u, v in _graph.edges()]
    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}


@app.get("/v2/psyche-bank")
async def psyche_bank_rules() -> dict[str, Any]:
    return _bank.to_dict()


@app.get("/v2/router-status")
async def router_status() -> dict[str, Any]:
    return _router.status()


@app.post("/v2/router-reset")
async def router_reset() -> dict[str, Any]:
    _router.reset()
    return {"reset": True, "status": _router.status()}


@app.get("/v2/events")
async def sse_stream() -> StreamingResponse:
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _sse_queues.append(q)

    async def _generate() -> AsyncGenerator[str, None]:
        try:
            # Heartbeat on connect
            yield f"data: {json.dumps({'type': 'connected', 'version': '2.0.0'})}\n\n"
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {data}\n\n"
                except TimeoutError:
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
        finally:
            _sse_queues.remove(q)

    return StreamingResponse(_generate(), media_type="text/event-stream")


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    uvicorn.run(
        "studio.api:app",
        host=settings.studio_host,
        port=settings.studio_port,
        reload=settings.studio_reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
