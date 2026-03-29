"""
studio/routes/sandbox.py — Sandbox and Roadmap management endpoints.

Extracted from studio/api.py to reduce monolith size.
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel


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


router = APIRouter(tags=["sandbox"])


# Singletons set by api.py
_sandbox_orchestrator = None
_roadmap = None
_broadcast_fn = lambda _: None  # noqa: E731


def init(*, sandbox_orchestrator, roadmap, broadcast_fn):
    """Called by api.py to inject singletons."""
    global _sandbox_orchestrator, _roadmap, _broadcast_fn
    _sandbox_orchestrator = sandbox_orchestrator
    _roadmap = roadmap
    _broadcast_fn = broadcast_fn


# ── Sandbox endpoints ────────────────────────────────────────────────────────

@router.post("/v2/sandbox/spawn")
async def spawn_sandbox(req: SandboxSpawnRequest) -> dict[str, Any]:
    """Spawn one isolated sandbox for a single feature mandate."""
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


@router.get("/v2/sandbox")
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


@router.get("/v2/sandbox/{sandbox_id}")
async def get_sandbox(sandbox_id: str) -> dict[str, Any]:
    """Get one sandbox report by ID."""
    report = _sandbox_orchestrator.get_report(sandbox_id)
    if report is None:
        return {"error": "sandbox not found", "sandbox_id": sandbox_id}
    return report.to_dict()


# ── Roadmap endpoints ─────────────────────────────────────────────────────────

@router.get("/v2/roadmap")
async def get_roadmap() -> dict[str, Any]:
    """Return full roadmap report: items, wave plan, status/priority distribution."""
    return _roadmap.get_report().to_dict()


@router.post("/v2/roadmap/item")
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


@router.post("/v2/roadmap/run")
async def run_roadmap_sandboxes() -> dict[str, Any]:
    """Run ALL roadmap items as parallel sandboxes."""
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
    for r in reports:
        if r.roadmap_item_id:
            _roadmap.update_item_scores(
                item_id=r.roadmap_item_id,
                impact_score=r.impact_score,
                difficulty_score=r.difficulty_score,
                readiness_score=r.readiness_score,
                timeline_days=r.timeline_days,
                status=r.state if r.state in ("proven", "failed", "blocked") else "sandbox",
                sandbox_id=r.sandbox_id,
                notes=r.recommendations[:2] if r.recommendations else [],
            )
    _broadcast_fn({"type": "roadmap_run", "reports": [r.to_dict() for r in reports]})
    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "total": len(reports),
        "proven": sum(1 for r in reports if r.state == "proven"),
        "failed": sum(1 for r in reports if r.state == "failed"),
        "blocked": sum(1 for r in reports if r.state == "blocked"),
        "reports": [r.to_dict() for r in reports],
        "latency_ms": latency_ms,
    }


@router.get("/v2/roadmap/similar")
async def roadmap_similar(q: str = "", top_k: int = 3) -> dict[str, Any]:
    """Find roadmap items semantically similar to a query string."""
    if not q:
        return {"results": []}
    return {"query": q, "results": _roadmap.find_similar(q, top_k=top_k)}


@router.post("/v2/roadmap/{item_id}/promote")
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
    _broadcast_fn({"type": "roadmap_promote", "item_id": item_id, "title": item.title})
    return {"promoted": True, "item_id": item_id, "title": item.title}
