"""
studio/routes/pipeline.py — Execution Pipeline endpoints.

Extracted from studio/api.py to reduce monolith size.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from engine.router import LockedIntent
from engine.branch_executor import BranchSpec, BRANCH_FORK, BRANCH_CLONE, BRANCH_SHARE
from engine.pipeline import NStrokeEngine

router = APIRouter(tags=["pipeline"])

# Singletons set by api.py
_intent_discovery = None
_supervisor = None
_n_stroke_engine = None
_async_fluid_executor = None
_branch_executor = None
_mcp_manager = None
_broadcast_fn = lambda _: None  # noqa: E731
_create_n_stroke_fn = None


def init(
    *,
    intent_discovery,
    supervisor,
    n_stroke_engine,
    async_fluid_executor,
    branch_executor,
    mcp_manager,
    broadcast_fn,
    create_n_stroke_fn,
):
    """Called by api.py to inject singletons."""
    global _intent_discovery, _supervisor, _n_stroke_engine, _async_fluid_executor
    global _branch_executor, _mcp_manager, _broadcast_fn, _create_n_stroke_fn
    _intent_discovery = intent_discovery
    _supervisor = supervisor
    _n_stroke_engine = n_stroke_engine
    _async_fluid_executor = async_fluid_executor
    _branch_executor = branch_executor
    _mcp_manager = mcp_manager
    _broadcast_fn = broadcast_fn
    _create_n_stroke_fn = create_n_stroke_fn


class PipelineRequest(BaseModel):
    text: str
    session_id: str | None = None
    max_iterations: int = 3


class LockedIntentRequest(BaseModel):
    intent: str
    confidence: float
    value_statement: str
    constraint_summary: str = ""
    mandate_text: str
    session_id: str = ""
    max_iterations: int = 3


class NStrokeRequest(BaseModel):
    """Request body for /v2/n-stroke."""
    intent: str
    confidence: float
    value_statement: str
    constraint_summary: str = ""
    mandate_text: str
    session_id: str = ""
    max_strokes: int = 7


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


# ── Two-Stroke Pipeline endpoint ──────────────────────────────────────────────

@router.post("/v2/pipeline")
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

    _broadcast_fn({
        "type": "intent_clarification" if not discovery.locked else "intent_locked",
        "session_id": session_id,
        "pipeline_id": pipeline_id,
        "result": discovery.to_dict(),
    })

    if not discovery.locked:
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
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
    }


@router.post("/v2/pipeline/direct")
async def run_pipeline_direct(req: LockedIntentRequest) -> dict[str, Any]:
    """Run the Two-Stroke Engine with a pre-confirmed LockedIntent."""
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


# ── N-Stroke pipeline endpoints ───────────────────────────────────────────────

@router.post("/v2/n-stroke")
async def run_n_stroke(req: NStrokeRequest) -> dict[str, Any]:
    """N-Stroke Autonomous Cognitive Loop."""
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
    engine = _n_stroke_engine
    if req.max_strokes != 7:
        engine = _create_n_stroke_fn(req.max_strokes)

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


@router.post("/v2/n-stroke/async")
async def run_n_stroke_async(req: NStrokeRequest) -> dict[str, Any]:
    """N-Stroke Autonomous Cognitive Loop — async fluid execution variant."""
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
        engine = _create_n_stroke_fn(req.max_strokes)

    result = await engine.run_async(locked, pipeline_id=pipeline_id)

    return {
        "pipeline_id": pipeline_id,
        "session_id": session_id,
        "result": result.to_dict(),
        "execution_mode": "async_fluid",
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
    }


@router.get("/v2/n-stroke/benchmark")
async def n_stroke_benchmark() -> dict[str, Any]:
    """Run one sync stroke and one async stroke on a fixed short mandate."""
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
    _engine_sync = _create_n_stroke_fn(1)
    _t_sync = _time.monotonic()
    _res_sync = _engine_sync.run(_locked, pipeline_id="bench-sync")
    sync_ms = round((_time.monotonic() - _t_sync) * 1000, 2)

    # --- async stroke ---
    _engine_async = _create_n_stroke_fn(1)
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


@router.get("/v2/mcp/tools")
async def mcp_tool_manifest() -> dict[str, Any]:
    """Return the complete MCP tool manifest."""
    tools = _mcp_manager.manifest()
    return {
        "tool_count": len(tools),
        "tools": [t.to_dict() for t in tools],
    }


# ── Branch Executor endpoints ─────────────────────────────────────────────────

_VALID_BRANCH_TYPES = {BRANCH_FORK, BRANCH_CLONE, BRANCH_SHARE}

@router.post("/v2/branch")
async def run_branches(req: BranchRequest) -> dict[str, Any]:
    """Run a set of branched parallel autonomous processes."""
    t0 = time.monotonic()

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

    _broadcast_fn({"type": "branch_run_complete",
                "run_id": run_result.run_id,
                "satisfied": run_result.satisfied_count,
                "failed": run_result.failed_count})

    return {
        "run_id": run_result.run_id,
        "result": run_result.to_dict(),
        "latency_ms": round((time.monotonic() - t0) * 1000, 2),
    }


@router.get("/v2/branches")
async def list_branches() -> dict[str, Any]:
    """Return status snapshot of all known branch processes."""
    branches = _branch_executor.active_branches()
    return {
        "total": len(branches),
        "branches": branches,
    }
