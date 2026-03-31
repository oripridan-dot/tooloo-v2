# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: HUB_API.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/kernel/hub_api.py
# WHEN: 2026-03-31T14:26:13.345038+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: kernel, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import os
import logging
import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request, Depends, Header, BackgroundTasks
from pydantic import BaseModel

from tooloo_v3_hub.kernel.orchestrator import SovereignOrchestrator
from tooloo_v3_hub.kernel.cognitive.audit_agent import get_audit_agent as get_audit_agent
from tooloo_v3_hub.kernel.mcp_nexus import get_mcp_nexus as get_mcp_nexus
from tooloo_v3_hub.kernel.cognitive.calibration import get_calibration_engine

# Security Configuration
SOVEREIGN_KEY = os.getenv("SOVEREIGN_KEY", "SOVEREIGN_HUB_2026_V3")

async def verify_sovereign_key(x_sovereign_key: str = Header(...)):
    if x_sovereign_key != SOVEREIGN_KEY:
        logger.warning(f"Unauthorized Access Attempt: {x_sovereign_key}")
        raise HTTPException(status_code=403, detail="Sovereign Key Invalid")
    return x_sovereign_key

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HubAPI")

app = FastAPI(title="TooLoo Sovereign Hub", version="3.1.0")

# Mount Sovereign Portal (Rule 7: UX Supremacy)
portal_path = os.path.join(os.path.dirname(__file__), "..", "portal")
if os.path.exists(portal_path):
    app.mount("/portal", StaticFiles(directory=portal_path), name="portal")
    
@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(portal_path, "index.html"))

# Telemetry WebSocket (Rule 2: Realtime Awareness)
active_connections: List[WebSocket] = []

@app.websocket("/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text() # Heartbeat
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_telemetry(message: Dict[str, Any]):
    for connection in active_connections:
        await connection.send_json(message)

class GoalRequest(BaseModel):
    goal: str
    context: Dict[str, Any] = {}
    mode: str = "MACRO"
    async_execute: bool = False

class ToolCallRequest(BaseModel):
    organ: str
    tool: str
    arguments: Dict[str, Any]

class SyncRequest(BaseModel):
    engrams: List[Dict[str, Any]]

@app.on_event("startup")
async def startup_event():
    logger.info("Sovereign Hub (Galactic Node) Awakening...")
    
    # 1. Bootstrap the Nexus & Tether Organs (Rule 13) - NON-BLOCKING (Rule 12)
    nexus = get_mcp_nexus()
    asyncio.create_task(nexus.initialize_default_organs())
    logger.info("MCP Nexus Initialization DISPATCHED to background.")
    
    # 2. Activate Cloud Training (Calibration)
    try:
        calibration = get_calibration_engine()
        asyncio.create_task(calibration.start_calibration_loop(interval=300))
        logger.info("Autonomous Calibration Engine Active (Pulse: 300s).")
    except Exception as e:
        logger.warning(f"Calibration Engine failed to start: {e}")

@app.get("/health")
async def health():
    return {"status": "SOVEREIGN", "node": os.getenv("K_SERVICE", "local-hub")}

@app.get("/vitality", dependencies=[Depends(verify_sovereign_key)])
async def vitality():
    auditor = get_audit_agent()
    return await auditor.calculate_vitality_index()

@app.post("/execute", dependencies=[Depends(verify_sovereign_key)])
async def execute_goal(request: GoalRequest, background_tasks: BackgroundTasks):
    from tooloo_v3_hub.kernel.orchestrator import get_orchestrator
    orchestrator = get_orchestrator()
    try:
        if request.async_execute:
            logger.info(f"Galactic Node: Dispatching Async Goal: {request.goal}")
            background_tasks.add_task(orchestrator.execute_goal, request.goal, request.context, mode=request.mode)
            return {"status": "dispatched", "goal": request.goal}
            
        logger.info(f"Galactic Node: Executing Goal: {request.goal}")
        results = await orchestrator.execute_goal(request.goal, request.context, mode=request.mode)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Execution Fault: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync", dependencies=[Depends(verify_sovereign_key)])
async def sync_engrams(request: SyncRequest):
    """Federated Soul Sync: Injects engrams from peer nodes."""
    nexus = get_mcp_nexus()
    success_count = 0
    for e in request.engrams:
        try:
            # Propagate the engram to local memory
            # Map engram format to memory_store args
            await nexus.call_tool("memory_organ", "memory_store", {
                "engram_id": e.get("id", f"federated_{id(e)}"),
                "data": e.get("data", {}),
                "tier": 2
            })
            success_count += 1
        except Exception as ex:
             logger.error(f"Sync Failure for engram {e.get('id')}: {ex}")
             
    logger.info(f"Galactic Node: Soul Sync Complete ({success_count} engrams ingested).")
    return {"status": "success", "count": success_count}

@app.post("/audit", dependencies=[Depends(verify_sovereign_key)])
async def audit():
    auditor = get_audit_agent()
    return await auditor.perform_audit()

@app.get("/status", dependencies=[Depends(verify_sovereign_key)])
async def get_status():
    """Returns the tethered state of all federated organs."""
    nexus = get_mcp_nexus()
    tethers_summary = {}
    for name, config in nexus.tethers.items():
        tethers_summary[name] = {
            "status": config.get("status"),
            "type": config.get("type"),
            "tools": [t.name for t in config.get("tools", [])]
        }
    return {"status": "ACTIVE", "tethers": tethers_summary}

@app.post("/call_tool", dependencies=[Depends(verify_sovereign_key)])
async def call_tool_direct(request: ToolCallRequest):
    """Directly executes a tool on a tethered organ (Diagnostic/SOTA Verification)."""
    nexus = get_mcp_nexus()
    try:
        result = await nexus.call_tool(request.organ, request.tool, request.arguments)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Tool Call Failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))