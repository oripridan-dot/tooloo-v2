# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.workspace_server.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

import asyncio
import json
import logging
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# TooLoo Engine Imports
from engine.mandate_executor import MandateExecutor
from engine.daemon import BackgroundDaemon

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OuroborosServer")

app = FastAPI(title="TooLoo V2 | SOTA Workspace")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MandateRequest(BaseModel):
    prompt: str
    intent: str = "BUILD"

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Global State
daemon_instance = None
executor = MandateExecutor()

@app.on_event("startup")
async def startup_event():
    global daemon_instance
    # Initialize Daemon with the WebSocket broadcast hook
    daemon_instance = BackgroundDaemon(broadcast_fn=manager.broadcast)
    asyncio.create_task(daemon_instance.start())
    logger.info("Background Daemon initialized and broadcast-linked.")

@app.get("/health")
async def health():
    return {"status": "OPTIMAL", "version": "2.1.0-Ouroboros"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/mandate")
async def execute_mandate(request: MandateRequest):
    logger.info(f"Executing Mandate: {request.prompt}")
    # Trigger the executor (Real-time update will be pushed via Daemon if it touches files)
    # For now, we return a confirmation and the executor runs in the background
    asyncio.create_task(executor.execute(request.prompt, intent=request.intent))
    return {"status": "ACCEPTED", "prompt": request.prompt}

@app.post("/approve/{proposal_id}")
async def approve_patch(proposal_id: str):
    if daemon_instance:
        return await daemon_instance.approve(proposal_id)
    return {"status": "error", "msg": "Daemon not initialized"}

@app.post("/reject/{proposal_id}")
async def reject_patch(proposal_id: str):
    if daemon_instance:
        return await daemon_instance.reject(proposal_id)
    return {"status": "error", "msg": "Daemon not initialized"}

@app.post("/reject/{proposal_id}")
async def reject_patch(proposal_id: str):
    if daemon_instance:
        return daemon_instance.reject(proposal_id)
    return {"status": "error", "msg": "Daemon not initialized"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8099)
