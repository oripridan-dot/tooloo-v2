# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.api.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

from fastapi import FastAPI, Request, HTTPException, Header
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import asyncio
from engine.self_healer import SpokeSelfHealer
from engine.config import HUB_HMAC_SECRET

logger = logging.getLogger(__name__)

app = FastAPI(title="TooLoo V2 Cognitive Hub API")

# Initialize the healer with the secure HMAC secret from config
healer = SpokeSelfHealer(hmac_secret=HUB_HMAC_SECRET)

class DiagnosticStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"

class DiagnosticPayload(BaseModel):
    repository: str
    commit: str
    status: DiagnosticStatus
    logs: str
    diff: str
    timestamp: str

@app.post("/v1/diagnostics")
async def receive_diagnostic(
    request: Request,
    payload: DiagnosticPayload,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    Secure endpoint for Spokes to report CI failures.
    1. Verifies HMAC-SHA256 signature.
    2. Triggers autonomous repair via SpokeSelfHealer.
    """
    # 1. Verification
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Authentication signature required.")
    
    body = await request.body()
    if not healer.verify_signature(body, x_hub_signature_256):
        logger.warning(f"Unauthorized diagnostic attempt for {payload.repository} @ {payload.commit}")
        raise HTTPException(status_code=403, detail="Invalid HMAC signature.")

    # 2. Autonomous Repair Orchestration
    if payload.status == DiagnosticStatus.FAILURE:
        logger.info(f"CI Failure reported for {payload.repository}. Triggering self-healing.")
        task = asyncio.create_task(healer.handle_ci_failure(payload.model_dump()))
        # We process asynchronously to return a fast 202 to the GitHub Action
        return {"status": "accept", "message": "Diagnostic received. Self-healing initiated."}
    
    return {"status": "ok", "message": "Status reported."}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "TooLoo V2", "sota_ready": True}

if __name__ == "__main__":
    import uvicorn
    import asyncio
    uvicorn.run(app, host="0.0.0.0", port=8004)
