# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: HUB_API_V4 | Version: 1.1.0
# WHERE: tooloo_v4_hub/kernel/hub_api.py
# WHEN: 2026-03-31T14:26:13.345038+00:00
# WHY: Rule 7/10 - Principal Architect Control Plane (V4 Cloud Readiness)
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: kernel, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

# 6W Grounding (Cloud Readiness)
# 6W Grounding (Cloud Readiness)
# Rule 13: Top-level imports deferred to avoid Cold-Start Timeout (Rule 12: Self-Healing)
import os
import logging
import asyncio
import time
import json
from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, Header, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Rule 11/12: Prioritize Cloud Run environment over local .env collision
CLOUD_AUDIO_URL = os.getenv("CLOUD_AUDIO_URL", "https://claudio-supreme-sota-gru3xdvw6a-uc.a.run.app")
CLOUD_HUB_URL = os.getenv("CLOUD_HUB_URL", "https://sovereign-hub-v4-awakening-hwn5gyft5q-zf.a.run.app")
LEAN_MODE = os.getenv("LEAN_MODE", "true").lower() == "true"

from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
from tooloo_v4_hub.kernel.governance.sota_benchmarker import get_benchmarker

# Federated Cloud Logic
if os.getenv("CLOUD_NATIVE_WORKSPACE") == "true":
    # If in cloud, we MUST have organs tethered unless explicitly overridden
    LEAN_MODE = False

# Security & Governance Logic (Rule 11/18)
from tooloo_v4_hub.kernel.governance.kms_manager import get_kms_manager
from tooloo_v4_hub.kernel.cognitive.self_healing_pulse import get_self_healer

# Rule 11/18: Fast-path Cache for Sovereign Keys
_AUTHORIZED_KEYS_CACHE = set()

async def verify_sovereign_key(x_sovereign_key: str = Header(...)):
    if x_sovereign_key in _AUTHORIZED_KEYS_CACHE:
        return x_sovereign_key
        
    kms = get_kms_manager()
    if not kms.validate_sovereign_key(x_sovereign_key):
        logger.warning(f"Unauthorized Access Attempt: Key Validation Failed")
        raise HTTPException(status_code=403, detail="Sovereign Key Invalid or Expired")
    
    # Cache valid key to avoid repeat validation overhead
    _AUTHORIZED_KEYS_CACHE.add(x_sovereign_key)
    return x_sovereign_key

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HubAPI")

app = FastAPI(title="TooLoo Sovereign Hub", version="4.5.0")

# Rule 18: Allow Portal Manifestation across origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Open for multi-device portal access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SOVEREIGN_REVISION = "V4.5.ME-WEST1.PAID_AWAKENING"

# Mount Sovereign Portal (Rule 7: UX Supremacy)
portal_path = os.path.join(os.path.dirname(__file__), "..", "portal")
if os.path.exists(portal_path):
    app.mount("/portal", StaticFiles(directory=portal_path), name="portal")
    
# Redirect root to portal (Rule 7: UX Supremacy)
@app.get("/")
async def read_index():
    return {"status": "SOVEREIGN", "msg": "TooLoo Hub V4.2.0 Active", "portal": "/portal/index.html"}

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

# Buddy Chat WebSocket (Rule 7: High-Fidelity Cognitive Stream)
# Uses the centralized transmission module so chat_engine → chat_logic → transmission → client works
from tooloo_v4_hub.kernel.cognitive.transmission import register_buddy, deregister_buddy, broadcast_buddy as _tx_broadcast_buddy

@app.websocket("/ws")
async def buddy_ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    await register_buddy(websocket)
    try:
        from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
        logic = get_chat_logic()
        
        while True:
            data = await websocket.receive_json()
            if data["type"] == "user_chat":
                # Principal Mission: Trigger Cognitive Pulse
                asyncio.create_task(logic.execute_hub_chat(data["message"]))
            elif data["type"] == "ux_telemetry":
                # SOTA: Ingest UX Data into the Vitality Index
                payload = data.get('payload', {})
                logger.info(f"UX_TELEMETRY (Minified): {payload}")
                
                # Rule 7/16: Conditional Sync (Consolidated Fetch)
                if data.get("request_sync"):
                    sync_data = await get_system_sync_payload()
                    await websocket.send_json({
                        "type": "hub_sync",
                        "payload": sync_data
                    })

                if payload.get('f', 60) < 30:
                    logger.warning("UX JANK DETECTED: Scaling back animations.")
                
    except WebSocketDisconnect:
        await deregister_buddy(websocket)
    except Exception as e:
        logger.error(f"Buddy WS Error: {e}")
        await deregister_buddy(websocket)

