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
  GET  /v2/vlt/demo               demo Vector Layout Tree + audit
  POST /v2/vlt/audit              run math proofs on a submitted VLT
  POST /v2/vlt/render             render a VLT tree (SSE broadcast)
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ── De-prioritized imports for Lean Mode ──────────────────────────────────
# All 'engine' package imports are moved into _get_heavy_singletons()
# to ensure module-level memory remains below 256 MiB.
_settings: Any = None

def _get_settings():
    global _settings
    if _settings is None:
        from engine.config import settings
        _settings = settings
    return _settings

# ── Singletons ────────────────────────────────────────────────────────────────
# ── Singletons — lazy-initialized ──────────────────────────────────────────
_router: Any = None
_graph: Any = None
_bank: Any = None
_tribunal: Any = None
_mcp_manager: Any = None
_executor: Any = None
_sorter: Any = None
_scope_evaluator: Any = None
_refinement_loop: Any = None
_buddy_memory: Any = None
_conversation_engine: Any = None
_jit_booster: Any = None
_engram_generator: Any = None
_model_selector: Any = None
_refinement_supervisor: Any = None
_intent_discovery: Any = None
_async_fluid_executor: Any = None
_jit_designer: Any = None

# ── SSE broadcast queue ───────────────────────────────────────────────────────
_sse_queues: list[asyncio.Queue[str]] = []


def _broadcast(event: dict[str, Any]) -> None:
    data = json.dumps(event)
    for q in list(_sse_queues):
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass


_director: Any = None
_b_unit: Any = None
_STATIC = Path(__file__).parent / "static"
_STARTUP_TIME: str = datetime.now(UTC).isoformat()
 
_daemon: Any = None
_notification_bus: Any = None


def _on_tribunal_critical(event: Any) -> None:
    """Internal subscriber: log CRITICAL Tribunal events to structured output."""
    import logging as _logging
    _logging.getLogger("studio.api.bus").critical(
        "[CRITICAL-BUS] %s | source=%s | payload=%s",
        event.message, event.source, event.payload,
    )

_stance_engine: Any = None
CognitiveLens: Any = None
Engram: Any = None
Envelope: Any = None

import threading
_init_lock = threading.Lock()

# ── Heavyweight singletons — lazy-initialized on first use ───────────────────
# These are deferred to reduce startup memory below 512 MiB for Cloud Run.
_self_improvement_engine: Any = None
_bank_manager: Any = None
_sota_ingestion: Any = None
_validator_16d: Any = None
_cognitive_map: Any = None
_deep_introspector: Any = None
_parallel_validation: Any = None
_supervisor: Any = None
_n_stroke_engine: Any = None
_branch_executor: Any = None
_roadmap: Any = None
_sandbox_orchestrator: Any = None


