"""
studio/routes/introspection.py — Cognitive Map + Deep Introspector endpoints.

Extracted from studio/api.py to reduce monolith size.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any

from fastapi import APIRouter

from engine.cognitive_map import get_cognitive_map
from engine.deep_introspector import get_deep_introspector

router = APIRouter(tags=["introspection"])

# These singletons are the same instances used by the main api module.
# They are module-level singletons via get_* factory functions.
_cognitive_map = get_cognitive_map()
_deep_introspector = get_deep_introspector()

# _broadcast will be set by api.py after import
_broadcast_fn = lambda _: None  # noqa: E731


def set_broadcast(fn):
    """Called by api.py to inject the SSE broadcast function."""
    global _broadcast_fn
    _broadcast_fn = fn


# ── Cognitive Map endpoints ──────────────────────────────────────────────────


@router.get("/v2/cognitive-map")
async def cognitive_map_snapshot() -> dict[str, Any]:
    """Return a live snapshot of the CognitiveMap DAG (nodes, edges, summary)."""
    return _cognitive_map.to_dict()


@router.get("/v2/cognitive-map/mermaid")
async def cognitive_map_mermaid() -> dict[str, Any]:
    """Return the live Mermaid diagram of engine component dependencies."""
    return {
        "mermaid": _cognitive_map.to_mermaid(),
        "node_count": _cognitive_map.node_count(),
    }


@router.get("/v2/cognitive-map/context/{intent}")
async def cognitive_map_context(intent: str, mandate: str = "") -> dict[str, Any]:
    """Zero-shot workspace blueprint for a given intent."""
    safe_intent = intent.upper()[:64]
    safe_mandate = mandate[:512]
    blueprint = _cognitive_map.relevant_context(safe_intent, safe_mandate)
    nodes = [n.to_dict() for n in _cognitive_map.query_nodes(safe_intent)]
    return {"intent": safe_intent, "blueprint": blueprint, "nodes": nodes}


@router.post("/v2/cognitive-map/rebuild")
async def cognitive_map_rebuild() -> dict[str, Any]:
    """Force a full workspace rescan and rebuild the CognitiveMap."""
    await asyncio.to_thread(_cognitive_map.rebuild)
    _broadcast_fn({
        "type": "self_map_update",
        "source": "manual_rebuild",
        "node_count": _cognitive_map.node_count(),
    })
    return {"node_count": _cognitive_map.node_count(), "rebuilt": True}


# ── Deep Introspection endpoints ──────────────────────────────────────────────


@router.get("/v2/introspector")
async def introspector_snapshot() -> dict[str, Any]:
    """Full deep introspection snapshot: system health + all module health."""
    return await asyncio.to_thread(_deep_introspector.to_dict)


@router.get("/v2/introspector/health")
async def introspector_system_health() -> dict[str, Any]:
    """Break-glass system health dashboard (traffic-light status)."""
    report = await asyncio.to_thread(_deep_introspector.system_health)
    return report.to_dict()


@router.get("/v2/introspector/module/{module_name}")
async def introspector_module_health(module_name: str) -> dict[str, Any]:
    """Per-module health deep dive."""
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "", module_name)[:64]
    health = _deep_introspector.module_health(safe_name)
    if health is None:
        return {"error": f"Module '{safe_name}' not found", "modules": [
            h.module_name for h in _deep_introspector.all_module_health()
        ]}
    return health.to_dict()


@router.get("/v2/introspector/cross-refs")
async def introspector_all_cross_refs() -> dict[str, Any]:
    """All function-level cross-references grouped by target module."""
    refs = await asyncio.to_thread(_deep_introspector.all_cross_refs)
    total = sum(len(v) for v in refs.values())
    return {"total_refs": total, "by_module": refs}


@router.get("/v2/introspector/cross-refs/{module_name}")
async def introspector_module_cross_refs(module_name: str) -> dict[str, Any]:
    """Cross-references targeting a specific module's functions."""
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "", module_name)[:64]
    refs = _deep_introspector.cross_refs(safe_name)
    return {
        "module": safe_name,
        "ref_count": len(refs),
        "refs": [r.to_dict() for r in refs],
    }


@router.get("/v2/introspector/dead-code")
async def introspector_dead_code() -> dict[str, Any]:
    """Public functions never referenced by other modules."""
    dead = await asyncio.to_thread(_deep_introspector.dead_functions)
    return {"dead_function_count": len(dead), "functions": dead}


@router.get("/v2/introspector/knowledge-graph")
async def introspector_knowledge_graph() -> dict[str, Any]:
    """Semantic knowledge graph: module roles, layers, criticality."""
    return await asyncio.to_thread(_deep_introspector.knowledge_graph)


@router.get("/v2/introspector/cascade/{file_path:path}")
async def introspector_cascade(file_path: str) -> dict[str, Any]:
    """Predictive cascade analysis: failure risk if a file is modified."""
    safe_path = file_path.replace("..", "").strip("/")[:256]
    return await asyncio.to_thread(
        _deep_introspector.cascade_analysis, safe_path
    )


@router.post("/v2/introspector/rebuild")
async def introspector_rebuild() -> dict[str, Any]:
    """Force a full deep introspection rebuild."""
    await asyncio.to_thread(_deep_introspector.rebuild)
    report = _deep_introspector.system_health()
    _broadcast_fn({
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