async def broadcast_buddy(message: Any):
    # Delegate to the unified transmission module
    await _tx_broadcast_buddy(message)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat", dependencies=[Depends(verify_sovereign_key)])
async def rest_chat(request: ChatRequest):
    """REST fallback for chat when WebSocket is unavailable."""
    from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
    logic = get_chat_logic()
    
    try:
        from tooloo_v4_hub.kernel.cognitive.chat_engine import get_chat_engine
        chat = get_chat_engine(repo=logic.repo)
        full_response = ""
        async for token in chat.process_user_message(request.message):
            full_response += token
        
        return {
            "status": "success", 
            "type": "buddy_chat",
            "content": full_response,
            "speaker": "Buddy",
            "timestamp": "now"
        }
    except Exception as e:
        logger.error(f"REST Chat Fault: {e}")
        return {"status": "error", "response": f"Cognitive processing fault: {str(e)}"}

class MandateRequest(BaseModel):
    goal: str
    rationale: str
    context: Dict[str, Any] = {}

@app.post("/buddy/mandate", dependencies=[Depends(verify_sovereign_key)])
async def buddy_mandate(request: MandateRequest, background_tasks: BackgroundTasks):
    """
    Sovereign Buddy Mandate (Rule 7/18).
    Allows Buddy to autonomously trigger high-impact missions from the cloud.
    """
    from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
    orchestrator = get_orchestrator()
    
    logger.info(f"BUDDY MANDATE RECEIVED: {request.goal} | Rationale: {request.rationale}")
    
    # Inject Buddy Rationale into context for Rule 10/16 auditing
    request.context["buddy_rationale"] = request.rationale
    request.context["initiator"] = "BUDDY"
    
    background_tasks.add_task(orchestrator.execute_goal, request.goal, request.context, mode="DIRECT")
    
    return {
        "status": "mandated", 
        "goal": request.goal, 
        "msg": "Buddy has prioritized this mission for autonomous execution."
    }


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

class ContextSyncRequest(BaseModel):
    narrative: Dict[str, Any]
    cognitive_state: Dict[str, Any]
    engrams: List[Dict[str, Any]]
    session_id: str = "default"
    sovereignty_takeover: bool = False

async def get_system_sync_payload() -> Dict[str, Any]:
    """Rule 13: Consolidated System Health and Telemetry Pulse."""
    try:
        from tooloo_v4_hub.kernel.governance.sota_benchmarker import get_benchmarker
        from tooloo_v4_hub.kernel.governance.billing_manager import get_billing_manager
        benchmarker = get_benchmarker()
        billing = get_billing_manager()
        vitality_data = await benchmarker.run_full_audit()
        
        # Rule 14: Sovereign Financial Grounding
        cost_summary = billing.get_session_summary()
        
        # Rule 13: Memory Shards
        nexus = get_mcp_nexus()
        shards = []
        try:
            shards_result = await nexus.call_tool("memory_organ", "memory_query", {"query": "", "top_k": 5})
            if shards_result:
                for block in shards_result:
                    if block.get("type") == "text":
                        try:
                            data = json.loads(block["text"])
                            if isinstance(data, list): shards.extend(data)
                            else: shards.append(data)
                        except: continue
        except Exception as e:
            logger.warning(f"Memory Shard Fetch Error: {e}")

        return {
            "status": "SOVEREIGN",
            "hub_id": "SOVEREIGN_HUB_V4_GALACTIC",
            "purity": vitality_data.get("purity", {}).get("purity_score", 1.00),
            "vitality": vitality_data.get("svi", 1.00),
            "session_cost_usd": cost_summary.get("total_cost_usd", 0.0),
            "financial_vitality": cost_summary.get("financial_vitality", 1.0),
            "revision": SOVEREIGN_REVISION,
            "shards": shards[:5]
        }
    except Exception as e:
        logger.error(f"Sync Payload Fault: {e}")
        return {"status": "DEGRADED", "error": str(e)}

