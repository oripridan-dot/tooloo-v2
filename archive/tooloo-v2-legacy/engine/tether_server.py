# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: MCP Tether Server (WebSocket Hub v1.2)
# WHERE: engine/tether_server.py
# WHEN: 2026-03-29T03:50:00
# WHY: Support for synchronous-style polling of spatial data (Vision)
# HOW: asyncio.Future for request-response matching
# ==========================================================

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

class TetherServer:
    """Manages active WebSocket connections and track request-response cycles."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TetherServer, cls).__new__(cls)
            cls._instance.active_connections: Dict[str, WebSocket] = {}
            cls._instance.spoke_metadata: Dict[str, Dict[str, Any]] = {}
            cls._instance.pending_requests: Dict[str, asyncio.Future] = {}
        return cls._instance

    async def connect(self, spoke_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[spoke_id] = websocket
        self.spoke_metadata[spoke_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "messages_sent": 0,
            "last_seen": asyncio.get_event_loop().time()
        }
        print(f"[Tether] Spoke '{spoke_id}' connected.")

    def disconnect(self, spoke_id: str):
        if spoke_id in self.active_connections:
            del self.active_connections[spoke_id]
            del self.spoke_metadata[spoke_id]
            print(f"[Tether] Spoke '{spoke_id}' disconnected.")

    async def send_command(self, spoke_id: str, command: Dict[str, Any], wait_for_response: bool = False, timeout: float = 10.0) -> Any:
        """Send a JSON command. If wait_for_response is True, returns the response payload."""
        if spoke_id not in self.active_connections:
            if spoke_id == "any" and self.active_connections:
                spoke_id = list(self.active_connections.keys())[0]
            else:
                return False if not wait_for_response else None
        
        request_id = str(uuid.uuid4())
        command["request_id"] = request_id
        
        ws = self.active_connections[spoke_id]
        
        try:
            future = None
            if wait_for_response:
                future = asyncio.get_event_loop().create_future()
                self.pending_requests[request_id] = future
                
            await ws.send_text(json.dumps(command))
            self.spoke_metadata[spoke_id]["messages_sent"] += 1
            
            if wait_for_response:
                try:
                    return await asyncio.wait_for(future, timeout=timeout)
                except asyncio.TimeoutError:
                    print(f"[Tether] Request {request_id} timed out.")
                    return None
                finally:
                    if request_id in self.pending_requests:
                        del self.pending_requests[request_id]
            return True
        except Exception as e:
            print(f"[Tether] Send Error: {e}")
            self.disconnect(spoke_id)
            return False if not wait_for_response else None

    def handle_response(self, request_id: str, payload: Dict[str, Any]):
        """Match an incoming response to a pending request."""
        if request_id in self.pending_requests:
            future = self.pending_requests[request_id]
            if not future.done():
                future.set_result(payload)

    async def broadcast(self, command: Dict[str, Any]):
        for sid in list(self.active_connections.keys()):
            await self.send_command(sid, command)

_tether_server = TetherServer()
def get_tether_server() -> TetherServer:
    return _tether_server
