# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: CHAT_LOGIC.PY | Version: 1.0.0
# WHERE: tooloo_v3_hub/organs/sovereign_chat/chat_logic.py
# WHEN: 2026-03-31T21:55:00.000000
# WHY: Simplified 2D Spoke for Logic Foundations (Rule 7, 13)
# HOW: FastAPI / WebSocket Streaming (Parallel to Hub API)
# TIER: T3:architectural-purity
# DOMAINS: organ, logic, chat, communication, websocket
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import os
import logging
import asyncio
import json
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("SovereignChat-Logic")

class SovereignChatLogic:
    """
    Core Logic for the 2D Sovereign Chat Portal.
    Handles mission dispatching and real-time system feedback.
    """
    
    def __init__(self, port: int = 8087):
        self.port = port
        self.app = FastAPI()
        self.active_connections: List[WebSocket] = []
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        async def get_index():
            html_path = Path(__file__).parent / "index.html"
            return HTMLResponse(content=html_path.read_text(), status_code=200)

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info("Principal Architect Tethered to Sovereign Chat.")
            
            try:
                while True:
                    data = await websocket.receive_text()
                    msg = json.loads(data)
                    mtype = msg.get("type")
                    
                    if mtype == "user_chat":
                        message = msg.get("message")
                        logger.info(f"Sovereign Chat Received: {message}")
                        asyncio.create_task(self.execute_hub_chat(message))
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                logger.info("Architect Untethered.")

    async def execute_hub_chat(self, message: str):
        """Processes a chat message through the Hub's Chat Engine."""
        from tooloo_v3_hub.kernel.cognitive.chat_engine import get_chat_engine
        chat = get_chat_engine()
        
        # Initial status update
        await self.broadcast({"type": "status_update", "status": "COGNITIVE_REASONING"})
        
        # Process via engine
        response = await chat.process_user_message(message)
        
        # Post-process response (The engine broadcasts the buddy_chat type itself in v1.3.0 logic)
        logger.info(f"Buddy Response Manifested: {response}")

    async def broadcast(self, msg: Dict[str, Any]):
        """Broadcasts a message to all viewports."""
        tasks = [asyncio.ensure_future(c.send_json(msg)) for c in self.active_connections]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def run_in_background(self):
        """Starts the FastAPI server and telemetry stream in the background."""
        global _chat_logic
        _chat_logic = self
        
        config = uvicorn.Config(self.app, host="0.0.0.0", port=self.port, log_level="info")
        server = uvicorn.Server(config)
        
        # Start Telemetry Pulse (Shared with Hub logic)
        asyncio.create_task(self.start_telemetry_stream())
        
        await server.serve()

    async def start_telemetry_stream(self):
        """Streams system vitals from the Hub logic at 3Hz."""
        from tooloo_v3_hub.kernel.cognitive.audit_agent import get_audit_agent
        from tooloo_v3_hub.kernel.cognitive.calibration import get_calibration_engine
        
        auditor = get_audit_agent()
        calibration = get_calibration_engine()
        
        logger.info("Sovereign Telemetry Stream: Active.")
        while True:
            try:
                vitality = await auditor.calculate_vitality_index()
                drift = await calibration.compute_drift()
                
                await self.broadcast({
                    "type": "pose_update", # Legacy event name for UI compatibility
                    "vitality_index": vitality["vitality"],
                    "purity": vitality["purity"],
                    "drift": drift
                })
            except: pass
            await asyncio.sleep(0.3)

_chat_logic: Optional[SovereignChatLogic] = None

def get_chat_logic() -> SovereignChatLogic:
    global _chat_logic
    if _chat_logic is None:
        _chat_logic = SovereignChatLogic()
    return _chat_logic