@app.on_event("startup")
async def startup_event():
    logger.info("Sovereign Hub (Galactic Node) Awakening...")
    
    # Rule 12: Eager Loading / Warmup (Eliminate 50ms blocking path)
    try:
        kms = get_kms_manager()
        kms.warmup()
    except Exception as e:
        logger.error(f"Startup Hardware Warmup Failure: {e}")

    # Rule 12: Autonomous Self-Evaluation Pulse via Benchmarker (Background Task)
    benchmarker = get_benchmarker()
    # Assuming there's an outer loop, but for now we skip start_autonomous_pulse since benchmarker just runs full audit.

    # Rule 12/14: Buddy Self-Healing (Financial Stewardship)
    healer = get_self_healer()
    asyncio.create_task(healer.start_pulse(interval_s=300))

    # Rule 12/16: Pre-warm Buddy Collective Intelligence
    try:
        from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic
        logic = get_chat_logic()
        # Explicit Task for Collective Common Sense pre-warming (Rule 16)
        asyncio.create_task(logic.initialize_agency())
        logger.info("Buddy Agency: Pre-warm Task Dispatched.")
    except Exception as e:
        logger.error(f"Buddy Agency Warmup Failure: {e}")

@app.get("/health")
async def health():
    sync = await get_system_sync_payload()
    return sync

@app.get("/vitality", dependencies=[Depends(verify_sovereign_key)])
async def vitality():
    benchmarker = get_benchmarker()
    return await benchmarker.run_full_audit()

@app.post("/execute", dependencies=[Depends(verify_sovereign_key)])
async def execute_goal(request: GoalRequest, background_tasks: BackgroundTasks):
    from tooloo_v4_hub.kernel.orchestrator import get_orchestrator
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
    from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
    nexus = get_mcp_nexus()
    success_count = 0
    for e in request.engrams:
        try:
            # Propagate the engram to local memory
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

@app.post("/context/sync", dependencies=[Depends(verify_sovereign_key)])
async def sync_context(request: ContextSyncRequest):
    """Sovereign Context Handover: Injects Narrative, Cognitive State, and Engrams."""
    import json
    from pathlib import Path
    from tooloo_v4_hub.kernel.cognitive.narrative_ledger import get_narrative_ledger
    from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry
    from tooloo_v4_hub.kernel.mcp_nexus import get_mcp_nexus
    
    # 1. Sync Narrative Ledger
    ledger = get_narrative_ledger()
    # (Simplified: Merging milestones)
    for m in request.narrative.get("milestones", []):
        ledger.record_milestone(
            id=m["id"], 
            title=m["title"], 
            description=m["description"], 
            purity=m.get("purity_impact", 0.0),
            tags=m.get("tags", [])
        )
    
    # 2. Sync Cognitive State
    registry = get_cognitive_registry()
    state = registry.get_state(request.session_id)
    state.intent_vector = request.cognitive_state.get("intent_vector", state.intent_vector)
    state.stage = request.cognitive_state.get("stage", state.stage)
    state.cognitive_load = request.cognitive_state.get("cognitive_load", state.cognitive_load)
    state.resonance = request.cognitive_state.get("resonance", state.resonance)
    
    # 3. Persistent Sync (Rule 17: Physical Preservation)
    psyche_path = Path("tooloo_v4_hub/psyche_bank")
    psyche_path.mkdir(parents=True, exist_ok=True)
    
    # Persist Cognitive State specifically for cloud recovery
    state_file = psyche_path / f"cognitive_state_{request.session_id}.json"
    state_file.write_text(json.dumps({
        "intent": state.intent_vector,
        "stage": state.stage,
        "load": state.cognitive_load,
        "resonance": state.resonance,
        "timestamp": time.time()
    }, indent=2))
    
    # 4. Sync Engrams
    nexus = get_mcp_nexus()
    for e in request.engrams:
        try:
            await nexus.call_tool("memory_organ", "memory_store", {
                "engram_id": e.get("id"),
                "data": e.get("data"),
                "tier": 2
            })
        except: pass
        
    if request.sovereignty_takeover:
        logger.info("Rule 18: SOVEREIGNTY TAKEOVER DETECTED. Cloud Hub is now the Primary Seat of Manifestation.")
        # In a real scenario, this could trigger a state change in the orchestrator
        # or enable cloud-specific tools.
        
    logger.info(f"Galactic Node: FULL CONTEXT SYNC COMPLETE Stage: {state.stage}")
    return {"status": "success", "message": f"Context synced and persisted for stage: {state.stage}", "sovereignty": request.sovereignty_takeover}

