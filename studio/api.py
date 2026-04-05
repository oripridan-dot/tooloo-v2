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

from engine.branch_executor import (
    BRANCH_CLONE,
    BRANCH_FORK,
    BRANCH_SHARE,
    BranchExecutor,
    BranchSpec,
)
from engine.config import settings
from engine.config import (
    AUTONOMOUS_EXECUTION_ENABLED,
    AUTONOMOUS_CONFIDENCE_THRESHOLD,
    get_workspace_roots,
)
from engine.conversation import ConversationEngine, _FOLLOWUPS
from engine.buddy_cognition import CognitiveLens
from engine.buddy_memory import BuddyMemoryStore
from engine.firestore_memory import ColdMemoryFirestore
from engine.recursive_summarizer import RecursiveSummaryAgent
from engine.cognitive_map import get_cognitive_map
from engine.deep_introspector import get_deep_introspector
from engine.bus import get_bus, BusEvent, NotificationBus
from engine.stance import (
    get_stance_engine,
    get_active_stance,
    set_active_stance,
    CognitiveStanceEngine,
    Stance,
    StanceResult,
)
from engine.daemon import BackgroundDaemon
from engine.engram_visual import VisualEngramGenerator
from engine.executor import Envelope, JITExecutor
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.jit_booster import JITBooster
from engine.knowledge_banks.manager import BankManager
from engine.mandate_executor import make_live_work_fn
from engine.mcp_manager import MCPManager
from engine.model_garden import get_garden
from engine.model_selector import ModelSelector
from engine.n_stroke import NStrokeEngine
from engine.parallel_validation import FileChange, ParallelValidationPipeline
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.refinement_supervisor import RefinementSupervisor
from engine.roadmap import RoadmapManager
from engine.router import (
    ConversationalIntentDiscovery,
    LockedIntent,
    MandateRouter,
    compute_buddy_line,
)
from engine.sandbox import SandboxOrchestrator
from engine.scope_evaluator import ScopeEvaluator
from engine.self_improvement import SelfImprovementEngine
from engine.sota_ingestion import SOTAIngestionEngine
from engine.supervisor import TwoStrokeEngine
from engine.tribunal import Engram, Tribunal
from engine.validator_16d import Validator16D
from engine.async_fluid_executor import AsyncFluidExecutor
from engine.jit_designer import JITDesigner, StreamInterceptor, analyze_partial_prompt

# ── Singletons ────────────────────────────────────────────────────────────────
_router = MandateRouter()
_graph = CognitiveGraph()
_bank = PsycheBank()
_tribunal = Tribunal(bank=_bank)
_executor = JITExecutor()
_sorter = TopologicalSorter()
_scope_evaluator = ScopeEvaluator()
_refinement_loop = RefinementLoop()
_buddy_memory = BuddyMemoryStore()
_conversation_engine = ConversationEngine(memory_store=_buddy_memory)
_jit_booster = JITBooster()
_engram_generator = VisualEngramGenerator()
_self_improvement_engine = SelfImprovementEngine(
    booster=_jit_booster, bank=_bank)

# ── Knowledge Banks + SOTA Ingestion ─────────────────────────────────────────
_bank_manager = BankManager()
_sota_ingestion = SOTAIngestionEngine(
    manager=_bank_manager, tribunal=_tribunal)
_mcp_manager = MCPManager()
_model_selector = ModelSelector()
_refinement_supervisor = RefinementSupervisor()
_intent_discovery = ConversationalIntentDiscovery()
_validator_16d = Validator16D()
_async_fluid_executor = AsyncFluidExecutor()
_jit_designer = JITDesigner()
_STATIC = Path(__file__).parent / "static"
_STARTUP_TIME: str = datetime.now(UTC).isoformat()

# ── SSE broadcast queue ───────────────────────────────────────────────────────
_sse_queues: list[asyncio.Queue[str]] = []


def _broadcast(event: dict[str, Any]) -> None:
    data = json.dumps(event)
    for q in list(_sse_queues):
        with suppress(asyncio.QueueFull):
            q.put_nowait(data)


_daemon = BackgroundDaemon(_broadcast)

# ── NotificationBus — register SSE broadcaster so all alerts reach the UI ────
_notification_bus = get_bus()
_notification_bus.register_broadcast(_broadcast)

# Subscribe RefinementSupervisor to CRITICAL bus events so tribunal poison
# flags automatically queue a healing task (agent-to-agent signalling).


def _on_tribunal_critical(event: BusEvent) -> None:
    """Internal subscriber: log CRITICAL Tribunal events to structured output."""
    import logging as _logging
    _logging.getLogger("studio.api.bus").critical(
        "[CRITICAL-BUS] %s | source=%s | payload=%s",
        event.message, event.source, event.payload,
    )


_notification_bus.subscribe("CRITICAL", _on_tribunal_critical)

# ── CognitiveStanceEngine — process-level singleton ─────────────────────────
_stance_engine = get_stance_engine()

