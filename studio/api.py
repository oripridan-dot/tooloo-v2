"""
studio/api.py — TooLoo V2 Governor Dashboard API.

Routes:
  GET  /                          serve index.html
  GET  /v2/health                 liveness + component status
  GET  /v2/status                 rich system dashboard status
  POST /v2/mandate                route + plan + execute a mandate text
  GET  /v2/dag                    current DAG node/edge snapshot
  GET  /v2/psyche-bank            all .cog.json rules
  GET  /v2/router-status          circuit-breaker state
  POST /v2/router-reset           reset circuit-breaker
  GET  /v2/events                 SSE event stream
  POST /v2/auto-loop/start        start autonomous improvement loop
  POST /v2/auto-loop/stop         stop autonomous improvement loop
  GET  /v2/auto-loop/status       auto-loop state + cycle stats
  POST /v2/roadmap/{id}/promote   promote a proven roadmap item
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.config import settings
from engine.conversation import ConversationEngine
from engine.engram_visual import VisualEngramGenerator
from engine.executor import Envelope, JITExecutor
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.jit_booster import JITBooster
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.roadmap import RoadmapManager
from engine.router import ConversationalIntentDiscovery, LockedIntent, MandateRouter
from engine.sandbox import SandboxOrchestrator
from engine.scope_evaluator import ScopeEvaluator
from engine.self_improvement import SelfImprovementEngine
from engine.supervisor import TwoStrokeEngine
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
_engram_generator = VisualEngramGenerator()
_self_improvement_engine = SelfImprovementEngine(
    booster=_jit_booster, bank=_bank)
_intent_discovery = ConversationalIntentDiscovery()

_STATIC = Path(__file__).parent / "static"
_STARTUP_TIME: str = datetime.now(UTC).isoformat()

# ── SSE broadcast queue ───────────────────────────────────────────────────────
_sse_queues: list[asyncio.Queue[str]] = []


def _broadcast(event: dict[str, Any]) -> None:
    data = json.dumps(event)
    for q in list(_sse_queues):
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass


# ── Sandbox + Roadmap singletons (after _broadcast so they can be wired) ─────
_supervisor = TwoStrokeEngine(
    router=_router,
    booster=_jit_booster,
    tribunal=_tribunal,
    sorter=_sorter,
    executor=_executor,
    scope_evaluator=_scope_evaluator,
    refinement_loop=_refinement_loop,
    broadcast_fn=_broadcast,
)
_roadmap = RoadmapManager()
_sandbox_orchestrator = SandboxOrchestrator(
    max_workers=settings.sandbox_max_workers,
    broadcast_fn=_broadcast,
    booster=_jit_booster,
    bank=_bank,
)

# ── Autonomous improvement loop state ─────────────────────────────────────────
_loop_active: bool = False
_loop_task: asyncio.Task[None] | None = None
_loop_stats: dict[str, Any] = {
    "active": False,
    "cycles_completed": 0,
    "last_run_at": None,
    "next_run_at": None,
    "interval_seconds": 90,
    "proven_this_session": 0,
    "improvements_this_session": 0,
    "started_at": None,
}


async def _autonomous_loop() -> None:
    """Background coroutine: self-improve + roadmap sandboxes on a fixed interval."""
    global _loop_active, _loop_stats
    while _loop_active:
        interval = _loop_stats["interval_seconds"]
        _loop_stats["next_run_at"] = (
            datetime.now(UTC) + timedelta(seconds=interval)
        ).isoformat()
        await asyncio.sleep(interval)
        if not _loop_active:
            break
        try:
            cycle = _loop_stats["cycles_completed"] + 1
            _broadcast(
                {"type": "auto_loop", "phase": "started", "cycle": cycle})

            # 1. Self-improvement cycle (blocking — run in thread pool)
            loop = asyncio.get_event_loop()
            report = await loop.run_in_executor(None, _self_improvement_engine.run)
            _broadcast({"type": "self_improve", "report": report.to_dict()})

            # 2. Roadmap sandbox run (blocking)
            items = _roadmap.all_items()
            features = [
                {"text": i.description, "title": i.title, "roadmap_item_id": i.id}
                for i in items
            ]
            reports = await loop.run_in_executor(
                None, _sandbox_orchestrator.run_parallel, features
            )
            proven = 0
            for r in reports:
                if r.roadmap_item_id:
                    _roadmap.update_item_scores(
                        item_id=r.roadmap_item_id,
                        impact_score=r.impact_score,
                        difficulty_score=r.difficulty_score,
                        readiness_score=r.readiness_score,
                        timeline_days=r.timeline_days,
                        status=r.state if r.state in (
                            "proven", "failed", "blocked") else "sandbox",
                        sandbox_id=r.sandbox_id,
                        notes=r.recommendations[:2] if r.recommendations else [
                        ],
                    )
                if r.state == "proven":
                    proven += 1
            _broadcast({"type": "roadmap_run", "reports": [
                       r.to_dict() for r in reports]})

            _loop_stats["cycles_completed"] += 1
            _loop_stats["proven_this_session"] += proven
            _loop_stats["improvements_this_session"] += report.components_assessed
            _loop_stats["last_run_at"] = datetime.now(UTC).isoformat()
            _loop_stats["next_run_at"] = (
                datetime.now(UTC) + timedelta(seconds=interval)
            ).isoformat()
            _broadcast({
                "type": "auto_loop", "phase": "completed",
                "cycle": _loop_stats["cycles_completed"],
                "proven_count": proven,
                "stats": dict(_loop_stats),
            })
        except Exception as exc:  # noqa: BLE001
            _broadcast(
                {"type": "auto_loop", "phase": "error", "error": str(exc)})


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
            "engram_engine": "up",
            "self_improvement": "up",
            "supervisor": "up",
            "intent_discovery": "up",
        },
    }


class MandateRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    text: str
    session_id: str = ""


class IntentClarifyRequest(BaseModel):
    text: str
    session_id: str = ""


class PipelineRequest(BaseModel):
    text: str
    session_id: str = ""
    max_iterations: int = 3


class LockedIntentRequest(BaseModel):
    """Directly supply a pre-confirmed intent instead of using the discovery loop."""
    intent: str
    confidence: float
    value_statement: str
    constraint_summary: str = ""
    mandate_text: str
    session_id: str = ""
    max_iterations: int = 3


# ── Intent Discovery endpoint ─────────────────────────────────────────────────

@app.post("/v2/intent/clarify")
async def intent_clarify(req: IntentClarifyRequest) -> dict[str, Any]:
    """Process one conversational turn of intent discovery.

    Returns either a clarifying question (``locked=false``) or a
    ``locked_intent`` ready for ``/v2/pipeline`` (``locked=true``).
    """
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"
    result = _intent_discovery.discover(req.text, session_id)
    _broadcast({
        "type": "intent_clarification" if not result.locked else "intent_locked",
        "session_id": session_id,
        "result": result.to_dict(),
    })
    return {"session_id": session_id, **result.to_dict()}


@app.delete("/v2/intent/session/{session_id}")
async def clear_intent_session(session_id: str) -> dict[str, Any]:
    cleared = _intent_discovery.clear_session(session_id)
    return {"session_id": session_id, "cleared": cleared}


# ── Two-Stroke Pipeline endpoint ──────────────────────────────────────────────

@app.post("/v2/pipeline")
async def run_pipeline(req: PipelineRequest) -> dict[str, Any]:
    """THE singular execution pipeline.

    Runs intent discovery until locked, then fires the Two-Stroke Engine:
      Pre-Flight → Process 1 → Mid-Flight → Process 2 → Satisfaction Gate → loop.
    """
    t0 = time.monotonic()
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"
    pipeline_id = f"pipe-{uuid.uuid4().hex[:8]}"

    # 1. Intent Discovery — run until locked (or return discovery result if not yet locked)
    discovery = _intent_discovery.discover(req.text, session_id)

    _broadcast({
        "type": "intent_clarification" if not discovery.locked else "intent_locked",
        "session_id": session_id,
        "pipeline_id": pipeline_id,
        "result": discovery.to_dict(),
    })

    if not discovery.locked:
        # Not ready to execute — return the clarifying question to the client.
        return {
            "pipeline_id": pipeline_id,
            "session_id": session_id,
            "locked": False,
            "clarification_question": discovery.clarification_question,
            "clarification_type": discovery.clarification_type,
            "intent_hint": discovery.intent_hint,
            "confidence": discovery.confidence,
            "turn_count": discovery.turn_count,
            "result": None,
            "latency_ms": round((time.monotonic() - t0) * 1000, 2),
        }

    # 2. Intent locked — run the Two-Stroke Engine.
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _supervisor.run(
            discovery.locked_intent,
            pipeline_id=pipeline_id,
            max_iterations=req.max_iterations,
        ),
    )

    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "pipeline_id": pipeline_id,
        "session_id": session_id,
        "locked": True,
        "clarification_question": "",
        "clarification_type": "",
        "intent_hint": discovery.intent_hint,
        "confidence": discovery.confidence,
        "turn_count": discovery.turn_count,
        "result": result.to_dict(),
        "latency_ms": latency_ms,
    }


@app.post("/v2/pipeline/direct")
async def run_pipeline_direct(req: LockedIntentRequest) -> dict[str, Any]:
    """Run the Two-Stroke Engine with a pre-confirmed LockedIntent.

    Skips the intent-discovery loop — useful for programmatic callers that
    already hold a locked intent from a previous discovery session.
    """
    t0 = time.monotonic()
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"
    pipeline_id = f"pipe-{uuid.uuid4().hex[:8]}"
    from datetime import UTC, datetime as _dt
    locked = LockedIntent(
        intent=req.intent,
        confidence=req.confidence,
        value_statement=req.value_statement,
        constraint_summary=req.constraint_summary,
        mandate_text=req.mandate_text,
        context_turns=[],
        locked_at=_dt.now(UTC).isoformat(),
    )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _supervisor.run(
            locked,
            pipeline_id=pipeline_id,
            max_iterations=req.max_iterations,
        ),
    )

    return {
        "pipeline_id": pipeline_id,
        "session_id": session_id,
        "result": result.to_dict(),
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
    }


class SandboxSpawnRequest(BaseModel):
    feature_text: str
    feature_title: str = ""
    roadmap_item_id: str | None = None


class RoadmapItemRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    deps: list[str] = []
    evaluation_dimensions: list[str] = []


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

    # 7. Visual Engram — emit cognitive state to frontend SVG layers
    visual_engram = _engram_generator.from_mandate(
        route=route,
        jit_result=jit_result,
        tribunal_result=tribunal_result,
        plan=plan,
        scope=scope,
        refinement=refinement,
    )
    _broadcast({"type": "visual_engram", "engram": visual_engram.to_dict()})

    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "mandate_id": mandate_id,
        "route": route.to_dict(),
        "jit_boost": jit_result.to_dict(),
        "scope": scope.to_dict(),
        "plan": plan,
        "execution": flat,
        "refinement": refinement.to_dict(),
        "visual_engram": visual_engram.to_dict(),
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

    # 5. Visual Engram — emit cognitive state to frontend SVG layers
    visual_engram = _engram_generator.from_chat(
        route=route,
        jit_result=jit_result,
        tribunal_result=tribunal_result,
    )
    _broadcast({"type": "visual_engram", "engram": visual_engram.to_dict()})

    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "mandate_id": mandate_id,
        "session_id": session_id,
        "route": route.to_dict(),
        "jit_boost": jit_result.to_dict(),
        "tribunal_result": tribunal_result.to_dict(),
        "conversation": conv_result.to_dict(),
        "visual_engram": visual_engram.to_dict(),
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


@app.get("/v2/engram/current")
async def engram_current() -> dict[str, Any]:
    """Return the most recently generated Visual Engram (or idle if none)."""
    return {"engram": _engram_generator.current().to_dict()}


class EngramGenerateRequest(BaseModel):
    text: str = ""
    intent: str = "BUILD"
    confidence: float = 0.75
    mode: str = "idle"


@app.post("/v2/engram/generate")
async def engram_generate(req: EngramGenerateRequest) -> dict[str, Any]:
    """Manually trigger an engram from explicit parameters (for UI preview)."""
    from engine.router import RouteResult
    route = RouteResult(
        intent=req.intent,
        confidence=req.confidence,
        circuit_open=req.confidence < 0.85,
        mandate_text=req.text,
    )
    engram = _engram_generator.from_chat(route=route)
    _broadcast({"type": "visual_engram", "engram": engram.to_dict()})
    return {"engram": engram.to_dict()}


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


@app.post("/v2/self-improve")
async def self_improve() -> dict[str, Any]:
    """Run one full self-improvement cycle across all engine micro-components.

    Wave plan: 3 waves (core-security → performance → meta-analysis).
    Each component is routed through Router → JITBooster → Tribunal → Scope
    → Execute → Refinement.
    Returns a ``SelfImprovementReport`` with per-component assessments,
    JIT SOTA signals, and top recommendations.
    """
    t0 = time.monotonic()
    report = _self_improvement_engine.run()
    _broadcast({"type": "self_improve", "report": report.to_dict()})
    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {"self_improvement": report.to_dict(), "latency_ms": latency_ms}


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


# ── Sandbox endpoints ────────────────────────────────────────────────────────

@app.post("/v2/sandbox/spawn")
async def spawn_sandbox(req: SandboxSpawnRequest) -> dict[str, Any]:
    """Spawn one isolated sandbox for a single feature mandate.

    Runs the full pipeline: VectorDedup → Router → JIT → Tribunal →
    Scope → Execute → Refine → 9-Dimension Scoring → ReadinessGate.
    """
    t0 = time.monotonic()
    report = _sandbox_orchestrator.run_sandbox(
        feature_text=req.feature_text,
        feature_title=req.feature_title,
        roadmap_item_id=req.roadmap_item_id,
    )
    return {
        "sandbox_id": report.sandbox_id,
        "state": report.state,
        "report": report.to_dict(),
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
    }


@app.get("/v2/sandbox")
async def list_sandboxes() -> dict[str, Any]:
    """Return all sandbox reports from the orchestrator registry."""
    reports = _sandbox_orchestrator.all_reports()
    return {
        "total": len(reports),
        "proven": sum(1 for r in reports if r.state == "proven"),
        "failed": sum(1 for r in reports if r.state == "failed"),
        "blocked": sum(1 for r in reports if r.state == "blocked"),
        "duplicate": sum(1 for r in reports if r.state == "duplicate"),
        "reports": [r.to_dict() for r in reports],
        "vector_store": _sandbox_orchestrator.vector_store_summary(),
        "graph": _sandbox_orchestrator.graph_summary(),
    }


@app.get("/v2/sandbox/{sandbox_id}")
async def get_sandbox(sandbox_id: str) -> dict[str, Any]:
    """Get one sandbox report by ID."""
    report = _sandbox_orchestrator.get_report(sandbox_id)
    if report is None:
        return {"error": "sandbox not found", "sandbox_id": sandbox_id}
    return report.to_dict()


# ── Roadmap endpoints ─────────────────────────────────────────────────────────

@app.get("/v2/roadmap")
async def get_roadmap() -> dict[str, Any]:
    """Return full roadmap report: items, wave plan, status/priority distribution."""
    return _roadmap.get_report().to_dict()


@app.post("/v2/roadmap/item")
async def add_roadmap_item(req: RoadmapItemRequest) -> dict[str, Any]:
    """Add a new item to the roadmap (near-duplicates are rejected automatically)."""
    item = _roadmap.add_item(
        title=req.title,
        description=req.description,
        priority=req.priority,
        deps=req.deps,
        evaluation_dimensions=req.evaluation_dimensions or [],
    )
    if item is None:
        return {"accepted": False, "reason": "near-duplicate detected — item rejected"}
    return {"accepted": True, "item": item.to_dict()}


@app.post("/v2/roadmap/run")
async def run_roadmap_sandboxes() -> dict[str, Any]:
    """Run ALL roadmap items as parallel sandboxes (up to max=25 concurrent).

    Each item's description becomes the sandbox feature mandate.
    Proven results update the roadmap item scores and status automatically.
    All progress is broadcast via SSE 'sandbox' events in real-time.
    """
    t0 = time.monotonic()
    items = _roadmap.all_items()
    features = [
        {
            "text": item.description,
            "title": item.title,
            "roadmap_item_id": item.id,
        }
        for item in items
    ]
    reports = _sandbox_orchestrator.run_parallel(features)
    # Write sandbox scores back to roadmap
    for r in reports:
        if r.roadmap_item_id:
            _roadmap.update_item_scores(
                item_id=r.roadmap_item_id,
                impact_score=r.impact_score,
                difficulty_score=r.difficulty_score,
                readiness_score=r.readiness_score,
                timeline_days=r.timeline_days,
                status=r.state if r.state in (
                    "proven", "failed", "blocked") else "sandbox",
                sandbox_id=r.sandbox_id,
                notes=r.recommendations[:2] if r.recommendations else [],
            )
    _broadcast({"type": "roadmap_run", "reports": [
               r.to_dict() for r in reports]})
    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "total": len(reports),
        "proven": sum(1 for r in reports if r.state == "proven"),
        "failed": sum(1 for r in reports if r.state == "failed"),
        "blocked": sum(1 for r in reports if r.state == "blocked"),
        "reports": [r.to_dict() for r in reports],
        "latency_ms": latency_ms,
    }


@app.get("/v2/roadmap/similar")
async def roadmap_similar(q: str = "", top_k: int = 3) -> dict[str, Any]:
    """Find roadmap items semantically similar to a query string."""
    if not q:
        return {"results": []}
    return {"query": q, "results": _roadmap.find_similar(q, top_k=top_k)}


# ── Auto-improvement loop endpoints ──────────────────────────────────────────

@app.post("/v2/auto-loop/start")
async def start_auto_loop(interval_seconds: int = 90) -> dict[str, Any]:
    """Start the autonomous improvement loop (self-improve + roadmap run every N seconds)."""
    global _loop_active, _loop_task, _loop_stats
    if _loop_active:
        return {"started": False, "reason": "already running", "stats": dict(_loop_stats)}
    _loop_active = True
    _loop_stats["active"] = True
    _loop_stats["interval_seconds"] = max(30, interval_seconds)
    _loop_stats["started_at"] = datetime.now(UTC).isoformat()
    _loop_stats["next_run_at"] = (
        datetime.now(UTC) + timedelta(seconds=_loop_stats["interval_seconds"])
    ).isoformat()
    _loop_task = asyncio.create_task(_autonomous_loop())
    _broadcast({"type": "auto_loop", "phase": "loop_started",
               "stats": dict(_loop_stats)})
    return {"started": True, "stats": dict(_loop_stats)}


@app.post("/v2/auto-loop/stop")
async def stop_auto_loop() -> dict[str, Any]:
    """Stop the autonomous improvement loop."""
    global _loop_active, _loop_stats
    _loop_active = False
    _loop_stats["active"] = False
    _broadcast({"type": "auto_loop", "phase": "loop_stopped",
               "stats": dict(_loop_stats)})
    return {"stopped": True, "stats": dict(_loop_stats)}


@app.get("/v2/auto-loop/status")
async def auto_loop_status_endpoint() -> dict[str, Any]:
    return dict(_loop_stats)


# ── Rich system status (dashboard) ───────────────────────────────────────────

@app.get("/v2/status")
async def system_status() -> dict[str, Any]:
    """Full system status snapshot for the dashboard view."""
    sandboxes = _sandbox_orchestrator.all_reports()
    roadmap_report = _roadmap.get_report()
    router_st = _router.status()
    items = _roadmap.all_items()
    proven_sb = sum(1 for r in sandboxes if r.state == "proven")
    failed_sb = sum(1 for r in sandboxes if r.state == "failed")
    total_sb = len(sandboxes)
    avg_readiness = (
        sum(r.readiness_score for r in sandboxes) /
        total_sb if total_sb else 0.0
    )
    top_features = sorted(
        sandboxes, key=lambda r: r.readiness_score, reverse=True
    )[:5]
    return {
        "version": "2.0.0",
        "startup_time": _STARTUP_TIME,
        "system_health": round(avg_readiness, 3),
        "circuit_breaker": router_st,
        "psyche_bank_rules": len(_bank.all_rules()),
        "dag_nodes": len(_graph.nodes()),
        "sandboxes": {
            "total": total_sb,
            "proven": proven_sb,
            "failed": failed_sb,
            "avg_readiness": round(avg_readiness, 3),
        },
        "roadmap": {
            "total_items": roadmap_report.total_items,
            "by_status": roadmap_report.by_status,
            "by_priority": roadmap_report.by_priority,
            "wave_count": roadmap_report.wave_count,
        },
        "auto_loop": dict(_loop_stats),
        "top_features": [r.to_dict() for r in top_features],
        "items": [i.to_dict() for i in items],
    }


# ── Roadmap promote endpoint ──────────────────────────────────────────────────

@app.post("/v2/roadmap/{item_id}/promote")
async def promote_roadmap_item(item_id: str) -> dict[str, Any]:
    """Promote a proven roadmap item — marks it as promoted and broadcasts."""
    item = _roadmap.get_item(item_id)
    if not item:
        return {"promoted": False, "reason": "item not found"}
    updated = _roadmap.update_item_scores(
        item_id=item_id,
        impact_score=item.impact_score,
        difficulty_score=item.difficulty_score,
        readiness_score=item.readiness_score,
        timeline_days=item.timeline_days,
        status="promoted",
    )
    if not updated:
        return {"promoted": False, "reason": "update failed"}
    _broadcast({"type": "roadmap_promote",
               "item_id": item_id, "title": item.title})
    return {"promoted": True, "item_id": item_id, "title": item.title}