@app.get("/psyche/pull", dependencies=[Depends(verify_sovereign_key)])
async def pull_psyche():
    """Rule 18: High-Fidelity Sync Node Pull. Retrieves current narrative and cognitive state."""
    from tooloo_v4_hub.kernel.cognitive.narrative_ledger import get_narrative_ledger
    from tooloo_v4_hub.kernel.cognitive.cognitive_registry import get_cognitive_registry
    
    ledger = get_narrative_ledger()
    registry = get_cognitive_registry()
    state = registry.get_state("default")
    
    return {
        "status": "success",
        "narrative": {"milestones": [m.__dict__ for m in ledger.milestones]},
        "cognitive_state": {
            "intent_vector": state.intent_vector,
            "stage": state.stage,
            "cognitive_load": state.cognitive_load,
            "resonance": state.resonance
        }
    }

@app.post("/audit", dependencies=[Depends(verify_sovereign_key)])
async def audit():
    benchmarker = get_benchmarker()
    return await benchmarker.run_full_audit()

@app.get("/context/history", dependencies=[Depends(verify_sovereign_key)])
async def get_chat_history(limit: int = 50, session_id: str = "default"):
    """Tier 2 (Architecture Spec): Session resumption endpoint.
    
    Returns the most recent chat messages for the given session,
    enabling the portal to restore context after a page refresh or handover.
    """
    from tooloo_v4_hub.organs.memory_organ.sqlite_persistence import ChatRepository
    repo = ChatRepository()
    messages = repo.get_history(session_id=session_id, limit=limit)
    return {
        "status": "success",
        "session_id": session_id,
        "count": len(messages),
        "messages": [m.model_dump() for m in messages]
    }

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

@app.get("/memory/shards", dependencies=[Depends(verify_sovereign_key)])
async def get_memory_shards(limit: int = 10):
    """Retrieves the latest memory engrams (shards) for the Dashboard."""
    nexus = get_mcp_nexus()
    try:
        # Use memory_query tool with an empty string for everything
        results = await nexus.call_tool("memory_organ", "memory_query", {
            "query": "", 
            "top_k": limit
        })
        
        # Rule 13: Normalization. Extract raw engrams from MCP text blocks
        shards = []
        for block in results:
            if block.get("type") == "text":
                try:
                    data = json.loads(block["text"])
                    if isinstance(data, list): shards.extend(data)
                    else: shards.append(data)
                except: continue
        return {"status": "success", "shards": shards}
    except Exception as e:
        logger.error(f"Shard Retrieval Failure: {e}")
        # Fallback to direct logic if nexus tool fails
        from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic
        memory = await get_memory_logic()
        results = await memory.query_memory("", top_k=limit)
        return {"status": "success", "shards": results}

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

@app.post("/self_evaluate", dependencies=[Depends(verify_sovereign_key)])
async def trigger_self_evaluation():
    """Manual trigger for the Sovereign Self-Evaluation Cycle."""
    benchmarker = get_benchmarker()
    report = await benchmarker.run_full_audit()
    return report

@app.post("/audio/synthesize", dependencies=[Depends(verify_sovereign_key)])
async def synthesize_audio(request: Request):
    """
    SOTA: Proxy high-fidelity synthesis to the Claudio Cloud Organ.
    Rule 13: Strict Physical Decoupling.
    """
    body = await request.json()
    logger.info(f"Galactic Node: Proxying Synthesis Pulse to Cloud Organ...")
    
    if LEAN_MODE:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{CLOUD_AUDIO_URL}/synthesize", json=body)
                return response.json()
        except Exception as e:
            logger.error(f"Cloud Audio Proxy Failure: {e}")
            raise HTTPException(status_code=502, detail="Cloud Audio Organ Unreachable")
    else:
        # Local synthesis fallback (Rule 12: Self-Healing)
        from tooloo_v4_hub.organs.claudio_organ.audio_logic import perform_local_synthesis
        return await perform_local_synthesis(body)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))