def _get_heavy_singletons():
    """Nuclear Lazy Load: performing all engine imports locally and atomically."""
    global _router, _graph, _bank, _tribunal, _mcp_manager, _executor
    global _sorter, _scope_evaluator, _refinement_loop, _conversation_engine
    global _jit_booster, _engram_generator, _model_selector
    global _director, _b_unit, _daemon, _notification_bus, _stance_engine
    global _self_improvement_engine, _bank_manager, _sota_ingestion, _validator_16d
    global _cognitive_map, _deep_introspector, _parallel_validation
    global _supervisor, _n_stroke_engine, _branch_executor, _roadmap, _sandbox_orchestrator
    global _refinement_supervisor, _intent_discovery, _async_fluid_executor, _jit_designer
    global _buddy_memory, CognitiveLens, Engram, Envelope

    if _router is not None:
        return  # Already initialized

    with _init_lock:
        if _router is not None:
            return

        # SURGICAL IMPORTS
        from engine.config import settings
        from engine.router import MandateRouter, ConversationalIntentDiscovery
        from engine.graph import CognitiveGraph, TopologicalSorter
        from engine.psyche_bank import PsycheBank
        from engine.tribunal import Tribunal, Engram as _Engram
        from engine.mcp_manager import MCPManager
        from engine.executor import JITExecutor, Envelope as _Envelope
        from engine.scope_evaluator import ScopeEvaluator
        from engine.refinement import RefinementLoop
        from engine.memory_tier_orchestrator import get_memory_orchestrator
        from engine.conversation import ConversationEngine
        from engine.jit_booster import JITBooster
        from engine.engram_visual import VisualEngramGenerator
        from engine.mandate_executor import make_live_work_fn as _make_live_work_fn
        from engine.model_selector import ModelSelector
        from engine.director import Director
        from engine.b_unit import BUnit
        from engine.daemon import BackgroundDaemon
        from engine.bus import get_bus
        from engine.stance import get_stance_engine
        from engine.self_improvement import SelfImprovementEngine
        from engine.knowledge_banks.manager import BankManager
        from engine.sota_ingestion import SOTAIngestionEngine
        from engine.validator_16d import Validator16D
        from engine.cognitive_map import get_cognitive_map
        from engine.deep_introspector import get_deep_introspector
        from engine.pipeline import NStrokeEngine, TwoStrokeEngine
        from engine.branch_executor import BranchExecutor
        from engine.roadmap import RoadmapManager
        from engine.sandbox import SandboxOrchestrator
        from engine.refinement_supervisor import RefinementSupervisor
        from engine.async_fluid_executor import AsyncFluidExecutor
        from engine.jit_designer import JITDesigner
        from engine.parallel_validation import ParallelValidationPipeline
        from engine.buddy_cognition import CognitiveLens as _CognitiveLens

        # Explicit global assignment
        global make_live_work_fn, CognitiveLens, Engram, Envelope
        make_live_work_fn = _make_live_work_fn
        CognitiveLens = _CognitiveLens
        Engram = _Engram
        Envelope = _Envelope

        # 1. Base components
        _router = MandateRouter()
        _graph = CognitiveGraph()
        _bank = PsycheBank()
        _tribunal = Tribunal(bank=_bank)
        _mcp_manager = MCPManager()
        _executor = JITExecutor(mcp_manager=_mcp_manager, tribunal=_tribunal)
        _sorter = TopologicalSorter()
        _scope_evaluator = ScopeEvaluator()
        _refinement_loop = RefinementLoop()
        _buddy_memory = get_memory_orchestrator().buddy_store
        _conversation_engine = ConversationEngine(memory_store=_buddy_memory)
        _jit_booster = JITBooster()
        _engram_generator = VisualEngramGenerator()
        _model_selector = ModelSelector()
        _refinement_supervisor = RefinementSupervisor()
        _intent_discovery = ConversationalIntentDiscovery()
        _async_fluid_executor = AsyncFluidExecutor()
        _jit_designer = JITDesigner()

        _director = Director(_broadcast)
        _b_unit = BUnit(_broadcast)
        _daemon = BackgroundDaemon(_broadcast)

        # Re-register notification bus with initialized components
        _notification_bus = get_bus()
        _notification_bus.register_broadcast(_broadcast)
        _notification_bus.subscribe("ALL", lambda e: _director.on_bus_event(e.level, e.payload))
        _notification_bus.subscribe("INSIGHT", lambda e: _b_unit.on_bus_event(e.level, e.payload))
        _notification_bus.subscribe("CRITICAL", _on_tribunal_critical)

        # 1.1 Stance engine
        _stance_engine = get_stance_engine()

        # 2. Heavy components
        _self_improvement_engine = SelfImprovementEngine(booster=_jit_booster, bank=_bank)
        _bank_manager = BankManager()
        _sota_ingestion = SOTAIngestionEngine(manager=_bank_manager, tribunal=_tribunal)
        _validator_16d = Validator16D()

        _cognitive_map = get_cognitive_map()
        _cognitive_map.register_update_callback(_broadcast)
        _deep_introspector = get_deep_introspector()
        _deep_introspector.register_update_callback(_broadcast)

        _parallel_validation = ParallelValidationPipeline(
            broadcast_fn=_broadcast, tribunal=_tribunal, validator=_validator_16d
        )
        _supervisor = TwoStrokeEngine(
            router=_router, booster=_jit_booster, tribunal=_tribunal,
            sorter=_sorter, executor=_executor, scope_evaluator=_scope_evaluator,
            refinement_loop=_refinement_loop, broadcast_fn=_broadcast,
        )
        _n_stroke_engine = NStrokeEngine(
            router=_router, booster=_jit_booster, tribunal=_tribunal,
            sorter=_sorter, executor=_executor, scope_evaluator=_scope_evaluator,
            refinement_loop=_refinement_loop, mcp_manager=_mcp_manager,
            model_selector=_model_selector, refinement_supervisor=_refinement_supervisor,
            broadcast_fn=_broadcast, async_fluid_executor=_async_fluid_executor,
        )
        _n_stroke_engine.register_director(_director)
        _branch_executor = BranchExecutor(
            router=_router, booster=_jit_booster, tribunal=_tribunal,
            sorter=_sorter, jit_executor=_executor, scope_evaluator=_scope_evaluator,
            refinement_loop=_refinement_loop, broadcast_fn=_broadcast,
        )
        _roadmap = RoadmapManager()
        _sandbox_orchestrator = SandboxOrchestrator(
            max_workers=settings.sandbox_max_workers,
            broadcast_fn=_broadcast, booster=_jit_booster, bank=_bank,
        )
        _loop_stats["interval_seconds"] = 600 if settings.lean_mode else 30

        # 3. Route initialization (Lazy-loaded to keep import memory low)
        from studio.routes import introspection as ir
        from studio.routes import buddy as br
        from studio.routes import pipeline as pr
        from studio.routes import sandbox as sr
        from studio.routes import knowledge as kr
        from studio.routes import vlt as vr
        from studio.routes import core as cr
        from studio.routes import studio as str_r

        def __create_n_stroke(max_strokes: int):
            from engine.pipeline import NStrokeEngine as _NSE
            return _NSE(
                router=_router, booster=_jit_booster, tribunal=_tribunal,
                sorter=_sorter, executor=_executor, scope_evaluator=_scope_evaluator,
                refinement_loop=_refinement_loop, mcp_manager=_mcp_manager,
                model_selector=_model_selector, refinement_supervisor=_refinement_supervisor,
                broadcast_fn=_broadcast, max_strokes=max_strokes,
                async_fluid_executor=_async_fluid_executor,
            )

        ir.set_broadcast(_broadcast)
        br.init(buddy_memory=_buddy_memory, conversation_engine=_conversation_engine, broadcast_fn=_broadcast)
        pr.init(
            intent_discovery=_intent_discovery, supervisor=_supervisor,
            n_stroke_engine=_n_stroke_engine, async_fluid_executor=_async_fluid_executor,
            branch_executor=_branch_executor, mcp_manager=_mcp_manager,
            broadcast_fn=_broadcast, create_n_stroke_fn=__create_n_stroke,
        )
        sr.init(sandbox_orchestrator=_sandbox_orchestrator, roadmap=_roadmap, broadcast_fn=_broadcast)
        kr.init(bank_manager=_bank_manager, sota_ingestion=_sota_ingestion, broadcast_fn=_broadcast)
        vr.init(broadcast_fn=_broadcast)
        cr.init(
            parallel_validation=_parallel_validation,
            notification_bus=_notification_bus,
            stance_engine=_stance_engine,
            broadcast_fn=_broadcast,
        )

        app.include_router(ir.router)
        app.include_router(br.router)
        app.include_router(pr.router)
        app.include_router(sr.router)
        app.include_router(kr.router)
        app.include_router(vr.router)
        app.include_router(cr.router)
        app.include_router(str_r.router)

