# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: CHAT_LOGIC.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/sovereign_chat/chat_logic.py
# WHEN: 2026-03-31T21:55:00.000000
# WHY: Simplified 2D Spoke for Logic Foundations (Rule 7, 13)
# HOW: FastAPI / WebSocket Streaming (Parallel to Hub API)
# TIER: T3:architectural-purity
# DOMAINS: organ, logic, chat, communication, websocket
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

"""Sovereign Chat Logic

Provides a FastAPI WebSocket server that receives user chat messages, persists them via
`ChatRepository`, forwards the message to the Hub's `ChatEngine`, and streams the
assistant's token‑by‑token response back to the client.

All interactions are stamped with the 6W protocol for constitutional compliance.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from tooloo_v4_hub.kernel.cognitive.protocols import (
    SovereignMessage,
    CognitivePulse,
    HandoverEvent,
)
from tooloo_v4_hub.kernel.governance.living_map import get_living_map
from tooloo_v4_hub.spokes.repositories import ChatRepository

logger = logging.getLogger("SovereignChat-Logic")


class SovereignChatLogic:
    """Core WebSocket chat orchestrator.

    - Persists inbound user messages via :class:`ChatRepository`.
    - Streams token responses from the Hub's :class:`ChatEngine`.
    - Emits telemetry updates at 3 Hz.
    """

    def __init__(self):
        import os
        self.port = int(os.getenv('PORT', '8080'))
        self.app = FastAPI()
        self.active_connections: List[WebSocket] = []
        # Choose repository based on env var
        if os.getenv('USE_GCS', 'false').lower() == 'true':
            from .gcs_repository import GCSChatRepository
            bucket_name = os.getenv('GCS_BUCKET')
            self.repo = GCSChatRepository(bucket_name=bucket_name)
        else:
            self.repo = ChatRepository()
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.on_event("startup")
        async def on_startup():
            # Rule 12: Fire-and-Forget Agency Initialization
            await self.initialize_agency()

        @self.app.get("/")
        async def get_index() -> HTMLResponse:
            html_path = Path(__file__).parent / "index.html"
            return HTMLResponse(content=html_path.read_text(), status_code=200)

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info("Principal Architect Tethered to Sovereign Chat.")
            
            # Rule 1: Sync System Vitality on Connect
            living_map = get_living_map()
            await websocket.send_text(json.dumps({
                "type": "SYSTEM_STATUS_UPDATE",
                "payload": {
                    "node_count": len(living_map.nodes),
                    "status": "VITAL" if len(living_map.nodes) > 10 else "BOOTSTRAPPING"
                }
            }))
            try:
                while True:
                    data = await websocket.receive_text()
                    msg = json.loads(data)
                    mtype = msg.get("type")
                    if mtype == "user_chat":
                        message = msg.get("message")
                        inbound_msg = SovereignMessage(role="user", content=message)
                        # Store message (await if async, fallback sync)
                        try:
                            await self.repo.store_message(inbound_msg)
                        except TypeError:
                            self.repo.store_message(inbound_msg)
                        logger.info(f"Sovereign Chat Received: {message}")
                        asyncio.create_task(self.execute_hub_chat(message))
                    elif mtype == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                logger.info("Architect Untethered.")

    async def execute_hub_chat(self, message: str) -> None:
        """Process a chat message through the Hub's Chat Engine with token streaming."""
        from tooloo_v4_hub.kernel.cognitive.chat_engine import get_chat_engine

        chat = get_chat_engine(self.repo)
        await self.broadcast(CognitivePulse(status="COGNITIVE_REASONING"))
        full_response = ""
        async for token in chat.process_user_message(message):
            await self.broadcast({"type": "buddy_token", "token": token})
            full_response += token
        logger.info(f"Buddy Response Streamed: {len(full_response)} chars.")

    async def broadcast(self, msg: Union[Dict[str, Any], SovereignMessage, CognitivePulse, HandoverEvent]) -> None:
        """Send a message to the unified Hub WebSocket (Principal Control Plane)."""
        try:
            from tooloo_v4_hub.kernel.cognitive.transmission import broadcast_buddy
            await broadcast_buddy(msg)
        except Exception as e:
            logger.error(f"Unified Transmission Failure: {e}")

    async def run_in_background(self) -> None:
        """Legacy background runner – retained for backward compatibility (Rule 13)."""
        logger.info("ChatLogic: Unified Orchestration Active. Legacy Background Runner Stalled.")
        pass

    async def start_telemetry_stream(self) -> None:
        """Emit system vitals at ~3 Hz for the UI telemetry sandbox."""
        from tooloo_v4_hub.kernel.cognitive.audit_agent import get_audit_agent
        from tooloo_v4_hub.kernel.cognitive.calibration import get_calibration_engine

        auditor = get_audit_agent()
        calibration = get_calibration_engine()
        logger.info("Sovereign Telemetry Stream: Active.")
        while True:
            try:
                vitality = await auditor.calculate_vitality_index()
                drift = await calibration.compute_drift()
                await self.broadcast({
                    "type": "pose_update",
                    "vitality_index": vitality["vitality"],
                    "purity": vitality["purity"],
                    "drift": drift,
                })
            except Exception:
                pass
            await asyncio.sleep(0.3)

    async def _heartbeat_loop(self) -> None:
        """Rule 12: Prevents WebSocket 1006 timeouts (every 20s)."""
        while True:
            await asyncio.sleep(20)
            if self.active_connections:
                # We broadcast a lightweight ping to keep connection logic hot
                await self.broadcast({"type": "hub_heartbeat", "pulse": "STABLE"})

    async def initialize_agency(self) -> None:
        """Rule 12: Bootstraps Buddy's Pulse."""
        logger.info("Buddy Agency: Core Pulse ACTIVE.")
        asyncio.create_task(self._heartbeat_loop())


_chat_logic: Optional[SovereignChatLogic] = None

def get_chat_logic() -> SovereignChatLogic:
    """Singleton accessor for the chat logic instance."""
    global _chat_logic
    if _chat_logic is None:
        _chat_logic = SovereignChatLogic()
    return _chat_logic
