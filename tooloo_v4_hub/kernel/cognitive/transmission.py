# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: transmission.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/transmission.py
# WHEN: 2026-04-03T16:08:23.403235+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

# WHAT: TRANSMISSION.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/transmission.py
# WHY: Rule 13: Strict Physical Decoupling & Unified Pulse Routing
# HOW: Singleton Connection Registry for WebSocket Federation

import logging
import json
from typing import List, Any, Dict
from fastapi import WebSocket

logger = logging.getLogger("SovereignTransmission")

# The Primary Seat of Manifestation (Rule 7: Real-time UI Synergy)
buddy_connections: List[WebSocket] = []

async def register_buddy(websocket: WebSocket):
    """Registers a high-fidelity portal connection (accepted handshake)."""
    buddy_connections.append(websocket)
    logger.info(f"Transmission: High-Fidelity Buddy Link Established [{len(buddy_connections)} active]")

async def deregister_buddy(websocket: WebSocket):
    """Safely severs a portal connection (Rule 15: Zero-Footprint Exit)."""
    if websocket in buddy_connections:
        buddy_connections.remove(websocket)
        logger.info(f"Transmission: Buddy Link Dissolved [{len(buddy_connections)} remaining]")

async def broadcast_buddy(message: Any):
    """Broadcasts a cognitive pulse to all registered portal viewports."""
    # Rule 10: Structural Integrity Check
    if hasattr(message, "model_dump_json"):
        msg_dict = json.loads(message.model_dump_json())
    else:
        msg_dict = message
        
    logger.debug(f"Transmission: Pulsing {msg_dict.get('type')} to {len(buddy_connections)} nodes.")
    
    for connection in buddy_connections:
        try:
            await connection.send_json(msg_dict)
        except Exception as e:
            logger.error(f"Transmission: Failed to pulse node: {e}")
            # Note: We do NOT remove here to avoid modifying list during iteration
            # Deregistration happens on WebSocketDisconnect
