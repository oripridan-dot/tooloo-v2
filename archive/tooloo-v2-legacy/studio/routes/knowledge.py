"""
studio/routes/knowledge.py — Knowledge Banks & SOTA Ingestion endpoints.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

class KnowledgeQueryRequest(BaseModel):
    topic: str
    context: str = ""
    n_per_bank: int = 3

class KnowledgeIngestRequest(BaseModel):
    bank_id: str
    domain: str
    signals: list[str]

router = APIRouter(tags=["knowledge"])

_bank_manager = None
_sota_ingestion = None
_broadcast_fn = lambda _: None  # noqa: E731

def init(*, bank_manager, sota_ingestion, broadcast_fn):
    global _bank_manager, _sota_ingestion, _broadcast_fn
    _bank_manager = bank_manager
    _sota_ingestion = sota_ingestion
    _broadcast_fn = broadcast_fn

@router.get("/v2/knowledge/health")
async def knowledge_health() -> dict[str, Any]:
    return _bank_manager.health()

@router.get("/v2/knowledge/dashboard")
async def knowledge_dashboard() -> dict[str, Any]:
    return _bank_manager.dashboard()

@router.get("/v2/knowledge/{bank_id}")
async def get_knowledge_bank(bank_id: str) -> dict[str, Any]:
    bank = _bank_manager.get_bank(bank_id)
    if bank is None:
        return {"error": f"Unknown bank: {bank_id}", "valid_ids": list(_bank_manager.all_banks())}
    return {
        "bank_id": bank_id,
        "bank_name": bank.bank_name,
        "domains": bank.domains,
        "entries": [e.to_dict() for e in bank.all_entries()],
    }

@router.get("/v2/knowledge/{bank_id}/signals")
async def get_bank_signals(bank_id: str, domain: str = "", n: int = 5) -> dict[str, Any]:
    bank = _bank_manager.get_bank(bank_id)
    if bank is None:
        return {"error": f"Unknown bank: {bank_id}"}
    return {"bank_id": bank_id, "domain": domain, "signals": bank.get_signals(domain, n)}

@router.post("/v2/knowledge/query")
async def query_knowledge(req: KnowledgeQueryRequest) -> dict[str, Any]:
    results = _bank_manager.query_all(req.topic, req.context, req.n_per_bank)
    return {
        "topic": req.topic,
        "results": [e.to_dict() for e in results],
        "count": len(results),
    }

@router.post("/v2/knowledge/ingest")
async def ingest_knowledge(req: KnowledgeIngestRequest) -> dict[str, Any]:
    try:
        report = _sota_ingestion.ingest_single(req.bank_id, req.domain, req.signals)
        _broadcast_fn({"type": "knowledge_ingested", "report": report.to_dict()})
        return report.to_dict()
    except ValueError as exc:
        return {"error": str(exc)}

@router.post("/v2/knowledge/ingest/full")
async def run_full_sota_ingestion() -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, _sota_ingestion.run_full_ingestion)
    _broadcast_fn({"type": "sota_ingestion_complete", "report": report.to_dict()})
    return report.to_dict()

@router.get("/v2/knowledge/intent/{intent}/signals")
async def get_intent_signals(intent: str, n: int = 5) -> dict[str, Any]:
    signals = _bank_manager.signals_for_intent(intent.upper(), n)
    return {"intent": intent.upper(), "signals": signals, "count": len(signals)}
