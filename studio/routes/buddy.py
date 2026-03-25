"""
studio/routes/buddy.py — Buddy memory and profile endpoints.

Extracted from studio/api.py to reduce monolith size.
Only the lightest, most self-contained buddy endpoints are here.
The heavy chat endpoints remain in api.py for now.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from engine.buddy_memory import BuddyMemoryStore

router = APIRouter(tags=["buddy"])

# Singletons set by api.py
_buddy_memory: BuddyMemoryStore | None = None
_conversation_engine = None
_broadcast_fn = lambda _: None  # noqa: E731


def init(*, buddy_memory, conversation_engine, broadcast_fn):
    """Called by api.py to inject singletons."""
    global _buddy_memory, _conversation_engine, _broadcast_fn
    _buddy_memory = buddy_memory
    _conversation_engine = conversation_engine
    _broadcast_fn = broadcast_fn


@router.get("/v2/buddy/memory")
async def get_buddy_memory(limit: int = 10) -> dict[str, Any]:
    """Return the *limit* most recently saved conversation memory entries."""
    limit = max(1, min(limit, 50))
    entries = _buddy_memory.recent(limit=limit)
    return {
        "count": len(entries),
        "total_stored": _buddy_memory.entry_count(),
        "entries": [e.to_dict() for e in entries],
    }


@router.post("/v2/buddy/memory/save/{session_id}")
async def save_buddy_memory(session_id: str) -> dict[str, Any]:
    """Explicitly persist the named in-progress session to BuddyMemoryStore."""
    entry = _conversation_engine.save_session_to_memory(session_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or had fewer than 2 user turns.",
        )
    _broadcast_fn({"type": "buddy_memory_saved", "session_id": session_id})
    return {"saved": True, "session_id": session_id, "entry": entry.to_dict()}


@router.get("/v2/buddy/profile")
async def get_buddy_profile() -> dict[str, Any]:
    """Return the user's persistent cognitive profile."""
    profile = _conversation_engine.get_user_profile()
    return {
        "profile": profile.to_dict(),
        "expertise_label": profile.expertise_label(),
    }


@router.get("/v2/buddy/goals")
async def get_buddy_goals() -> dict[str, Any]:
    """Return the user's active and completed cross-session goals."""
    profile = _conversation_engine.get_user_profile()
    return {
        "active_goals": profile.active_goals,
        "completed_goals": profile.completed_goals,
        "active_count": len(profile.active_goals),
        "completed_count": len(profile.completed_goals),
    }


@router.post("/v2/buddy/goals/complete")
async def complete_buddy_goal(payload: dict[str, Any]) -> dict[str, Any]:
    """Mark the best-matching active goal as completed."""
    goal_text = str(payload.get("goal_text", "")).strip()
    if not goal_text:
        raise HTTPException(status_code=422, detail="goal_text is required.")
    completed = _conversation_engine.complete_goal(goal_text)
    _broadcast_fn({"type": "buddy_goal_completed",
                   "goal": goal_text, "found": completed})
    return {"completed": completed, "goal_text": goal_text}


@router.get("/v2/buddy/cache/stats")
async def get_buddy_cache_stats() -> dict[str, Any]:
    """Return 3-layer cache hit/miss statistics."""
    return _conversation_engine.get_cache_stats()


@router.post("/v2/buddy/cache/invalidate")
async def invalidate_buddy_cache() -> dict[str, Any]:
    """Clear all 3 cache layers."""
    _conversation_engine.invalidate_cache()
    _broadcast_fn({"type": "buddy_cache_invalidated"})
    return {"invalidated": True, "layers_cleared": ["l1_semantic", "l2_process", "l3_persistent"]}
