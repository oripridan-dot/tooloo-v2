# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: CIRCUS_LOGIC.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/circus_spoke/circus_logic.py
# WHEN: 2026-03-31T14:26:13.352723+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: organ, unmapped, initial-v3
# PURITY: 1.00
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

logger = logging.getLogger("CircusSpoke-Logic")

class CircusSpokeLogic:
    """
    Core Logic for the Manifestation Circus (Spoke-1).
    Manages the visual lifecycle and WebSocket tethering to the viewport.
    """
    
    def __init__(self, port: int = 8085):
        self.port = port
        self.app = FastAPI()
        self.active_connections: List[WebSocket] = []
        self._setup_routes()
        
        self.manifest_history: List[Dict[str, Any]] = []

    def _setup_routes(self):
        """Setup HTML and WebSocket routes."""
        
        @self.app.get("/")
        async def get_index():
            html_path = Path(__file__).parent / "index.html"
            return HTMLResponse(content=html_path.read_text(), status_code=200)

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info("New Viewport connected.")
            
            # Replay history to the new viewport
            for item in self.manifest_history:
                await websocket.send_json(item)
                
            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        msg = json.loads(data)
                        mtype = msg.get("type")
                        
                        if mtype == "user_goal":
                            goal = msg.get("goal")
                            logger.info(f"Sovereign Goal Received: {goal}")
                            asyncio.create_task(self.execute_hub_goal(goal))
                        elif mtype == "user_chat":
                            message = msg.get("message")
                            logger.info(f"Sovereign Chat: {message}")
                            asyncio.create_task(self.execute_hub_chat(message))
                        elif mtype == "key_pulse":
                            await self.broadcast({"type": "key_pulse"})
                            from tooloo_v4_hub.kernel.cognitive.pose_engine import get_pose_engine
                            get_pose_engine().update_listening(0.3)
                        elif mtype == "validation_confirm":
                            logger.info(f"High-Fidelity Interaction Confirmed: {msg.get('item_id')}")
                        elif mtype == "interaction":
                            logger.info(f"Interaction: {msg.get('id')}")
                    except json.JSONDecodeError:
                        logger.info(f"Telemetry: {data}")
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                logger.info("Viewport disconnected.")

    async def execute_hub_chat(self, message: str):
        """Processes a chat message through the Hub's Chat Engine."""
        from tooloo_v4_hub.kernel.cognitive.chat_engine import get_chat_engine
        chat = get_chat_engine()
        response = await chat.process_user_message(message)
        logger.info(f"Buddy Response: {response}")

    async def execute_hub_goal(self, goal: str):
        """Asynchronously executes a goal via the Hub Kernel with the Validation Protocol."""
        from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
        from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus as get_mcp_nexus
        
        nexus = get_mcp_nexus()
        if "circus" not in nexus.tethers:
            await nexus.attach_organ("memory", ["python3", "-m", "tooloo_v4_hub.organs.memory_organ.mcp_server"])
            await nexus.attach_organ("circus", ["python3", "-m", "tooloo_v4_hub.organs.circus_spoke.mcp_server"])
        
        orchestrator = get_orchestrator()
        
        async def status_callback(status):
            """Syncs the Sovereign Status Pipeline with the Viewport."""
            await self.broadcast({"type": "status_update", "status": status})
            if status == "VALIDATING":
                from tooloo_v4_hub.kernel.cognitive.pose_engine import get_pose_engine
                get_pose_engine().update_listening(0.0)
                await asyncio.sleep(0.6) # Subtle Magenta pulse pacing

        await orchestrator.execute_goal(goal, {"user": "Principal Architect"}, callback=status_callback)
        logger.info(f"Goal Validated & Complete: {goal}")

    async def broadcast(self, msg: Dict[str, Any]):
        """Broadcasts a message to all viewports (with Sovereign Safety Check)."""
        if msg is None:
            return
            
        tasks = [asyncio.ensure_future(c.send_json(msg)) for c in self.active_connections]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_value_score(self, total: float, user: float, compliance: float, foresight: float):
        """Specifically broadcasts the 4D Value Planning metrics to the HUD."""
        await self.broadcast({
            "type": "value_update",
            "score": {
                "total": total,
                "user": user,
                "compliance": compliance,
                "foresight": foresight
            }
        })

    async def broadcast_inner_thought(self, thought: str):
        """Broadcasts a cognitive 'Inner Thought' from the calibration engine."""
        await self.broadcast({
            "thought": thought,
            "type": "inner_thought"
        })

    async def adjust_environment(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Live-sculpts the 3D sanctuary settings (color, fog, intensity)."""
        await self.broadcast({
            "type": "environment_update",
            "settings": settings
        })
        logger.info(f"Sanctum Atmosphere Adjusted: {settings}")
        return {"status": "success", "settings": settings}

    async def flag_node_drift(self, node_id: str, delta: float):
        """Visually flags a node in the 3D sanctuary as drifting (Rule 11)."""
        await self.broadcast({
            "type": "drift_pulse",
            "id": node_id,
            "delta": delta,
            "color": "0xff3300" if delta < 0 else "0x00ff88"
        })
        logger.info(f"Drift Pulse emitted for node: {node_id}")

    async def sync_topography(self) -> Dict[str, Any]:
        """Manifests the entire Living Map as 3D PBR Shards in the Sanctum."""
        logger.info("Syncing Hub Topography to Viewport...")
        from tooloo_v4_hub.kernel.governance.living_map import get_living_map
        living_map = get_living_map()
        nodes = living_map.nodes
        
        import math
        shards = []
        
        # Tier-based Radial Distribution
        # T1 (Kernel): Core circle (Radius 20)
        # T2 (Organs): Mid circle (Radius 50)
        # T3 (Others): Outer circle (Radius 100)
        
        for i, (node_id, metadata) in enumerate(nodes.items()):
            # Categorize by path
            material = "basalt"
            radius = 100.0
            y = 5.0
            
            if "kernel" in node_id:
                material = "obsidian"
                radius = 25.0
                y = 15.0
            elif "organs" in node_id or "mcp_server" in node_id:
                material = "steel"
                radius = 60.0
                y = 8.0
            elif "tests" in node_id:
                material = "marble"
                radius = 130.0
                y = 2.0
            
            # Use deterministic angle based on ID hash for stable positioning
            import hashlib
            angle_hash = int(hashlib.md5(node_id.encode()).hexdigest(), 16)
            angle = (angle_hash % 360) * (math.pi / 180)
            
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            
            directive = {
                "type": "manifest_shard",
                "id": node_id.split("/")[-1], # Basename for the label
                "full_id": node_id,
                "material": material,
                "pos": {"x": x, "y": y, "z": z},
                "purity": metadata.get("purity_score", 1.0),
                "version": metadata.get("version", "1.0.0")
            }
            shards.append(directive)
            await self.broadcast(directive)
            self.manifest_history.append(directive)
            
        logger.info(f"Topography Synced: {len(shards)} nodes manifested.")
        return {"status": "success", "count": len(shards)}

    async def manifest_sota_matrix(self) -> Dict[str, Any]:
        """Manifests the entire SOTA matrix as 3D PBR Shards in the Sanctuary."""
        logger.info("Manifesting SOTA Matrix Shards...")
        
        # 1. Fetch learned engrams
        from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic
        memory = await get_memory_logic()
        engrams = memory.query_memory("academy", top_k=20)
        
        shards = []
        for i, engram in enumerate(engrams):
            shard_id = engram["id"].replace("academy_", "")
            # Determine material based on engram data
            manifestation = engram.get("data", {}).get("manifestation", "oak")
            
            # Spatial distribution (Perimeter)
            angle = (i / len(engrams)) * math.pi * 2
            radius = 80.0
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            
            directive = {
                "type": "manifest_shard",
                "id": shard_id,
                "material": manifestation,
                "pos": {"x": x, "y": 10.0, "z": z},
                "principals": engram.get("data", {}).get("principals", [])
            }
            shards.append(directive)
            await self.broadcast(directive)
            self.manifest_history.append(directive)
            
        logger.info(f"SOTA Matrix Manifested: {len(shards)} shards.")
        return {"status": "success", "count": len(shards)}

    async def manifest_node(self, id: str, shape: str = "sphere", color: str = "0x00ccff") -> Dict[str, Any]:
        """Alias for manifest, used by the Orchestrator's parallel DAG engine."""
        return await self.manifest(id, shape=shape, color=color)

    async def manifest(self, id: str, shape: str = "cube", color: str = "0x00ff88") -> Dict[str, Any]:
        """Broadcast a manifestation directive to all connected viewports (Safe)."""
        directive = {
            "type": "manifest",
            "id": id,
            "shape": shape,
            "color": color
        }
        self.manifest_history.append(directive)
        
        tasks = [asyncio.ensure_future(c.send_json(directive)) for c in self.active_connections]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
        logger.info(f"Manifested {shape} '{id}' across {len(self.active_connections)} viewports.")
        return {"status": "success", "id": id}

    async def buddy_act(self, directive: str) -> Dict[str, Any]:
        """Triggers a physical action in the Hub's Pose Engine."""
        from tooloo_v4_hub.kernel.cognitive.pose_engine import get_pose_engine
        engine = get_pose_engine()
        engine.trigger_action(directive)
        
        logger.info(f"Buddy Acted: {directive}")
        return {"status": "success", "directive": directive}

    async def start_pose_stream(self):
        """Dedicated high-priority loop for 30Hz 3D Pose Streaming with Sovereign Pulse."""
        from tooloo_v4_hub.kernel.cognitive.pose_engine import get_pose_engine
        from tooloo_v4_hub.kernel.cognitive.audit_agent import get_audit_agent as get_audit_agent
        from tooloo_v4_hub.kernel.cognitive.calibration import get_calibration_engine
        
        engine = get_pose_engine()
        auditor = get_audit_agent()
        calibration = get_calibration_engine()
        
        logger.info("Sovereign Pose Stream: Pulse-30 Active.")
        tick = 0
        while True:
            # 1. Compute the frame at 33ms intervals
            frame = engine.compute_next_frame(0.033)
            
            # 2. Inject Sovereign Pulse (Vitality/Drift) every 10 ticks (~3Hz)
            if tick % 10 == 0:
                vitality = await auditor.calculate_vitality_index()
                drift = await calibration.compute_drift()
                frame.update({
                    "vitality_index": vitality["vitality"],
                    "purity": vitality["purity"],
                    "drift": drift,
                    "sync_active": True # Soul Sync loop check
                })
            
            # 3. Broadcast to all viewports
            await self.broadcast(frame)
            tick += 1
            await asyncio.sleep(0.033)
            
    async def run_in_background(self):
        """Starts the FastAPI server, the Pose Stream, and the Proactive Agent in the Hub event loop."""
        global _circus_logic
        _circus_logic = self
        
        config = uvicorn.Config(self.app, host="0.0.0.0", port=self.port, log_level="info")
        server = uvicorn.Server(config)
        
        # 1. Proactive Soul Agent + Calibration + Soul Sync
        from tooloo_v4_hub.kernel.cognitive.proactive_agent import get_proactive_agent
        from tooloo_v4_hub.kernel.cognitive.calibration import get_calibration_engine
        from tooloo_v4_hub.kernel.cognitive.soul_sync import get_soul_sync
        
        proactive_agent = get_proactive_agent()
        calibration = get_calibration_engine()
        soul_sync = get_soul_sync()
        
        # 2. Parallel Orchestration
        await asyncio.gather(
            server.serve(),
            self.start_pose_stream(),
            proactive_agent.start_proactive_loop(),
            calibration.start_calibration_loop(interval=120),
            soul_sync.start_sync_loop(interval=300)
        )

# --- Global Logic instance ---
_circus_logic: Optional[CircusSpokeLogic] = None

def get_circus_logic() -> CircusSpokeLogic:
    global _circus_logic
    if _circus_logic is None:
        _circus_logic = CircusSpokeLogic()
    return _circus_logic

if __name__ == "__main__":
    # Test runner
    logic = get_circus_logic()
    asyncio.run(logic.run_in_background())