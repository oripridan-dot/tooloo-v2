"""
studio/routes/core.py — Core system endpoints: validation, alerts, stance.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.bus import BusEvent
from engine.stance import Stance, set_active_stance, get_active_stance
from engine.recursive_summarizer import RecursiveSummaryAgent

router = APIRouter(tags=["core"])

_parallel_validation = None
_notification_bus = None
_stance_engine = None
_broadcast_fn = lambda _: None  # noqa: E731

def init(*, parallel_validation, notification_bus, stance_engine, broadcast_fn):
    global _parallel_validation, _notification_bus, _stance_engine, _broadcast_fn
    _parallel_validation = parallel_validation
    _notification_bus = notification_bus
    _stance_engine = stance_engine
    _broadcast_fn = broadcast_fn


class ParallelValidateRequest(BaseModel):
    files: list[dict[str, Any]]
    run_tests: bool = True

@router.post("/v2/validate")
async def parallel_validate(req: ParallelValidateRequest) -> dict[str, Any]:
    from engine.parallel_validator import FileChange
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
        raise HTTPException(status_code=422, detail="No valid file paths provided")
    report = await _parallel_validation.validate_changes(changes, run_tests=req.run_tests)
    return report.to_dict()


# ── NotificationBus ──

@router.get("/v2/alerts")
async def alerts_list(level: str | None = None, limit: int = 50) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 200))
    safe_level = level.upper() if level else None
    events = _notification_bus.history(level=safe_level, limit=safe_limit)
    return {
        "events": [e.to_dict() for e in events],
        "stats": _notification_bus.stats(),
    }

@router.get("/v2/alerts/pending")
async def alerts_pending() -> dict[str, Any]:
    return {"pending": [e.to_dict() for e in _notification_bus.pending()]}

@router.post("/v2/alerts/confirm/{event_id}")
async def alerts_confirm(event_id: str, accepted: bool = True) -> dict[str, Any]:
    result = _notification_bus.confirm(event_id, accepted=accepted)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pending event '{event_id}' not found",
        )
    return result.to_dict()

@router.post("/v2/alerts/dismiss/{event_id}")
async def alerts_dismiss(event_id: str) -> dict[str, Any]:
    removed = _notification_bus.dismiss(event_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Pending event not found")
    return {"event_id": event_id, "dismissed": True}

@router.post("/v2/alerts/publish")
async def alerts_publish(req: dict[str, Any]) -> dict[str, Any]:
    level = str(req.get("level", "INFO")).upper()
    if level not in ("INFO", "INSIGHT", "WARNING", "CRITICAL"):
        level = "INFO"
    event = BusEvent(
        level=level,
        source=str(req.get("source", "api"))[:64],
        message=str(req.get("message", ""))[:500],
        payload=req.get("payload", {}) if isinstance(req.get("payload"), dict) else {},
        requires_confirmation=bool(req.get("requires_confirmation", False)),
    )
    _notification_bus.publish(event)
    return {"published": True, "event_id": event.event_id, "level": event.level}


# ── Cognitive Stance ──

class StanceOverrideRequest(BaseModel):
    stance: str
    mandate_text: str = ""

@router.get("/v2/stance")
async def stance_get() -> dict[str, Any]:
    return get_active_stance().to_dict()

@router.post("/v2/stance")
async def stance_set(req: StanceOverrideRequest) -> dict[str, Any]:
    stance_upper = req.stance.upper()
    try:
        stance_enum = Stance(stance_upper)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stance '{req.stance}'",
        )

    if req.mandate_text:
        result = _stance_engine.detect(mandate_text=req.mandate_text, recent_intents=[stance_upper])
    else:
        from engine.stance import _STANCE_WEIGHTS, _STANCE_BUDDY_PERSONA, StanceResult
        result = StanceResult(
            stance=stance_enum,
            confidence=1.0,
            explanation="Manually set via POST /v2/stance",
            dimension_weights=_STANCE_WEIGHTS[stance_enum],
            buddy_persona=_STANCE_BUDDY_PERSONA[stance_enum],
        )
        set_active_stance(result)

    _broadcast_fn({
        "type": "stance_detected",
        "stance": result.stance.value,
        "confidence": round(result.confidence, 3),
        "explanation": result.explanation,
        "source": "manual_override",
    })
    return result.to_dict()

@router.post("/v2/stance/detect")
async def stance_detect(req: dict[str, Any]) -> dict[str, Any]:
    result = _stance_engine.detect(
        mandate_text=str(req.get("mandate_text", ""))[:512],
        recent_intents=[str(i) for i in req.get("recent_intents", [])][:10],
    )
    _broadcast_fn({
        "type": "stance_detected",
        "stance": result.stance.value,
        "confidence": round(result.confidence, 3),
        "explanation": result.explanation,
    })
    return result.to_dict()

@router.post("/v2/memory/distill")
async def distill_hot_memory() -> dict[str, Any]:
    agent = RecursiveSummaryAgent()
    return agent.distill_pending()