# ── CognitiveMap + ParallelValidationPipeline (after _broadcast) ───────────
_cognitive_map = get_cognitive_map()          # builds on first call
_cognitive_map.register_update_callback(_broadcast)  # SSE self_map_update
_deep_introspector = get_deep_introspector()  # deep self-awareness engine
_deep_introspector.register_update_callback(_broadcast)
_parallel_validation = ParallelValidationPipeline(
    broadcast_fn=_broadcast,
    tribunal=_tribunal,
    validator=_validator_16d,
)


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
_n_stroke_engine = NStrokeEngine(
    router=_router,
    booster=_jit_booster,
    tribunal=_tribunal,
    sorter=_sorter,
    executor=_executor,
    scope_evaluator=_scope_evaluator,
    refinement_loop=_refinement_loop,
    mcp_manager=_mcp_manager,
    model_selector=_model_selector,
    refinement_supervisor=_refinement_supervisor,
    broadcast_fn=_broadcast,
    async_fluid_executor=_async_fluid_executor,
)
_branch_executor = BranchExecutor(
    router=_router,
    booster=_jit_booster,
    tribunal=_tribunal,
    sorter=_sorter,
    jit_executor=_executor,
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
_daemon_task: asyncio.Task[None] | None = None
_loop_stats: dict[str, Any] = {
    "active": False,
    "cycles_completed": 0,
    "last_run_at": None,
    "next_run_at": None,
    "interval_seconds": 30,  # DEV MODE: 90→30s for faster iteration
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
        except Exception as exc:
            _broadcast(
                {"type": "auto_loop", "phase": "error", "error": str(exc)})


# ── App ─────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def _lifespan(_: FastAPI):
    _jit_booster.start_background_refresh()

    async def _purge_psychebank_loop() -> None:
        """Hourly background task: evict TTL-expired PsycheBank rules."""
        while True:
            await asyncio.sleep(3600)
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
        _jit_booster.stop_background_refresh()


app = FastAPI(title="TooLoo V2 Governor Dashboard",
              version="2.1.0", lifespan=_lifespan)


# ── Routes ───────────────────────────────────────────────────────────────────

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


@app.get("/studio", response_class=HTMLResponse, include_in_schema=False)
async def serve_studio() -> HTMLResponse:
    """TooLoo AI Creation Studio — chat-to-canvas image generation."""
    html = (_STATIC / "studio_ui.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


# ── Studio Image Generation helpers ─────────────────────────────────────────

_RATIO_TO_DIMS: dict[str, tuple[int, int]] = {
    "1:1":  (1024, 1024),
    "16:9": (1408, 768),
    "9:16": (768, 1408),
    "4:3":  (1024, 768),
    "3:4":  (768, 1024),
}
_IMAGEN_FAST = "imagen-3.0-fast-generate-001"
_IMAGEN_HD   = "imagen-3.0-generate-002"


def _build_imagen_prompt(prompt: str, style: str, enhance: bool) -> str:
    style_suffix = {
        "cinematic":     ", cinematic lighting, anamorphic lens, film grain, dramatic composition",
        "photorealistic": ", photorealistic, DSLR, sharp focus, natural lighting, 8K",
        "anime":         ", anime style, studio ghibli inspired, vibrant colors, cel-shaded",
        "digital art":   ", digital art, trending on artstation, sharp details, concept art quality",
        "concept art":   ", concept art, matte painting, detailed environment design, moody",
    }.get(style.lower(), "")
    base = prompt + style_suffix
    if enhance:
        base += ", masterpiece, best quality, ultra-detailed, professional"
    return base


async def _enhance_prompt_via_gemini(prompt: str, style: str) -> str:
    """Use Gemini text to expand and enrich the user prompt before image gen."""
    try:
        from google import genai as _genai
        from engine.config import GCP_PROJECT_ID, GCP_REGION, GEMINI_API_KEY, _VERTEX_AVAILABLE
        if _VERTEX_AVAILABLE and GCP_PROJECT_ID:
            client = _genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_REGION)
        else:
            client = _genai.Client(api_key=GEMINI_API_KEY)
        system = (
            "You are a professional image prompt engineer. "
            "Expand the user's idea into a vivid, detailed image generation prompt "
            f"in {style} style. Return ONLY the expanded prompt, no commentary. "
            "Max 120 words."
        )
        resp = await client.aio.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt,
            config={"system_instruction": system, "temperature": 0.9},
        )
        enhanced = resp.text.strip()
        return enhanced if len(enhanced) > 20 else prompt
    except Exception:
        return prompt


async def _generate_imagen(
    prompt: str,
    style: str = "cinematic",
    ratio: str = "16:9",
    quality: str = "standard",
    enhance: bool = True,
    seed: int | None = None,
) -> tuple[str | None, str | None]:
    """
    Returns (enhanced_prompt, base64_image_png).
    Raises on hard failure.
    """
    from google import genai as _genai
    from google.genai import types as _gtypes
    from engine.config import GCP_PROJECT_ID, GCP_REGION, GEMINI_API_KEY, _VERTEX_AVAILABLE

    if _VERTEX_AVAILABLE and GCP_PROJECT_ID:
        client = _genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_REGION)
    else:
        client = _genai.Client(api_key=GEMINI_API_KEY)

    model = _IMAGEN_HD if quality == "hd" else _IMAGEN_FAST
    w, h = _RATIO_TO_DIMS.get(ratio, (1024, 1024))

    final_prompt = _build_imagen_prompt(prompt, style, enhance)

    cfg: dict[str, Any] = {
        "number_of_images": 1,
        "output_mime_type": "image/png",
        "aspect_ratio": ratio if ratio in ("1:1", "16:9", "9:16", "4:3", "3:4") else "1:1",
    }
    if seed is not None:
        cfg["seed"] = seed

    response = await client.aio.models.generate_images(
        model=model,
        prompt=final_prompt,
        config=_gtypes.GenerateImagesConfig(**cfg),
    )

    import base64 as _b64
    img = response.generated_images[0]
    raw = img.image.image_bytes
    b64 = _b64.b64encode(raw).decode()
    return final_prompt, b64


class StudioGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=800)
    style: str = Field("cinematic")
    ratio: str = Field("16:9")
    quality: str = Field("standard")
    enhance: bool = Field(True)
    seed: int | None = Field(None)
    session_id: str | None = Field(None)


@app.post("/v2/studio/generate")
async def studio_generate(req: StudioGenerateRequest) -> dict[str, Any]:
    """REST fallback for image generation when WebSocket is unavailable."""
    try:
        enhanced_prompt, b64 = await _generate_imagen(
            prompt=req.prompt,
            style=req.style,
            ratio=req.ratio,
            quality=req.quality,
            enhance=req.enhance,
            seed=req.seed,
        )
        return {
            "image_b64": b64,
            "enhanced_prompt": enhanced_prompt,
            "chat": "Done. Your image is ready on the canvas.",
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.websocket("/ws/studio")
async def studio_ws(websocket: WebSocket) -> None:
    """Real-time chat-to-canvas WebSocket for TooLoo Studio."""
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON payload."})
                continue

            # Validate prompt
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                await websocket.send_json({"type": "error", "content": "Prompt is required."})
                continue

            # Sanitise parameters
            style   = str(payload.get("style",   "cinematic"))[:64]
            ratio   = str(payload.get("ratio",   "16:9"))[:8]
            quality = str(payload.get("quality", "standard"))[:16]
            enhance = bool(payload.get("enhance", True))
            seed    = payload.get("seed")
            if seed is not None:
                try:
                    seed = int(seed)
                except (TypeError, ValueError):
                    seed = None

            # 1. Acknowledge — show thinking state
            await websocket.send_json({
                "type": "thinking",
                "text": "Interpreting your vision…",
            })

            # 2. Optionally enhance the prompt with Gemini
            enhanced_prompt = prompt
            if enhance:
                await websocket.send_json({
                    "type": "thinking",
                    "text": "Enhancing your prompt…",
                })
                enhanced_prompt = await _enhance_prompt_via_gemini(prompt, style)
                await websocket.send_json({
                    "type": "refined_prompt",
                    "enhanced_prompt": enhanced_prompt,
                })

            # 3. Start image generation
            await websocket.send_json({
                "type": "thinking",
                "text": "Generating image…",
            })

            try:
                final_prompt, b64 = await _generate_imagen(
                    prompt=prompt,
                    style=style,
                    ratio=ratio,
                    quality=quality,
                    enhance=enhance,
                    seed=seed,
                )
                await websocket.send_json({
                    "type": "canvas",
                    "image_b64": b64,
                    "enhanced_prompt": final_prompt,
                    "content": "Done — your image is on the canvas. Ask me to refine it anytime.",
                })
            except Exception as exc:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Generation failed: {exc}",
                })

    except WebSocketDisconnect:
        pass
    except Exception:
        with suppress(Exception):
            await websocket.close()