# ── Autonomous improvement loop state ─────────────────────────────────────────
_loop_active: bool = False
_loop_task: asyncio.Task[None] | None = None
_daemon_task: asyncio.Task[None] | None = None
_loop_stats: dict[str, Any] = {
    "active": False,
    "cycles_completed": 0,
    "last_run_at": None,
    "next_run_at": None,
    "interval_seconds": 600,  # Default for safety; refined in _get_heavy_singletons
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

            # 1. Self-improvement cycle (asynchronous)
            report = await _self_improvement_engine.run()
            _broadcast({"type": "self_improve", "report": report.to_dict()})

            # 2. Roadmap sandbox run (asynchronous)
            items = _roadmap.all_items()
            features = [
                {"text": i.description, "title": i.title, "roadmap_item_id": i.id}
                for i in items
            ]
            reports = await _sandbox_orchestrator.run_parallel(features)
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
        except Exception as exc:
            _broadcast(
                {"type": "auto_loop", "phase": "error", "error": str(exc)})


# ── App ─────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def _lifespan(_: FastAPI):
    # DOCKER-OPTIMIZED: Do not call _get_heavy_singletons on boot.
    # We want the container to listen on 8080 instantly to pass health-checks.
    # Individual routes (and health checks) will call it on-demand.
    if _jit_booster is not None:
        _jit_booster.start_background_refresh()

    async def _purge_psychebank_loop() -> None:
        """Hourly background task: evict TTL-expired PsycheBank rules."""
        while True:
            await asyncio.sleep(3600)
            if _bank is not None:
                removed = _bank.purge_expired()
                if removed:
                    _broadcast({"type": "psychebank_purge", "removed": removed})

    purge_task = asyncio.create_task(_purge_psychebank_loop())
    try:
        yield
    finally:
        purge_task.cancel()
        with suppress(asyncio.CancelledError):
            await purge_task
        if _jit_booster is not None:
            _jit_booster.stop_background_refresh()


app = FastAPI(title="TooLoo V2 Governor Dashboard",
              version="2.1.0", lifespan=_lifespan)


# ── Routes ───────────────────────────────────────────────────────────────────

# Route modules are now imported and initialized inside _get_heavy_singletons
# to ensure they receive fully initialized singletons in Lean Mode.

app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(str(_STATIC / "favicon.ico"))


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index() -> HTMLResponse:
    html = (_STATIC / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
async def serve_buddy_demo() -> HTMLResponse:
    """Standalone SOTA real-time Buddy demo — DAG visualization + EQ chat."""
    html = (_STATIC / "buddy_demo.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/v2/health")
async def get_health():
    # Health check MUST BE LIGHT to pass Cloud Run port probes within 512 MiB.
    # We do NOT call _get_heavy_singletons() here; it will happen on the first mandate.
    
    import psutil
    import os
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        rss_mb = round(mem_info.rss / (1024 * 1024), 2)
        vms_mb = round(mem_info.vms / (1024 * 1024), 2)
    except Exception:
        rss_mb = 0.0
        vms_mb = 0.0
    
    # Safely probe if singletons are loaded
    ready = (_router is not None)
    
    return {
        "status": "ok" if ready else "warmup",
        "version": "2.1.0",
        "lean_mode": _get_settings().lean_mode,
        "memory": {
            "rss_mb": rss_mb,
            "vms_mb": vms_mb,
        },
        "components": {
            "router": "up" if _router else "warmup",
            "graph": f"{len(_graph.nodes())} nodes" if _graph else "warmup",
            "psyche_bank": f"{len(await _bank.all_rules())} rules" if _bank else "warmup",
            "tribunal": "up" if _tribunal else "warmup",
            "cognitive_dreamer": "up" if _daemon else "warmup",
            "executor": "up" if _executor else "warmup",
            "jit_booster": "up" if _jit_booster else "warmup",
            "engram_engine": "up" if _engram_generator else "warmup",
            "self_improvement": "up" if _self_improvement_engine else "warmup",
            "supervisor": "up" if _supervisor else "warmup",
            "intent_discovery": "up" if _intent_discovery else "warmup",
            "mcp_manager": "up" if _mcp_manager else "warmup",
            "model_selector": "up" if _model_selector else "warmup",
            "refinement_supervisor": "up" if _refinement_supervisor else "warmup",
            "n_stroke_engine": "up" if _n_stroke_engine else "warmup",
            "branch_executor": "up" if _branch_executor else "warmup",
            "validator_16d": "up" if _validator_16d else "warmup",
            "async_fluid_executor": "up" if _async_fluid_executor else "warmup",
            "buddy_memory": f"{_buddy_memory.entry_count()} entries" if _buddy_memory else "warmup",
        }
    }


@app.post("/v2/dream/force-cycle")
async def force_dream_cycle() -> dict[str, Any]:
    try:
        report = await _daemon._dreamer.run_dream_cycle()
        return {
            "status": "success",
            "report": {
                "fused_concepts": report.fused_concepts,
                "insight_extracted": report.insight_extracted,
                "garbage_purged_count": report.garbage_purged_count,
                "consolidated_count": report.consolidated_count
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/v2/workspace/roots")
async def workspace_roots() -> dict[str, Any]:
    """Return the list of configured workspace roots (multi-root support)."""
    roots = get_workspace_roots()
    return {
        "roots": [str(r) for r in roots],
        "count": len(roots),
    }


class MandateRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    text: str
    session_id: str = ""
    # User-selected intent override (empty = auto-detect)
    forced_intent: str = ""


class IntentClarifyRequest(BaseModel):
    text: str
    session_id: str = ""


class BuddyChatRequest(BaseModel):
    text: str
    session_id: str = ""
    depth_level: int = 1  # 1=Chat/Explore, 2=JIT Validation (deeper signals)
    # User-selected mode/intent override (empty = auto-detect)
    # Accepts technical intents (EXPLAIN, IDEATE, DESIGN, AUDIT) and human
    # conversation modes (CASUAL, SUPPORT, DISCUSS, COACH, PRACTICE).
    forced_intent: str = ""


class BuddyListenRequest(BaseModel):
    text: str = Field(default="", max_length=2000)
    session_id: str = ""  # optional — enables context-aware suggestions


# ── Buddy Chat fast-path ─────────────────────────────────────────────────────

# Intents that require full N-Stroke execution and must not be served via chat.
_EXECUTION_INTENTS = frozenset({"BUILD", "DEBUG", "SPAWN_REPO"})


@app.post("/v2/buddy/chat")
async def buddy_chat_fast_path(req: BuddyChatRequest) -> dict[str, Any]:
    """Lightweight Buddy Chat fast-path for exploratory / conversational intents.

    Routes the mandate and:
      - Returns HTTP 400 for execution intents (BUILD / DEBUG / SPAWN_REPO),
        instructing the client to use /v2/pipeline or /v2/n-stroke instead.
      - For IDEATE / EXPLAIN / DESIGN / AUDIT, fetches SOTA signals via
        JITBooster, runs a Tribunal scan, then generates a response via
        ConversationEngine (ModelGarden → Gemini Direct → keyword fallback).

    Does NOT trigger the N-Stroke Engine or the SimulationGate.
    """
    t0 = time.monotonic()
    mandate_id = f"bc-{uuid.uuid4().hex[:8]}"
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"

    # 1. Route (chat path — no circuit-breaker counter increments)
    route = _router.route_chat(req.text)

    # 1a. User-selected intent override (includes social modes)
    _CHAT_VALID_INTENTS = {
        "AUDIT", "DESIGN", "EXPLAIN", "IDEATE",
        "CASUAL", "SUPPORT", "DISCUSS", "COACH", "PRACTICE",
    }
    if req.forced_intent and req.forced_intent.upper() in _CHAT_VALID_INTENTS:
        from engine.router import compute_buddy_line
        route.intent = req.forced_intent.upper()
        route.confidence = 1.0
        route.buddy_line = compute_buddy_line(route.intent, route.confidence)

    # 2. Gate execution intents — they must use the N-Stroke pipeline
    if route.intent in _EXECUTION_INTENTS:
        return {
            "error": (
                f"Intent '{route.intent}' requires N-Stroke execution. "
                "Use /v2/pipeline or /v2/n-stroke for build / debug / spawn tasks."
            ),
            "intent": route.intent,
            "confidence": route.confidence,
        }

    # 3. JIT SOTA grounding — depth_level drives how deep JITBooster searches
    _action_context_map = {
        1: req.text[:200],
        2: f"deep_research: {req.text[:300]}",
    }
    jit_result = _jit_booster.fetch_for_node(
        route=route,
        node_type="chat",
        action_context=_action_context_map.get(
            req.depth_level, req.text[:200]),
        vertex_model_id=None,
    )
    _router.apply_jit_boost(route, jit_result.boosted_confidence)

    # 4. Tribunal scan (OWASP poison guard)
    engram = Engram(
        slug=mandate_id,
        intent=route.intent,
        logic_body=req.text,
        domain="conversation",
        mandate_level="L1",
    )
    tribunal_result = await _tribunal.evaluate(engram)

    # 5. Generate response via ConversationEngine (ModelGarden inside)
    conv_result = _conversation_engine.process(
        req.text, route, session_id, jit_result=jit_result
    )

    # 6. JIT Designer — compute visual rendering directive
    memory_recalled = bool(_buddy_memory.find_relevant(req.text, limit=1))
    design_directive = _jit_designer.evaluate(
        intent=route.intent,
        emotional_state=conv_result.emotional_state,
        confidence=route.confidence,
        response_text=conv_result.response_text,
        memory_recalled=memory_recalled,
        jit_signal_count=len(jit_result.signals) if jit_result.signals else 0,
    )

    # 7. SSE broadcast — includes emotional_state so the demo DAG can update EQ ring
    _broadcast({
        "type": "buddy_chat_fast",
        "mandate_id": mandate_id,
        "session_id": session_id,
        "intent": route.intent,
        "confidence": route.confidence,
        "emotional_state": conv_result.emotional_state,
        "tribunal_passed": tribunal_result.passed,
        "jit_boost": jit_result.to_dict(),
        "design_directive": design_directive.to_dict(),
    })
    # Broadcast each thought card as a separate SSE event for storybook rendering
    for card in design_directive.thought_cards:
        _broadcast({
            "type": "thought",
            "mandate_id": mandate_id,
            "session_id": session_id,
            "card": card.to_dict(),
        })
    # Broadcast any VLT patches emitted by Buddy (spatial 3D mutations)
    for patch in conv_result.vlt_patches:
        _broadcast(patch.to_dict())

    # 8. Parse response into structured UI components → broadcast + HTTP payload
    ui_components = _jit_designer.parse_response_blocks(
        conv_result.response_text,
        intent=route.intent,
        palette_key=design_directive.palette_key,
    )
    for comp in ui_components:
        _broadcast({
            "type": "ui_component",
            "mandate_id": mandate_id,
            "session_id": session_id,
            "component": comp.to_dict(),
        })

    return {
        "mandate_id": mandate_id,
        "session_id": session_id,
        "response": conv_result.response_text,
        "intent": route.intent,
        "confidence": route.confidence,
        "suggestions": conv_result.suggestions,
        "model_used": conv_result.model_used,
        "emotional_state": conv_result.emotional_state,
        "tone": conv_result.tone,
        "jit_boost": jit_result.to_dict(),
        "tribunal_passed": tribunal_result.passed,
        "depth_level": req.depth_level,
        "visual_artifacts": [a.to_dict() for a in conv_result.visual_artifacts],
        "vlt_patches": [p.to_dict() for p in conv_result.vlt_patches],
        "design_directive": design_directive.to_dict(),
        "ui_components": [c.to_dict() for c in ui_components],
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
        "goal_progress": conv_result.goal_progress,
    }


# ── Buddy Chat SSE streaming endpoint ────────────────────────────────────────


@app.post("/v2/buddy/chat/stream")
async def buddy_chat_stream(req: BuddyChatRequest) -> StreamingResponse:
    """SSE streaming path for Buddy Chat.

    Identical pre-flight to /v2/buddy/chat (route → JIT → Tribunal), then
    yields a ``text/event-stream`` response where:

      - ``type: "token"``        — plain prose text chunks
      - ``type: "ui_component"`` — structured Markdown block parsed into a
                                   UIComponent (swallowed from token stream)
      - ``type: "thought"``      — JIT Designer ThoughtCard (pipeline phases)
      - ``type: "done"``         — final metadata (suggestions, design_directive,
                                   latency_ms, model_used, etc.)

    The ``StreamInterceptor`` is responsible for routing chunks: prose text
    becomes ``token`` events immediately for progressive rendering, while
    fenced code blocks, numbered/bullet lists, and Markdown tables are buffered
    until complete and emitted as ``ui_component`` events.
    """
    t0 = time.monotonic()
    mandate_id = f"bcs-{uuid.uuid4().hex[:8]}"
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"

    # ── 1. Route ──────────────────────────────────────────────────────────────
    route = _router.route_chat(req.text)

    # ── 1a. User-selected intent override (includes social modes) ────────────
    _STREAM_VALID_INTENTS = {
        "AUDIT", "DESIGN", "EXPLAIN", "IDEATE",
        "CASUAL", "SUPPORT", "DISCUSS", "COACH", "PRACTICE",
    }
    if req.forced_intent and req.forced_intent.upper() in _STREAM_VALID_INTENTS:
        from engine.router import compute_buddy_line as _cbl
        route.intent = req.forced_intent.upper()
        route.confidence = 1.0
        route.buddy_line = _cbl(route.intent, route.confidence)

    if route.intent in _EXECUTION_INTENTS:
        async def _reject() -> AsyncGenerator[str, None]:
            payload = json.dumps({
                "type": "error",
                "error": (
                    f"Intent '{route.intent}' requires N-Stroke execution. "
                    "Use /v2/pipeline or /v2/n-stroke for build / debug / spawn tasks."
                ),
                "intent": route.intent,
            })
            yield f"data: {payload}\n\n"

        return StreamingResponse(_reject(), media_type="text/event-stream")

    # ── 2. JIT SOTA grounding ─────────────────────────────────────────────────
    jit_result = _jit_booster.fetch_for_node(
        route=route,
        node_type="chat",
        action_context=req.text[:200],
        vertex_model_id=None,
    )
    _router.apply_jit_boost(route, jit_result.boosted_confidence)

    # ── 3. Tribunal scan ──────────────────────────────────────────────────────
    engram = Engram(
        slug=mandate_id,
        intent=route.intent,
        logic_body=req.text,
        domain="conversation",
        mandate_level="L1",
    )
    tribunal_result = await _tribunal.evaluate(engram)

    # ── 4. JIT Designer — design directive + thought cards ───────────────────
    memory_recalled = bool(_buddy_memory.find_relevant(req.text, limit=1))
    design_directive = _jit_designer.evaluate(
        intent=route.intent,
        emotional_state="neutral",   # updated after stream in finalize
        confidence=route.confidence,
        response_text=req.text,      # approximation for emphasis; refined in done
        memory_recalled=memory_recalled,
        jit_signal_count=len(jit_result.signals) if jit_result.signals else 0,
    )

    # ── 5. prepare_stream — session tracking + prompt assembly ────────────────
    prompt, session, plan, tone, emotional_state = _conversation_engine.prepare_stream(
        text=req.text,
        route=route,
        session_id=session_id,
        jit_result=jit_result,
    )

    # ── 6. Build SSE generator ────────────────────────────────────────────────
    async def _stream() -> AsyncGenerator[str, None]:
        def _sse(payload: dict[str, Any]) -> str:
            return f"data: {json.dumps(payload)}\n\n"

        # Emit connection header
        yield _sse({"type": "connected", "mandate_id": mandate_id, "session_id": session_id})

        # Emit thought cards upfront
        for card in design_directive.thought_cards:
            yield _sse({"type": "thought", "mandate_id": mandate_id,
                        "session_id": session_id, "card": card.to_dict()})

        # If plan asks for clarification, emit that directly and short-circuit
        if plan.needs_clarification:
            yield _sse({"type": "token", "text": plan.clarification_question})
            full_response = plan.clarification_question
        elif plan.cache_hit:
            # 3-layer cache hit — emit cached response as a single token burst
            yield _sse({"type": "cache_hit", "mandate_id": mandate_id, "session_id": session_id})
            yield _sse({"type": "token", "text": plan.cache_response})
            full_response = plan.cache_response
        else:
            interceptor = StreamInterceptor(
                intent=route.intent,
                palette_key=design_directive.palette_key,
                designer=_jit_designer,
            )

            # Run sync Gemini streaming in a thread to avoid blocking the event loop
            chunks = await asyncio.to_thread(
                _conversation_engine.stream_chunks_sync, prompt
            )

            full_parts: list[str] = []
            for chunk in chunks:
                full_parts.append(chunk)
                for event in interceptor.feed(chunk):
                    event.update({"mandate_id": mandate_id,
                                 "session_id": session_id})
                    yield _sse(event)

            # Flush any remaining buffered block
            for event in interceptor.flush():
                event.update({"mandate_id": mandate_id,
                             "session_id": session_id})
                yield _sse(event)

            full_response = "".join(full_parts)

        # Finalize session tracking with the assembled response
        _conversation_engine.finalize_stream(
            session=session,
            buddy_text=full_response,
            plan=plan,
            tone=tone,
            route=route,
            emotional_state=emotional_state,
        )

        # Compute final design directive with actual response text
        final_directive = _jit_designer.evaluate(
            intent=route.intent,
            emotional_state=emotional_state,
            confidence=route.confidence,
            response_text=full_response,
            memory_recalled=memory_recalled,
            jit_signal_count=len(
                jit_result.signals) if jit_result.signals else 0,
        )

        suggestions = _FOLLOWUPS.get(route.intent, [])

        # Broadcast to global SSE clients
        _broadcast({
            "type": "buddy_chat_fast",
            "mandate_id": mandate_id,
            "session_id": session_id,
            "intent": route.intent,
            "confidence": route.confidence,
            "emotional_state": emotional_state,
            "tribunal_passed": tribunal_result.passed,
            "jit_boost": jit_result.to_dict(),
            "design_directive": final_directive.to_dict(),
        })

        profile = _conversation_engine.get_user_profile()
        ct_load = CognitiveLens.analyze(req.text).cognitive_load
        yield _sse({
            "type": "done",
            "mandate_id": mandate_id,
            "session_id": session_id,
            "intent": route.intent,
            "confidence": route.confidence,
            "emotional_state": emotional_state,
            "suggestions": suggestions,
            "model_used": "cache" if plan.cache_hit else "gemini-stream",
            "tribunal_passed": tribunal_result.passed,
            "design_directive": final_directive.to_dict(),
            "jit_boost": jit_result.to_dict(),
            "latency_ms": round((time.monotonic() - t0) * 1000, 2),
            "cache_hit": plan.cache_hit,
            "expertise_label": profile.expertise_label(),
            "cognitive_load": ct_load,
            "goal_progress": int(round(len(profile.completed_goals) / max(1, len(profile.completed_goals) + len(profile.active_goals)) * 100)),
        })

    return StreamingResponse(_stream(), media_type="text/event-stream")


# ── Buddy Active Listener endpoint ──────────────────────────────────────────


@app.post("/v2/buddy/listen")
async def buddy_listen(req: BuddyListenRequest) -> dict[str, Any]:
    """Ultra-low-latency active listener for real-time typing feedback.

    Analyzes a partial user prompt with pure heuristics (no LLM calls) and
    returns comprehension signals to drive the Active Listener UI:
      - comprehension_level : clear | vague | complex | listening
      - visual_indicator    : nodding | thinking | listening | confused_tilt
      - prompt_suggestions  : 1-2 actionable tips to tighten the prompt
      - detected_intent     : best-guess intent (or "")
      - word_count          : int
    """
    session_context = ""
    if req.session_id:
        history = _conversation_engine.session_history(req.session_id)
        if history:
            recent_intents = [t["intent"]
                              for t in history[-4:] if t.get("role") == "user"]
            if recent_intents:
                session_context = recent_intents[-1]
    result = analyze_partial_prompt(req.text, session_context=session_context)
    return result


# ── Buddy Memory / Profile / Goals / Cache endpoints ─────────────────────────
# MOVED to studio/routes/buddy.py — included via app.include_router() above.


# ── Buddy conversation modes catalogue ──────────────────────────────────────

# Human-like social interaction modes with full metadata for the UI.
_BUDDY_MODES: list[dict[str, Any]] = [
    # ── Technical modes ──────────────────────────────────────────────────────
    {
        "id": "auto",
        "label": "Auto",
        "icon": "⚡",
        "category": "technical",
        "description": "Buddy auto-detects the best mode from your message.",
        "tone": "adaptive",
        "example_prompt": "What are you working on?",
    },
    {
        "id": "build",
        "label": "Build",
        "icon": "🔨",
        "category": "technical",
        "description": "Implement features, scaffold services, write and wire code.",
        "tone": "constructive",
        "example_prompt": "Build a REST endpoint that…",
    },
    {
        "id": "debug",
        "label": "Debug",
        "icon": "🔍",
        "category": "technical",
        "description": "Trace failures, find root causes, lock in regression tests.",
        "tone": "analytical",
        "example_prompt": "This keeps crashing with…",
    },
    {
        "id": "design",
        "label": "Design",
        "icon": "🎨",
        "category": "technical",
        "description": "Shape UIs, wireframes, component specs, and design systems.",
        "tone": "creative",
        "example_prompt": "Design a dashboard that shows…",
    },
    {
        "id": "ideate",
        "label": "Ideate",
        "icon": "💡",
        "category": "technical",
        "description": "Brainstorm, compare approaches, and explore the solution space.",
        "tone": "exploratory",
        "example_prompt": "What's the best way to approach…",
    },
    {
        "id": "audit",
        "label": "Audit",
        "icon": "🛡",
        "category": "technical",
        "description": "Security scan, dependency review, OWASP, and posture reporting.",
        "tone": "precise",
        "example_prompt": "Audit this module for vulnerabilities…",
    },
    # ── Human-like conversation modes ────────────────────────────────────────
    {
        "id": "casual",
        "label": "Casual",
        "icon": "💬",
        "category": "human",
        "description": "Just talk. Small talk, random topics, genuine conversation — no agenda.",
        "tone": "warm",
        "example_prompt": "Hey, how are you doing?",
    },
    {
        "id": "support",
        "label": "Support",
        "icon": "🤝",
        "category": "human",
        "description": "Emotional support and active listening — Buddy is here for you.",
        "tone": "empathetic",
        "example_prompt": "I've been feeling really overwhelmed lately…",
    },
    {
        "id": "discuss",
        "label": "Discuss",
        "icon": "🗣",
        "category": "human",
        "description": "Open intellectual discussion — opinions, debates, big ideas.",
        "tone": "conversational",
        "example_prompt": "What do you think about…",
    },
    {
        "id": "coach",
        "label": "Coach",
        "icon": "🎯",
        "category": "human",
        "description": "Personalized coaching — goals, accountability, and your next real action.",
        "tone": "encouraging",
        "example_prompt": "I want to improve my…",
    },
    {
        "id": "practice",
        "label": "Practice",
        "icon": "🎭",
        "category": "human",
        "description": "Roleplay scenarios — interview prep, social skills, difficult conversations.",
        "tone": "engaged",
        "example_prompt": "Let's practice a job interview for…",
    },
]


@app.get("/v2/buddy/modes")
async def get_buddy_modes() -> dict[str, Any]:
    """Return the full catalogue of Buddy conversation modes.

    Includes both technical modes (BUILD / DEBUG / DESIGN / IDEATE / AUDIT)
    and the new human-like social interaction modes (CASUAL / SUPPORT /
    DISCUSS / COACH / PRACTICE).  The UI uses this to render the mode
    selector with icons, descriptions, and example prompts.
    """
    technical = [m for m in _BUDDY_MODES if m["category"] == "technical"]
    human = [m for m in _BUDDY_MODES if m["category"] == "human"]
    return {
        "modes": _BUDDY_MODES,
        "technical_modes": technical,
        "human_modes": human,
        "total": len(_BUDDY_MODES),
    }


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


@app.post("/v2/mandate")
async def route_mandate(req: MandateRequest) -> dict[str, Any]:
    _get_heavy_singletons()
    t0 = time.monotonic()
    mandate_id = f"m-{uuid.uuid4().hex[:8]}"

    # 0. Cognitive Analysis (Emotional Rigging)
    cog_turn = CognitiveLens.analyze(req.text)
    # Map load to buddy scaling/bubbles
    _director.handle_cognitive_state(mood="idle", load=cog_turn.cognitive_load)

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
    tribunal_result = await _tribunal.evaluate(engram)
    _broadcast({"type": "tribunal", "mandate_id": mandate_id,
               "result": tribunal_result.to_dict()})
    
    # Notify Director of tribunal outcome
    _director.on_bus_event("ALL", {"type": "tribunal_result", "passed": tribunal_result.passed})

    # 4. Build a toy DAG plan from route
    spec: list[tuple[str, list[str]]] = [
        (f"{mandate_id}-ingest", []),
        (f"{mandate_id}-analyse", [f"{mandate_id}-ingest"]),
        (f"{mandate_id}-implement", [f"{mandate_id}-analyse"]),
        (f"{mandate_id}-validate", [f"{mandate_id}-implement"]),
    ]
    plan = _sorter.sort(spec)
    _broadcast({"type": "plan", "mandate_id": mandate_id, "waves": plan})

    # 4. Action scope evaluation — understand full plan before allocating resources
    scope = await _scope_evaluator.evaluate(plan, intent=route.intent)
    _broadcast({"type": "scope", "mandate_id": mandate_id,
               "scope": scope.to_dict()})

    # 5. Fan-out execution — real LLM-powered nodes (falls back to symbolic
    #    when Vertex AI + Gemini Direct are both unavailable)
    envelopes = [
        Envelope(  # type: ignore[call-arg]
            mandate_id=node_id,
            intent=route.intent,
            domain="backend",
            metadata={"wave": i, "nodes": wave},
        )
        for i, wave in enumerate(plan)
        for node_id in wave
    ]

    _live_work = make_live_work_fn(
        mandate_text=req.text,
        intent=route.intent,
        jit_signals=jit_result.signals,
    )

    exec_results = await _executor.fan_out_dag(
        _live_work,
        envelopes,
        {node_id: deps for node_id, deps in spec},
        max_workers=scope.recommended_workers,
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
async def chat_with_buddy(req: ChatRequest) -> dict[str, Any]:
    _get_heavy_singletons()
    t0 = time.monotonic()
    mandate_id = f"c-{uuid.uuid4().hex[:8]}"
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"

    # 1. Route (conversational path — does not touch circuit-breaker counters)
    route = _router.route_chat(req.text)

    # 1a. User-selected intent override — full confidence, recompute buddy_line
    _VALID_INTENTS = {
        "BUILD", "DEBUG", "AUDIT", "DESIGN", "EXPLAIN", "IDEATE", "SPAWN_REPO",
        "CASUAL", "SUPPORT", "DISCUSS", "COACH", "PRACTICE",
    }
    if req.forced_intent and req.forced_intent.upper() in _VALID_INTENTS:
        route.intent = req.forced_intent.upper()
        route.confidence = 1.0
        route.buddy_line = compute_buddy_line(route.intent, route.confidence)

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
    tribunal_result = await _tribunal.evaluate(engram)

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
    # Broadcast VLT patches for spatial 3D mutations
    for patch in conv_result.vlt_patches:
        _broadcast(patch.to_dict())

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
    _get_heavy_singletons()
    nodes = _graph.nodes()
    edges = [{"from": u, "to": v} for u, v in _graph.edges()]
    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}


@app.get("/v2/psyche-bank")
async def psyche_bank_rules() -> dict[str, Any]:
    _get_heavy_singletons()
    return await _bank.to_dict()


@app.get("/v2/router-status")
async def router_status() -> dict[str, Any]:
    _get_heavy_singletons()
    return _router.status()


@app.post("/v2/router-reset")
async def router_reset() -> dict[str, Any]:
    _get_heavy_singletons()
    _router.reset()
    return {"reset": True, "status": _router.status()}


# ── 16-Dimension Validator endpoints ─────────────────────────────────────────

class Validate16DRequest(BaseModel):
    mandate_id: str
    intent: str
    code_snippet: str | None = None
    test_pass_rate: float = 1.0
    estimated_input_tokens: int = 500
    estimated_output_tokens: int = 1000
    latency_p50_ms: float = 1000.0
    latency_p90_ms: float = 2000.0


@app.post("/v2/validate/16d")
async def validate_16d(req: Validate16DRequest) -> dict[str, Any]:
    """Run the 16-dimension pre-execution validation gate."""
    result = _validator_16d.validate(
        mandate_id=req.mandate_id,
        intent=req.intent,
        code_snippet=req.code_snippet,
        test_pass_rate=req.test_pass_rate,
        estimated_input_tokens=req.estimated_input_tokens,
        estimated_output_tokens=req.estimated_output_tokens,
        latency_p50_ms=req.latency_p50_ms,
        latency_p90_ms=req.latency_p90_ms,
    )
    _broadcast({"type": "tribunal", "sub": "validate_16d",
                "gate": result.autonomous_gate_pass,
                "composite": result.composite_score})
    return result.to_dict()


@app.get("/v2/validate/16d/schema")
async def validate_16d_schema() -> dict[str, Any]:
    """Return dimension names, thresholds, and autonomous confidence target."""
    return {
        "autonomous_confidence_threshold": _validator_16d.AUTONOMOUS_CONFIDENCE_THRESHOLD,
        "dimensions": [
            {"name": name, "threshold": threshold}
            for name, threshold in sorted(_validator_16d._THRESHOLDS.items())
        ],
    }


# ── AsyncFluidExecutor status endpoint ───────────────────────────────────────

@app.get("/v2/async-exec/status")
async def async_exec_status() -> dict[str, Any]:
    """Return runtime stats for the AsyncFluidExecutor."""
    hist = _async_fluid_executor._latency_histogram
    return {
        "max_workers": _async_fluid_executor._max_workers,
        "histogram_size": len(hist),
        "latency_p50_ms": round(sorted(hist)[len(hist) // 2] * 1000, 2) if hist else None,
        "status": "up",
    }


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
    report_dict = report.to_dict()
    return {"self_improvement": report_dict, "report": report_dict, "latency_ms": latency_ms}


@app.post("/v2/self-improve/parallel")
async def self_improve_parallel() -> dict[str, Any]:
    """Self-improvement with parallel validation pipeline.

    Combines component assessment with concurrent tribunal + 16D + test
    validation.  All stages run simultaneously per file — results stream
    live via SSE as each stage completes.

    SSE event types emitted:
      - parallel_validation_start
      - parallel_validation_stage (per file × per stage)
      - parallel_validation_complete
    """
    t0 = time.monotonic()
    report = await _self_improvement_engine.run_parallel(broadcast_fn=_broadcast)
    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    report_dict = report.to_dict()
    return {"self_improvement": report_dict, "report": report_dict, "latency_ms": latency_ms}


@app.post("/v2/validate/parallel")
async def validate_parallel(
    files: list[str] | None = None,
) -> dict[str, Any]:
    """Run parallel validation (tribunal + 16D + tests) on specified files.

    If no files are specified, validates all 17 engine components.
    Returns a ValidationReport with per-file, per-stage results.
    """
    from engine.parallel_validation import FileChange, ParallelValidationPipeline
    from engine.self_improvement import _COMPONENT_SOURCE

    pipeline = ParallelValidationPipeline(
        broadcast_fn=_broadcast,
        tribunal=_tribunal,
        validator=_validator_16d,
    )
    if files:
        changes = [FileChange(path=f) for f in files]
    else:
        changes = [
            FileChange(path=src, component=comp)
            for comp, src in _COMPONENT_SOURCE.items()
        ]
    report = await pipeline.validate_changes(changes)
    return report.to_dict()


class SelfImproveApplyRequest(BaseModel):
    """Apply a single FIX suggestion from a self-improvement assessment.

    Law 20 (Amended — Autonomous Execution Authority): TooLoo may approve and
    apply its own engine improvements without waiting for explicit human sign-off,
    subject to three invariants:
      1. Tribunal OWASP scan passes (legal / ethical safety gate).
      2. Activity is restricted to engine/ components inside this workspace.
      3. If internal confidence < AUTONOMOUS_CONFIDENCE_THRESHOLD (0.99), a
         ``consultation_recommended`` event is broadcast so the user can review
         — but execution is NOT blocked.

    ``confirmed=True`` is still accepted for callers that prefer explicit consent
    (e.g. the UI Approve button).  When ``AUTONOMOUS_EXECUTION_ENABLED=True`` the
    gate passes automatically regardless of ``confirmed``.
    """
    suggestion: str           # full "FIX N: file.py:LINE — desc\nCODE:\n..." string
    component: str            # engine component name (for logging)
    # caller-supplied confidence for this suggestion (0-1)
    confidence: float = 1.0
    confirmed: bool = False   # explicit human approval; not required in autonomous mode


@app.post("/v2/self-improve/apply")
async def self_improve_apply(req: SelfImproveApplyRequest) -> dict[str, Any]:
    """Autonomous code application of a self-improvement suggestion.

    Flow:
      1. Law 20 autonomy gate — auto-approve when AUTONOMOUS_EXECUTION_ENABLED=True,
         or when req.confirmed=True.  If confidence < AUTONOMOUS_CONFIDENCE_THRESHOLD,
         broadcast a consultation_recommended event (advisory only, never blocking).
      2. Parse the FIX block to extract file path, old code anchor, new code.
      3. Use MCPManager.file_read to load the target file.
      4. Validate the old-code anchor exists (exact substring match).
      5. Use MCPManager.file_write to apply the patch atomically.
      6. Run tests via MCPManager.run_tests to verify correctness.
      7. On test failure, restore the original via a second file_write (revert).
      8. Broadcast result and return structured response.

    Returns:
        ``{"status": "applied"|"reverted"|"skipped", "file": ..., "tests": ...}``
    """
    import re as _re

    # ── Law 20 (Amended) autonomy gate ────────────────────────────────────
    # Grant execution when autonomous mode is on OR explicit confirmation given.
    # Always block if neither condition holds.
    autonomous = AUTONOMOUS_EXECUTION_ENABLED
    if not autonomous and not req.confirmed:
        return {
            "status": "skipped",
            "reason": (
                "Law 20: explicit confirmation required when autonomous execution "
                "is disabled. Set confirmed=true or enable AUTONOMOUS_EXECUTION_ENABLED."
            ),
        }

    # Advisory consultation signal when confidence below threshold
    if req.confidence < AUTONOMOUS_CONFIDENCE_THRESHOLD:
        _broadcast({
            "type": "consultation_recommended",
            "component": req.component,
            "confidence": req.confidence,
            "threshold": AUTONOMOUS_CONFIDENCE_THRESHOLD,
            "reason": (
                f"Confidence {req.confidence:.2f} is below the autonomous threshold "
                f"{AUTONOMOUS_CONFIDENCE_THRESHOLD}. Proceeding autonomously — review suggested."
            ),
        })

    sugg = req.suggestion

    # ── Parse FIX block ───────────────────────────────────────────────────
    fix_m = _re.match(
        r"FIX\s+\d+:\s*([\w/\.\-]+\.py):(\d+)\s*[—\-]+\s*(.+)", sugg
    )
    if not fix_m:
        return {"status": "skipped", "reason": "Suggestion does not match FIX format."}

    file_rel = fix_m.group(1).strip()
    description = fix_m.group(3).strip()

    # Extract CODE block from suggestion string
    code_lines: list[str] = []
    in_code = False
    for line in sugg.splitlines():
        if line.strip().startswith("CODE:"):
            in_code = True
            rest = line.strip()[5:].strip()
            if rest:
                code_lines.append(rest)
        elif in_code:
            code_lines.append(line)
    code_snippet = "\n".join(code_lines).strip()

    if not code_snippet:
        return {
            "status": "skipped",
            "reason": "No CODE block found in suggestion — cannot apply blindly.",
        }

    # ── Path-jail check ───────────────────────────────────────────────────
    _repo_root = Path(__file__).resolve().parents[1]
    full_path = (_repo_root / file_rel).resolve()
    if not str(full_path).startswith(str(_repo_root)):
        return {"status": "skipped", "reason": "Path traversal blocked."}

    # ── Read current file ─────────────────────────────────────────────────
    read_result = _mcp_manager.call_uri(
        "mcp://tooloo/file_read", path=file_rel)
    if not read_result.success:
        return {"status": "skipped", "reason": f"Could not read {file_rel}."}

    original: str = str(read_result.output or "")

    # ── The CODE block IS the new content for the described region.
    # We write the full new code as an append / targeted insert only when
    # an exact anchor exists; otherwise we reject to stay safe.
    # For simplicity: if the suggestion says to ADD something, append;
    # if it says to REPLACE, require an exact anchor in the existing file.
    if code_snippet not in original:
        # Write the snippet as a new file section (append with header comment)
        patched = (
            original.rstrip()
            + f"\n\n# daemon-apply [{req.component}]: {description}\n"
            + code_snippet
            + "\n"
        )
    else:
        # Already present — nothing to do
        return {"status": "skipped", "reason": "Code snippet already present in file."}

    # ── Apply via MCPManager.file_write ──────────────────────────────────
    write_result = _mcp_manager.call_uri(
        "mcp://tooloo/file_write", path=file_rel, content=patched
    )
    if not write_result.success:
        return {
            "status": "skipped",
            "reason": f"file_write failed: {write_result.output}",
        }

    _broadcast({
        "type": "self_improve_apply",
        "component": req.component,
        "file": file_rel,
        "description": description,
        "status": "patch_applied",
    })

    # ── Run tests via MCPManager ──────────────────────────────────────────
    test_result = _mcp_manager.call_uri(
        "mcp://tooloo/run_tests", module="tests", timeout=45
    )
    tests_passed = test_result.success
    test_summary = str(test_result.output or "")[:300]

    if tests_passed:
        _broadcast({
            "type": "self_improve_apply",
            "component": req.component,
            "file": file_rel,
            "status": "committed",
            "tests": test_summary,
        })
        return {
            "status": "applied",
            "file": file_rel,
            "component": req.component,
            "description": description,
            "tests": test_summary,
        }
    else:
        # Revert
        _mcp_manager.call_uri(
            "mcp://tooloo/file_write", path=file_rel, content=original
        )
        _broadcast({
            "type": "self_improve_apply",
            "component": req.component,
            "file": file_rel,
            "status": "reverted",
            "tests": test_summary,
        })
        return {
            "status": "reverted",
            "file": file_rel,
            "component": req.component,
            "description": description,
            "tests": test_summary,
        }


@app.get("/v2/events")
async def sse_stream() -> StreamingResponse:
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _sse_queues.append(q)

    async def _generate() -> AsyncGenerator[str, None]:
        try:
            # Heartbeat on connect
            yield f"data: {json.dumps({'type': 'connected', 'version': '2.1.0'})}\n\n"
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
        host=_get_settings().studio_host,
        port=_get_settings().studio_port,
        reload=_get_settings().studio_reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()


# ── Auto-improvement loop endpoints ──────────────────────────────────────────

@app.post("/v2/auto-loop/start")
async def start_auto_loop(interval_seconds: int = 30) -> dict[str, Any]:
    """Start the autonomous improvement loop (self-improve + roadmap run every N seconds)."""
    global _loop_active, _loop_task, _loop_stats
    if _loop_active:
        return {"started": False, "reason": "already running", "stats": dict(_loop_stats)}
    _loop_active = True
    _loop_stats["active"] = True
    _loop_stats["interval_seconds"] = max(
        10, interval_seconds)  # DEV MODE: floor 30→10
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
        "version": "2.1.0",
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


@app.get("/v2/daemon/status")
async def get_daemon_status():
    return {
        "active": _daemon.active,
        "pending_approvals": _daemon.awaiting_approval,
    }


@app.post("/v2/daemon/start")
async def start_daemon():
    global _daemon_task
    if not _daemon.active:
        _daemon_task = asyncio.create_task(_daemon.start())
        _daemon_task.add_done_callback(lambda _: None)
        return {"status": "started"}
    return {"status": "already_running"}


@app.post("/v2/daemon/stop")
async def stop_daemon():
    _daemon.stop()
    return {"status": "stopped"}


@app.post("/v2/daemon/approve/{proposal_id}")
async def approve_daemon_proposal(proposal_id: str):
    res = _daemon.approve(proposal_id)
    return res


# ── Cognitive Map + Deep Introspection endpoints ─────────────────────────────
# MOVED to studio/routes/introspection.py — included via app.include_router() above.


# Session state: phase, history, current prototype HTML, iteration count


