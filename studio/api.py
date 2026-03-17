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
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.config import settings
from engine.executor import Envelope, JITExecutor
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.psyche_bank import PsycheBank
from engine.router import MandateRouter
from engine.tribunal import Engram, Tribunal

# ── Singletons ────────────────────────────────────────────────────────────────
_router = MandateRouter()
_graph = CognitiveGraph()
_bank = PsycheBank()
_tribunal = Tribunal(bank=_bank)
_executor = JITExecutor()
_sorter = TopologicalSorter()

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
        },
    }


class MandateRequest(BaseModel):
    text: str


@app.post("/v2/mandate")
async def route_mandate(req: MandateRequest) -> dict[str, Any]:
    t0 = time.monotonic()
    mandate_id = f"m-{uuid.uuid4().hex[:8]}"

    # 1. Route
    route = _router.route(req.text)
    _broadcast({"type": "route", "mandate_id": mandate_id, "route": route.to_dict()})

    # Open-circuit → return early
    if route.circuit_open:
        return {
            "mandate_id": mandate_id,
            "route": route.to_dict(),
            "plan": [],
            "execution": [],
            "latency_ms": round((time.monotonic() - t0) * 1000, 2),
        }

    # 2. Build a minimal engram for tribunal check
    engram = Engram(
        slug=mandate_id,
        intent=route.intent,
        logic_body=req.text,
        domain="backend",
        mandate_level="L2",
    )
    tribunal_result = _tribunal.evaluate(engram)
    _broadcast({"type": "tribunal", "mandate_id": mandate_id, "result": tribunal_result.to_dict()})

    # 3. Build a toy DAG plan from route
    spec: list[tuple[str, list[str]]] = [
        (f"{mandate_id}-recon", []),
        (f"{mandate_id}-plan", [f"{mandate_id}-recon"]),
        (f"{mandate_id}-generate", [f"{mandate_id}-plan"]),
        (f"{mandate_id}-validate", [f"{mandate_id}-generate"]),
    ]
    plan = _sorter.sort(spec)
    _broadcast({"type": "plan", "mandate_id": mandate_id, "waves": plan})

    # 4. Fan-out execution
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

    exec_results = _executor.fan_out(_work, envelopes)
    flat = [r.to_dict() for r in exec_results]
    _broadcast({"type": "execution", "mandate_id": mandate_id, "results": flat})

    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "mandate_id": mandate_id,
        "route": route.to_dict(),
        "plan": plan,
        "execution": flat,
        "latency_ms": latency_ms,
    }


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