@app.get("/v2/health")
async def health() -> dict[str, Any]:
    mcp_tool_count = len(_mcp_manager.manifest())
    dora = _executor.dora_metrics().to_dict()
    return {
        "status": "ok",
        "version": "2.1.0",
        "components": {
            "router": "up",
            "graph": f"{len(_graph.nodes())} nodes",
            "psyche_bank": f"{len(_bank.all_rules())} rules",
            "tribunal": "up",
            "cognitive_dreamer": "up",
            "executor": "up",
            "jit_booster": "up",
            "engram_engine": "up",
            "self_improvement": "up",
            "supervisor": "up",
            "intent_discovery": "up",
            "mcp_manager": f"{mcp_tool_count} tools",
            "model_selector": "up",
            "refinement_supervisor": "up",
            "n_stroke_engine": "up",
            "branch_executor": "up",
            "model_garden": get_garden().to_status(),
            "validator_16d": "up",
            "async_fluid_executor": "up",
            "buddy_memory": f"{_buddy_memory.entry_count()} entries",
            "recursive_summarizer": "up",
            "cold_memory": "gcp" if ColdMemoryFirestore().enabled else "mock",
            "persistence": "up",
            "semantics": "up",
        },
        "dora": dora,
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
    tribunal_result = _tribunal.evaluate(engram)

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
    tribunal_result = _tribunal.evaluate(engram)

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


# ── Buddy Memory endpoints ────────────────────────────────────────────────────


@app.get("/v2/buddy/memory")
async def get_buddy_memory(limit: int = 10) -> dict[str, Any]:
    """Return the *limit* most recently saved conversation memory entries."""
    limit = max(1, min(limit, 50))
    entries = _buddy_memory.recent(limit=limit)
    return {
        "count": len(entries),
        "total_stored": _buddy_memory.entry_count(),
        "entries": [e.to_dict() for e in entries],
    }


@app.post("/v2/buddy/memory/save/{session_id}")
async def save_buddy_memory(session_id: str) -> dict[str, Any]:
    """Explicitly persist the named in-progress session to BuddyMemoryStore."""
    entry = _conversation_engine.save_session_to_memory(session_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or had fewer than 2 user turns.",
        )
    _broadcast({"type": "buddy_memory_saved", "session_id": session_id})
    return {"saved": True, "session_id": session_id, "entry": entry.to_dict()}


# ── Buddy Cognitive Profile & Cache endpoints ─────────────────────────────────
# Research basis: UserProfile (buddy_cognition.py) tracks expertise, goals, and
# learning style across sessions. BuddyCache (buddy_cache.py) provides 3-layer
# semantic caching to eliminate redundant LLM calls and reduce response latency.


@app.get("/v2/buddy/profile")
async def get_buddy_profile() -> dict[str, Any]:
    """Return the user's persistent cognitive profile.

    Includes expertise score (0.0–1.0), expertise tier label, preferred
    learning style, active cross-session goals, completed goals, and the
    most recent knowledge anchors (effective explanations for this user).
    """
    profile = _conversation_engine.get_user_profile()
    return {
        "profile": profile.to_dict(),
        "expertise_label": profile.expertise_label(),
    }


@app.get("/v2/buddy/goals")
async def get_buddy_goals() -> dict[str, Any]:
    """Return the user's active and completed cross-session goals."""
    profile = _conversation_engine.get_user_profile()
    return {
        "active_goals": profile.active_goals,
        "completed_goals": profile.completed_goals,
        "active_count": len(profile.active_goals),
        "completed_count": len(profile.completed_goals),
    }


@app.post("/v2/buddy/goals/complete")
async def complete_buddy_goal(payload: dict[str, Any]) -> dict[str, Any]:
    """Mark the best-matching active goal as completed.

    Body: {"goal_text": "the goal to complete"}
    Uses substring fuzzy matching — does not need to be an exact string.
    """
    goal_text = str(payload.get("goal_text", "")).strip()
    if not goal_text:
        raise HTTPException(status_code=422, detail="goal_text is required.")
    completed = _conversation_engine.complete_goal(goal_text)
    _broadcast({"type": "buddy_goal_completed",
               "goal": goal_text, "found": completed})
    return {"completed": completed, "goal_text": goal_text}


@app.get("/v2/buddy/cache/stats")
async def get_buddy_cache_stats() -> dict[str, Any]:
    """Return 3-layer cache hit/miss statistics with per-layer descriptions.

    Useful for monitoring latency optimisation from semantic caching.
    Layer 1: in-session Jaccard similarity cache.
    Layer 2: process-scoped exact-fingerprint cache (TTL=1h).
    Layer 3: persistent disk knowledge cache (TTL=24h).
    """
    return _conversation_engine.get_cache_stats()


@app.post("/v2/buddy/cache/invalidate")
async def invalidate_buddy_cache() -> dict[str, Any]:
    """Clear all 3 cache layers. Use for testing or after major content updates."""
    _conversation_engine.invalidate_cache()
    _broadcast({"type": "buddy_cache_invalidated"})
    return {"invalidated": True, "layers_cleared": ["l1_semantic", "l2_process", "l3_persistent"]}


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
    locked_intent = discovery.locked_intent
    if locked_intent is None:
        return {
            "pipeline_id": pipeline_id,
            "session_id": session_id,
            "locked": False,
            "clarification_question": "Intent lock was expected but missing. Please retry.",
            "clarification_type": "intent",
            "intent_hint": discovery.intent_hint,
            "confidence": discovery.confidence,
            "turn_count": discovery.turn_count,
            "result": None,
            "latency_ms": round((time.monotonic() - t0) * 1000, 2),
        }

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: _supervisor.run(
            locked_intent,
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
    locked = LockedIntent(
        intent=req.intent,
        confidence=req.confidence,
        value_statement=req.value_statement,
        constraint_summary=req.constraint_summary,
        mandate_text=req.mandate_text,
        context_turns=[],
        locked_at=datetime.now(UTC).isoformat(),
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
        (f"{mandate_id}-ingest", []),
        (f"{mandate_id}-analyse", [f"{mandate_id}-ingest"]),
        (f"{mandate_id}-implement", [f"{mandate_id}-analyse"]),
        (f"{mandate_id}-validate", [f"{mandate_id}-implement"]),
    ]
    plan = _sorter.sort(spec)
    _broadcast({"type": "plan", "mandate_id": mandate_id, "waves": plan})

    # 4. Action scope evaluation — understand full plan before allocating resources
    scope = _scope_evaluator.evaluate(plan, intent=route.intent)
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

    exec_results = _executor.fan_out_dag(
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
async def buddy_chat(req: ChatRequest) -> dict[str, Any]:
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
    loop = asyncio.get_running_loop()
    report = await loop.run_in_executor(
        None,
        lambda: _self_improvement_engine.run_parallel(broadcast_fn=_broadcast),
    )
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


# ── N-Stroke pipeline endpoints ───────────────────────────────────────────────


class NStrokeRequest(BaseModel):
    """Request body for /v2/n-stroke.

    Requires a pre-confirmed LockedIntent.  To build one via multi-turn
    discovery first, use /v2/intent/clarify then pass the locked_intent here.
    """
    intent: str
    confidence: float
    value_statement: str
    constraint_summary: str = ""
    mandate_text: str
    session_id: str = ""
    max_strokes: int = 7


@app.post("/v2/n-stroke")
async def run_n_stroke(req: NStrokeRequest) -> dict[str, Any]:
    """N-Stroke Autonomous Cognitive Loop.

    Runs the full N-stroke pipeline:
      PreflightSupervisor → Process 1 → MidflightSupervisor →
      Process 2 → Satisfaction Gate → (loop with model escalation if needed)

    Features vs /v2/pipeline:
      - Dynamic model selection (Flash → Pro-Thinking on failures)
      - MCP tool manifest injected into every stroke's execution context
      - RefinementSupervisor autonomous healing on 3+ node failures
      - Loops up to max_strokes (default 7, vs 3 for two-stroke)

    SSE events: n_stroke_start · model_selected · healing_triggered ·
                preflight · plan · midflight · execution ·
                satisfaction_gate · n_stroke_complete
    """
    t0 = time.monotonic()
    pipeline_id = f"ns-{uuid.uuid4().hex[:8]}"
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"

    locked = LockedIntent(
        intent=req.intent,
        confidence=req.confidence,
        value_statement=req.value_statement,
        constraint_summary=req.constraint_summary,
        mandate_text=req.mandate_text,
        context_turns=[],
        locked_at=datetime.now(UTC).isoformat(),
    )

    loop = asyncio.get_event_loop()
    # Honour max_strokes override
    engine = _n_stroke_engine
    if req.max_strokes != 7:
        from engine.n_stroke import NStrokeEngine as _NSE
        engine = _NSE(
            router=_router,
            booster=_jit_booster,
            tribunal=_tribunal,
            sorter=_sorter,
            executor=_executor,
            scope_evaluator=_scope_evaluator,
            refinement_loop=_refinement_loop,
            mcp_manager=_mcp_manager,
            model_selector=_model_selector,
            refinement_supervisor=_refinement_supervisor,
            broadcast_fn=_broadcast,
            max_strokes=req.max_strokes,
            async_fluid_executor=_async_fluid_executor,
        )

    result = await loop.run_in_executor(
        None,
        lambda: engine.run(locked, pipeline_id=pipeline_id),
    )

    return {
        "pipeline_id": pipeline_id,
        "session_id": session_id,
        "result": result.to_dict(),
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
    }


@app.post("/v2/n-stroke/async")
async def run_n_stroke_async(req: NStrokeRequest) -> dict[str, Any]:
    """N-Stroke Autonomous Cognitive Loop — async fluid execution variant.

    Identical to POST /v2/n-stroke but uses AsyncFluidExecutor.fan_out_dag_async()
    for Process 2 execution.  Each DAG node fires the instant its individual
    dependencies resolve, eliminating wave-level stalls.

    Expected latency improvement: 25-40% on DAGs with 6+ nodes and non-trivial
    dependency fan-out structures (diamond shapes, multiple parallel branches).

    Response includes ``"execution_mode": "async_fluid"`` in execution SSE events.
    """
    t0 = time.monotonic()
    pipeline_id = f"ns-async-{uuid.uuid4().hex[:8]}"
    session_id = req.session_id or f"s-{uuid.uuid4().hex[:12]}"

    locked = LockedIntent(
        intent=req.intent,
        confidence=req.confidence,
        value_statement=req.value_statement,
        constraint_summary=req.constraint_summary,
        mandate_text=req.mandate_text,
        context_turns=[],
        locked_at=datetime.now(UTC).isoformat(),
    )

    engine = _n_stroke_engine
    if req.max_strokes != 7:
        from engine.n_stroke import NStrokeEngine as _NSE
        engine = _NSE(
            router=_router,
            booster=_jit_booster,
            tribunal=_tribunal,
            sorter=_sorter,
            executor=_executor,
            scope_evaluator=_scope_evaluator,
            refinement_loop=_refinement_loop,
            mcp_manager=_mcp_manager,
            model_selector=_model_selector,
            refinement_supervisor=_refinement_supervisor,
            broadcast_fn=_broadcast,
            max_strokes=req.max_strokes,
            async_fluid_executor=_async_fluid_executor,
        )

    result = await engine.run_async(locked, pipeline_id=pipeline_id)

    return {
        "pipeline_id": pipeline_id,
        "session_id": session_id,
        "result": result.to_dict(),
        "execution_mode": "async_fluid",
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
    }


@app.get("/v2/n-stroke/benchmark")
async def n_stroke_benchmark() -> dict[str, Any]:
    """Run one sync stroke and one async stroke on a fixed short mandate.

    Returns timing comparison so clients can decide which execution path is
    faster for their deployment.  Both strokes use max_strokes=1 to keep
    the benchmark short.
    """
    import time as _time
    _mandate = "benchmark build create implement generate"
    _locked = LockedIntent(
        intent="BUILD",
        confidence=0.95,
        value_statement=_mandate,
        constraint_summary="benchmark only",
        mandate_text=_mandate,
        context_turns=[],
        locked_at=datetime.now(UTC).isoformat(),
    )

    # --- sync stroke ---
    _engine_sync = NStrokeEngine(
        router=_router,
        booster=_jit_booster,
        tribunal=_tribunal,
        sorter=_sorter,
        executor=_executor,
        scope_evaluator=_scope_evaluator,
        refinement_loop=_refinement_loop,
        mcp_manager=_mcp_manager,
        model_selector=_model_selector,
        refinement_supervisor=_refinement_supervisor,
        broadcast_fn=_broadcast,
        max_strokes=1,
    )
    _t_sync = _time.monotonic()
    _res_sync = _engine_sync.run(_locked, pipeline_id="bench-sync")
    sync_ms = round((_time.monotonic() - _t_sync) * 1000, 2)

    # --- async stroke ---
    _engine_async = NStrokeEngine(
        router=_router,
        booster=_jit_booster,
        tribunal=_tribunal,
        sorter=_sorter,
        executor=_executor,
        scope_evaluator=_scope_evaluator,
        refinement_loop=_refinement_loop,
        mcp_manager=_mcp_manager,
        model_selector=_model_selector,
        refinement_supervisor=_refinement_supervisor,
        broadcast_fn=_broadcast,
        max_strokes=1,
        async_fluid_executor=_async_fluid_executor,
    )
    _t_async = _time.monotonic()
    _res_async = await _engine_async.run_async(_locked, pipeline_id="bench-async")
    async_ms = round((_time.monotonic() - _t_async) * 1000, 2)

    delta_ms = round(sync_ms - async_ms, 2)
    faster = "async_fluid" if async_ms < sync_ms else "sync"
    return {
        "sync_ms": sync_ms,
        "async_ms": async_ms,
        "delta_ms": delta_ms,
        "faster": faster,
        "sync_verdict": _res_sync.final_verdict,
        "async_verdict": _res_async.final_verdict,
    }


@app.get("/v2/mcp/tools")
async def mcp_tool_manifest() -> dict[str, Any]:
    """Return the complete MCP tool manifest.

    Each entry describes one registered tool with its URI, name,
    description, and parameter schema.  The manifest is static for the
    lifetime of the process — tools are registered at import time.
    """
    tools = _mcp_manager.manifest()
    return {
        "tool_count": len(tools),
        "tools": [t.to_dict() for t in tools],
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


# ── Branch Executor endpoints ─────────────────────────────────────────────────

_VALID_BRANCH_TYPES = {BRANCH_FORK, BRANCH_CLONE, BRANCH_SHARE}


class BranchSpecRequest(BaseModel):
    """One branch specification for /v2/branch."""
    branch_id: str = ""
    branch_type: str = BRANCH_FORK
    mandate_text: str
    intent: str = "BUILD"
    target: str = ""
    parent_branch_id: str | None = None
    metadata: dict = {}


class BranchRequest(BaseModel):
    branches: list[BranchSpecRequest]
    timeout: float = 120.0


@app.post("/v2/branch")
async def run_branches(req: BranchRequest) -> dict[str, Any]:
    """Run a set of branched parallel autonomous processes.

    Each branch spec describes an independent (FORK/CLONE) or dependent
    (SHARE) pipeline segment.  All branches execute concurrently; SHARE
    branches wait for their parent to post a result first.

    Branch types:
      - ``fork``  — independent parallel paths from a parent context
      - ``clone`` — identical logic applied to multiple targets
      - ``share`` — waits for parent branch result, inherits context

    SSE events: branch_run_start · branch_spawned · branch_complete ·
                branch_run_complete
    """
    t0 = time.monotonic()

    # Validate and build BranchSpec list (input validation boundary)
    specs: list[BranchSpec] = []
    for i, s in enumerate(req.branches):
        branch_type = s.branch_type.lower() if s.branch_type else BRANCH_FORK
        if branch_type not in _VALID_BRANCH_TYPES:
            return {
                "error": f"Invalid branch_type '{s.branch_type}'. "
                f"Must be one of: {sorted(_VALID_BRANCH_TYPES)}",
                "branch_index": i,
            }
        intent = s.intent.upper() if s.intent else "BUILD"
        specs.append(BranchSpec(
            branch_id=s.branch_id or f"b-{uuid.uuid4().hex[:8]}",
            branch_type=branch_type,
            mandate_text=s.mandate_text,
            intent=intent,
            target=s.target,
            parent_branch_id=s.parent_branch_id,
            metadata=s.metadata,
        ))

    run_result = await _branch_executor.run_branches(specs, timeout=req.timeout)

    _broadcast({"type": "branch_run_complete",
                "run_id": run_result.run_id,
                "satisfied": run_result.satisfied_count,
                "failed": run_result.failed_count})

    return {
        "run_id": run_result.run_id,
        "result": run_result.to_dict(),
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
    }


@app.get("/v2/branches")
async def list_branches() -> dict[str, Any]:
    """Return status snapshot of all known branch processes."""
    branches = _branch_executor.active_branches()
    return {
        "total": len(branches),
        "branches": branches,
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


# ── Knowledge Banks ────────────────────────────────────────────────────────────


@app.get("/v2/knowledge/health")
async def knowledge_health() -> dict[str, Any]:
    """Return health summary for all knowledge banks."""
    return _bank_manager.health()


@app.get("/v2/knowledge/dashboard")
async def knowledge_dashboard() -> dict[str, Any]:
    """Full dashboard dict for the Knowledge Banks UI panel."""
    return _bank_manager.dashboard()


@app.get("/v2/knowledge/{bank_id}")
async def get_knowledge_bank(bank_id: str) -> dict[str, Any]:
    """Return all entries for a specific bank (design/code/ai/bridge)."""
    bank = _bank_manager.get_bank(bank_id)
    if bank is None:
        return {"error": f"Unknown bank: {bank_id}", "valid_ids": list(_bank_manager.all_banks())}
    return {
        "bank_id": bank_id,
        "bank_name": bank.bank_name,
        "domains": bank.domains,
        "entries": [e.to_dict() for e in bank.all_entries()],
    }


@app.get("/v2/knowledge/{bank_id}/signals")
async def get_bank_signals(bank_id: str, domain: str = "", n: int = 5) -> dict[str, Any]:
    """Return top-N signal strings from a bank, optionally filtered by domain."""
    bank = _bank_manager.get_bank(bank_id)
    if bank is None:
        return {"error": f"Unknown bank: {bank_id}"}
    return {"bank_id": bank_id, "domain": domain, "signals": bank.get_signals(domain, n)}


class KnowledgeQueryRequest(BaseModel):
    topic: str
    context: str = ""
    n_per_bank: int = 3


@app.post("/v2/knowledge/query")
async def query_knowledge(req: KnowledgeQueryRequest) -> dict[str, Any]:
    """Cross-bank semantic query — returns top entries across all banks."""
    results = _bank_manager.query_all(req.topic, req.context, req.n_per_bank)
    return {
        "topic": req.topic,
        "results": [e.to_dict() for e in results],
        "count": len(results),
    }


class KnowledgeIngestRequest(BaseModel):
    bank_id: str
    domain: str
    signals: list[str]


@app.post("/v2/knowledge/ingest")
async def ingest_knowledge(req: KnowledgeIngestRequest) -> dict[str, Any]:
    """Manually ingest a list of signal strings into a specific bank/domain."""
    try:
        report = _sota_ingestion.ingest_single(
            req.bank_id, req.domain, req.signals)
        _broadcast({"type": "knowledge_ingested", "report": report.to_dict()})
        return report.to_dict()
    except ValueError as exc:
        return {"error": str(exc)}


@app.post("/v2/knowledge/ingest/full")
async def run_full_sota_ingestion() -> dict[str, Any]:
    """Trigger a full SOTA ingestion run across all banks and domains.

    This enriches all knowledge banks with the latest signals from Gemini
    (or the structured SOTA catalogue when offline). May take 15-30 s when
    Gemini is available; ~1 s in offline/structured mode.
    """
    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, _sota_ingestion.run_full_ingestion)
    _broadcast({"type": "sota_ingestion_complete", "report": report.to_dict()})
    return report.to_dict()


@app.get("/v2/knowledge/intent/{intent}/signals")
async def get_intent_signals(intent: str, n: int = 5) -> dict[str, Any]:
    """Return the top SOTA signals for a given routing intent, from knowledge banks."""
    signals = _bank_manager.signals_for_intent(intent.upper(), n)
    return {"intent": intent.upper(), "signals": signals, "count": len(signals)}


# ── VLT (Vector Layout Tree) endpoints ───────────────────────────────────────────────

from engine.vlt_schema import VectorTree, VLTAuditReport, demo_vlt  # noqa: E402


@app.get("/v2/vlt/demo")
async def vlt_demo() -> dict[str, Any]:
    """Return the production-quality demo VLT + its full math audit report.

    Used by the Spatial Engine canvas “Load Demo VLT” button.
    The tree encodes the TooLoo Studio layout using pure numeric constraints;
    the audit proves zero violations before the browser ever paints a pixel.
    """
    tree = demo_vlt()
    audit: VLTAuditReport = tree.full_audit()
    _broadcast({"type": "vlt_rendered", "tree_id": tree.tree_id,
                "verdict": audit.verdict, "violations": audit.total_violations})
    return {
        "tree":  tree.model_dump(),
        "audit": audit.model_dump(),
    }


@app.post("/v2/vlt/audit")
async def vlt_audit(req: dict[str, Any]) -> dict[str, Any]:
    """Run all three math proofs (collision / overflow / WCAG) on a submitted VLT.

    Accepts a raw VectorTree JSON body (not wrapped).  Returns VLTAuditReport.
    Security: validated through Pydantic model — no raw dict passed to eval/exec.
    """
    if "tree" not in req and "tree_id" not in req:
        raise HTTPException(
            status_code=422, detail="Missing required field: 'tree'")
    try:
        tree = VectorTree.model_validate(req.get("tree", req))
    except Exception as exc:
        return {"error": f"Invalid VLT payload: {exc}"}
    audit: VLTAuditReport = tree.full_audit()
    _broadcast({"type": "vlt_audit_complete", "tree_id": tree.tree_id,
                "verdict": audit.verdict, "violations": audit.total_violations})
    return audit.model_dump()


@app.post("/v2/vlt/render")
async def vlt_render(req: dict[str, Any]) -> dict[str, Any]:
    """Validate a VLT, run audit, broadcast via SSE so all connected clients
    automatically update their Spatial Canvas in real-time.

    Returns the audit report.  The SSE ''vlt_push'' event carries the full tree
    so the JS renderVectorTree() engine can tween coordinates client-side.
    """
    try:
        tree = VectorTree.model_validate(req)
    except Exception as exc:
        return {"error": f"Invalid VLT payload: {exc}"}
    audit: VLTAuditReport = tree.full_audit()
    _broadcast({
        "type":       "vlt_push",
        "tree":        tree.model_dump(),
        "audit":       audit.model_dump(),
        "verdict":     audit.verdict,
        "violations":  audit.total_violations,
    })
    return {
        "tree_id":    tree.tree_id,
        "audit":      audit.model_dump(),
        "broadcast":  True,
    }


class VLTPatchRequest(BaseModel):
    """Differential VLT patch — updates a subset of nodes without full reload.

    Each entry in ``patches`` is a dict with ``node_id`` and any properties to
    override (material, sensor_bindings, coordinates, style_tokens).  The SSE
    ``vlt_patch`` event is streamed immediately so the frontend can tween only
    the changed nodes without interrupting the current animation state.
    """
    tree_id: str = ""
    patches: list[dict[str, Any]]
    transition_ms: int = Field(
        400, ge=0, le=5000,
        description="Frontend GSAP tween duration for this patch (milliseconds)")


@app.post("/v2/vlt/patch")
async def vlt_patch(req: VLTPatchRequest) -> dict[str, Any]:
    """Stream a differential VLT patch for live-wire real-time UI evolution.

    Used by Buddy's Ghost Manifestation loop: material or sensor-binding changes
    are extracted from LLM output and broadcast immediately so the 3D canvas
    morphs *while* the text response is still streaming.

    Security: node_id values validated as non-empty strings; no eval/exec.
    """
    validated_patches = []
    for p in req.patches:
        node_id = p.get("node_id", "")
        if not node_id or not isinstance(node_id, str):
            continue
        if "material" in p:
            from engine.vlt_schema import MaterialProps
            try:
                MaterialProps.model_validate(p["material"])
            except Exception:
                p.pop("material")
        validated_patches.append(p)

    _broadcast({
        "type":          "vlt_patch",
        "tree_id":       req.tree_id,
        "patches":       validated_patches,
        "transition_ms": req.transition_ms,
    })
    return {
        "tree_id":         req.tree_id,
        "patches_applied": len(validated_patches),
        "broadcast":       True,
    }


# ── Cognitive Self-Map endpoints ──────────────────────────────────────────────

@app.get("/v2/cognitive-map")
async def cognitive_map_snapshot() -> dict[str, Any]:
    """Return a live snapshot of the CognitiveMap DAG (nodes, edges, summary)."""
    return _cognitive_map.to_dict()


@app.get("/v2/cognitive-map/mermaid")
async def cognitive_map_mermaid() -> dict[str, Any]:
    """Return the live Mermaid diagram of engine component dependencies."""
    return {
        "mermaid": _cognitive_map.to_mermaid(),
        "node_count": _cognitive_map.node_count(),
    }


@app.get("/v2/cognitive-map/context/{intent}")
async def cognitive_map_context(intent: str, mandate: str = "") -> dict[str, Any]:
    """Zero-shot workspace blueprint for a given intent."""
    safe_intent = intent.upper()[:64]
    safe_mandate = mandate[:512]
    blueprint = _cognitive_map.relevant_context(safe_intent, safe_mandate)
    nodes = [n.to_dict() for n in _cognitive_map.query_nodes(safe_intent)]
    return {"intent": safe_intent, "blueprint": blueprint, "nodes": nodes}


@app.post("/v2/cognitive-map/rebuild")
async def cognitive_map_rebuild() -> dict[str, Any]:
    """Force a full workspace rescan and rebuild the CognitiveMap."""
    await asyncio.to_thread(_cognitive_map.rebuild)
    _broadcast({
        "type": "self_map_update",
        "source": "manual_rebuild",
        "node_count": _cognitive_map.node_count(),
    })
    return {"node_count": _cognitive_map.node_count(), "rebuilt": True}


# ── Deep Introspection endpoints ──────────────────────────────────────────────


@app.get("/v2/introspector")
async def introspector_snapshot() -> dict[str, Any]:
    """Full deep introspection snapshot: system health + all module health."""
    return await asyncio.to_thread(_deep_introspector.to_dict)


@app.get("/v2/introspector/health")
async def introspector_system_health() -> dict[str, Any]:
    """Break-glass system health dashboard (traffic-light status)."""
    report = await asyncio.to_thread(_deep_introspector.system_health)
    return report.to_dict()


@app.get("/v2/introspector/module/{module_name}")
async def introspector_module_health(module_name: str) -> dict[str, Any]:
    """Per-module health deep dive."""
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "", module_name)[:64]
    health = _deep_introspector.module_health(safe_name)
    if health is None:
        return {"error": f"Module '{safe_name}' not found", "modules": [
            h.module_name for h in _deep_introspector.all_module_health()
        ]}
    return health.to_dict()


@app.get("/v2/introspector/cross-refs")
async def introspector_all_cross_refs() -> dict[str, Any]:
    """All function-level cross-references grouped by target module."""
    refs = await asyncio.to_thread(_deep_introspector.all_cross_refs)
    total = sum(len(v) for v in refs.values())
    return {"total_refs": total, "by_module": refs}


@app.get("/v2/introspector/cross-refs/{module_name}")
async def introspector_module_cross_refs(module_name: str) -> dict[str, Any]:
    """Cross-references targeting a specific module's functions."""
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "", module_name)[:64]
    refs = _deep_introspector.cross_refs(safe_name)
    return {
        "module": safe_name,
        "ref_count": len(refs),
        "refs": [r.to_dict() for r in refs],
    }


@app.get("/v2/introspector/dead-code")
async def introspector_dead_code() -> dict[str, Any]:
    """Public functions never referenced by other modules."""
    dead = await asyncio.to_thread(_deep_introspector.dead_functions)
    return {"dead_function_count": len(dead), "functions": dead}


@app.get("/v2/introspector/knowledge-graph")
async def introspector_knowledge_graph() -> dict[str, Any]:
    """Semantic knowledge graph: module roles, layers, criticality."""
    return await asyncio.to_thread(_deep_introspector.knowledge_graph)


@app.get("/v2/introspector/cascade/{file_path:path}")
async def introspector_cascade(file_path: str) -> dict[str, Any]:
    """Predictive cascade analysis: failure risk if a file is modified."""
    safe_path = file_path.replace("..", "").strip("/")[:256]
    return await asyncio.to_thread(
        _deep_introspector.cascade_analysis, safe_path
    )


@app.post("/v2/introspector/rebuild")
async def introspector_rebuild() -> dict[str, Any]:
    """Force a full deep introspection rebuild."""
    await asyncio.to_thread(_deep_introspector.rebuild)
    report = _deep_introspector.system_health()
    _broadcast({
        "type": "deep_introspection_update",
        "source": "manual_rebuild",
        "status": report.status,
        "module_count": report.module_count,
    })
    return {
        "rebuilt": True,
        "status": report.status,
        "module_count": report.module_count,
        "avg_health": round(report.avg_health, 3),
    }


# ── Parallel Validation endpoint ──────────────────────────────────────────────

class ParallelValidateRequest(BaseModel):
    """Batch of file changes to validate concurrently (Tribunal + 16D + tests)."""
    files: list[dict[str, Any]]
    run_tests: bool = True


@app.post("/v2/validate")
async def parallel_validate(req: ParallelValidateRequest) -> dict[str, Any]:
    """Fan-out Tribunal + 16D + tests concurrently for a batch of file changes.

    Security: path values are validated inside ParallelValidationPipeline
    (path-traversal guard). No eval/exec.
    """
    changes = [
        FileChange(
            path=f.get("path", ""),
            content=f.get("content"),
            component=f.get("component", ""),
        )
        for f in req.files
        if isinstance(f.get("path"), str) and f["path"]
    ]
    if not changes:
        raise HTTPException(
            status_code=422, detail="No valid file paths provided")
    report = await _parallel_validation.validate_changes(
        changes, run_tests=req.run_tests
    )
    return report.to_dict()


# ── NotificationBus endpoints ─────────────────────────────────────────────────

@app.get("/v2/alerts")
async def alerts_list(
    level: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Return recent alert history from the NotificationBus.

    Query params:
        level  — filter by INFO | INSIGHT | WARNING | CRITICAL (optional)
        limit  — max events to return (default 50)
    """
    safe_limit = max(1, min(limit, 200))
    safe_level = level.upper() if level else None
    events = _notification_bus.history(level=safe_level, limit=safe_limit)
    return {
        "events": [e.to_dict() for e in events],
        "stats": _notification_bus.stats(),
    }


@app.get("/v2/alerts/pending")
async def alerts_pending() -> dict[str, Any]:
    """Return all events that are awaiting user confirmation."""
    return {
        "pending": [e.to_dict() for e in _notification_bus.pending()],
    }


@app.post("/v2/alerts/confirm/{event_id}")
async def alerts_confirm(event_id: str, accepted: bool = True) -> dict[str, Any]:
    """Confirm or dismiss a bus event that requires human acknowledgement.

    SSE: broadcasts a ``bus_confirm_response`` event with the result.
    """
    result = _notification_bus.confirm(event_id, accepted=accepted)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pending event '{event_id}' not found (already confirmed or expired)",
        )
    return result.to_dict()


@app.post("/v2/alerts/dismiss/{event_id}")
async def alerts_dismiss(event_id: str) -> dict[str, Any]:
    """Silently remove a pending confirmation event without triggering on_confirm."""
    removed = _notification_bus.dismiss(event_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Pending event '{event_id}' not found",
        )
    return {"event_id": event_id, "dismissed": True}


@app.post("/v2/alerts/publish")
async def alerts_publish(req: dict[str, Any]) -> dict[str, Any]:
    """Manually publish a bus event (for testing or external system integration).

    Security: level is constrained to the allowed set; message is plain text only.
    """
    level = str(req.get("level", "INFO")).upper()
    if level not in ("INFO", "INSIGHT", "WARNING", "CRITICAL"):
        level = "INFO"
    message = str(req.get("message", ""))[:500]
    source = str(req.get("source", "api"))[:64]
    payload = req.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}
    requires_confirmation = bool(req.get("requires_confirmation", False))

    event = BusEvent(
        level=level,
        source=source,
        message=message,
        payload=payload,
        requires_confirmation=requires_confirmation,
    )
    _notification_bus.publish(event)
    return {"published": True, "event_id": event.event_id, "level": event.level}


# ── Cognitive Stance endpoints ────────────────────────────────────────────────

@app.get("/v2/stance")
async def stance_get() -> dict[str, Any]:
    """Return the currently active Cognitive Stance."""
    return get_active_stance().to_dict()


class StanceOverrideRequest(BaseModel):
    # IDEATION | DEEP_EXECUTION | SURGICAL_REPAIR | MAINTENANCE
    stance: str
    mandate_text: str = ""            # optional — used for confidence estimation


@app.post("/v2/stance")
async def stance_set(req: StanceOverrideRequest) -> dict[str, Any]:
    """Override the active Cognitive Stance for current session.

    This immediately propagates to the 16D Validator, ConversationEngine persona,
    and the next NStroke execution preflight.  Broadcasting a ``stance_detected``
    SSE event so the UI can reflect the change.
    """
    stance_upper = req.stance.upper()
    try:
        stance_enum = Stance(stance_upper)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stance '{req.stance}'. "
            f"Valid values: {[s.value for s in Stance if s != Stance.UNKNOWN]}",
        )

    if req.mandate_text:
        result = _stance_engine.detect(
            mandate_text=req.mandate_text,
            recent_intents=[stance_upper],
        )
    else:
        from engine.stance import (
            # type: ignore[attr-defined]
            _STANCE_WEIGHTS, _STANCE_BUDDY_PERSONA, StanceResult
        )
        result = StanceResult(
            stance=stance_enum,
            confidence=1.0,
            explanation=f"Manually set via POST /v2/stance",
            dimension_weights=_STANCE_WEIGHTS[stance_enum],
            buddy_persona=_STANCE_BUDDY_PERSONA[stance_enum],
        )
        set_active_stance(result)

    _broadcast({
        "type": "stance_detected",
        "stance": result.stance.value,
        "confidence": round(result.confidence, 3),
        "explanation": result.explanation,
        "source": "manual_override",
    })
    return result.to_dict()


@app.post("/v2/stance/detect")
async def stance_detect(req: dict[str, Any]) -> dict[str, Any]:
    """Run automatic stance detection from mandate text + intent history.

    Body: { "mandate_text": "...", "recent_intents": ["BUILD", "DEBUG"] }
    """
    mandate_text = str(req.get("mandate_text", ""))[:512]
    recent_intents = [str(i) for i in req.get("recent_intents", [])][:10]
    result = _stance_engine.detect(
        mandate_text=mandate_text,
        recent_intents=recent_intents,
    )
    _broadcast({
        "type": "stance_detected",
        "stance": result.stance.value,
        "confidence": round(result.confidence, 3),
        "explanation": result.explanation,
    })
    return result.to_dict()


@app.post("/v2/memory/distill")
async def distill_hot_memory() -> dict[str, Any]:
    """Trigger the Recursive Summary Agent to distill Hot Memory → Warm Memory → Cold Memory.

    Reads non-distilled BuddyMemoryStore entries in batches, extracts long-term
    'pure facts' via a Tier-3 LLM, stores them in PsycheBank (Warm Memory) and
    GCP Firestore (Cold Memory), then marks the source entries as distilled.

    SSE event: ``memory_distill`` with status, processed count, and facts extracted.
    Useful to call periodically (hourly) or after intensive sessions.
    """
    import time as _time
    t0 = _time.monotonic()
    agent = RecursiveSummaryAgent()
    result = agent.distill_pending()
    latency_ms = round((_time.monotonic() - t0) * 1000, 2)
    _broadcast({
        "type": "memory_distill",
        "status": result.get("status"),
        "processed": result.get("processed", 0),
        "facts_extracted": result.get("facts_extracted", 0),
        "latency_ms": latency_ms,
    })
    return {**result, "latency_ms": latency_ms}


@app.get("/v2/memory/cold")
async def query_cold_memory(limit: int = 50) -> dict[str, Any]:
    """Query Cold Memory (GCP Firestore) for stored pure facts.

    Returns facts distilled from previous Hot Memory sessions.  In offline
    mode (no GCP credentials), returns from the in-process mock store.
    """
    limit = max(1, min(limit, 200))
    store = ColdMemoryFirestore()
    facts = store.query_facts(limit=limit)
    return {
        "source": "firestore" if store.enabled else "mock",
        "count": len(facts),
        "facts": facts,
    }
