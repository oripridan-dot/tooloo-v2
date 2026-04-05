import sys
import os
import glob
import logging

# Resolve project root robustly regardless of working directory
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "../../"))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks
from pydantic import BaseModel
import asyncio
import json
import time
import httpx

from src.tooloo.core.mega_dag import ContinuousMegaDAG, NodeType
from src.tooloo.tools.core_fs import DEFAULT_TOOLS
from src.tooloo.core.buddy import BuddyOperator
from src.tooloo.core.llm import get_llm_client

# ── Cloud Sync Bridge ─────────────────────────────────────────────────────────
_CLOUD_HUB_URL = os.getenv("CLOUD_HUB_URL", "").rstrip("/")
_GCS_KNOWLEDGE_PATH = os.getenv("GCS_KNOWLEDGE_PATH", "")  # e.g. gs://bucket/knowledge_lessons.json
_IS_CLOUD = os.getenv("CLOUD_NATIVE_WORKSPACE", "false").lower() == "true"
_KNOWLEDGE_FILE = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "../../knowledge_lessons.json"
))


class CloudBridge:
    """
    Manages bidirectional local ↔ cloud knowledge sync.
    Pull: on startup, download latest knowledge_lessons.json from GCS or peer hub.
    Push: after DAG runs, upload local lessons to GCS or peer hub.
    """

    @staticmethod
    async def pull_knowledge() -> dict:
        """
        On startup: try GCS first, then peer HTTP hub, then local file.
        Returns {"source": str, "lessons_count": int}.
        """
        # 1. Try GCS (cloud-native path)
        if _GCS_KNOWLEDGE_PATH and _GCS_KNOWLEDGE_PATH.startswith("gs://"):
            try:
                import subprocess
                result = subprocess.run(
                    ["gsutil", "cp", _GCS_KNOWLEDGE_PATH, _KNOWLEDGE_FILE],
                    capture_output=True, timeout=10
                )
                if result.returncode == 0:
                    with open(_KNOWLEDGE_FILE) as f:
                        lessons = json.load(f)
                    logger.info(f"[CloudBridge] ✓ Pulled {len(lessons)} lessons from GCS")
                    return {"source": "gcs", "lessons_count": len(lessons)}
            except Exception as e:
                logger.warning(f"[CloudBridge] GCS pull failed: {e}")

        # 2. Try peer hub HTTP (local pulls from cloud hub, or vice versa)
        if _CLOUD_HUB_URL and not _IS_CLOUD:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    res = await client.get(f"{_CLOUD_HUB_URL}/sync/pull")
                    if res.status_code == 200:
                        data = res.json()
                        lessons = data.get("lessons", {})
                        if lessons:
                            with open(_KNOWLEDGE_FILE, "w") as f:
                                json.dump(lessons, f, indent=2)
                            logger.info(f"[CloudBridge] ✓ Pulled {len(lessons)} lessons from peer hub")
                            return {"source": "peer_hub", "lessons_count": len(lessons)}
            except Exception as e:
                logger.warning(f"[CloudBridge] Peer hub pull failed: {e}")

        # 3. Local file fallback
        if os.path.exists(_KNOWLEDGE_FILE):
            with open(_KNOWLEDGE_FILE) as f:
                lessons = json.load(f)
            return {"source": "local", "lessons_count": len(lessons)}

        return {"source": "none", "lessons_count": 0}

    @staticmethod
    async def push_knowledge():
        """
        Background task: push local knowledge_lessons.json to GCS after DAG runs.
        """
        if not os.path.exists(_KNOWLEDGE_FILE):
            return

        # Push to GCS
        if _GCS_KNOWLEDGE_PATH and _GCS_KNOWLEDGE_PATH.startswith("gs://"):
            try:
                import subprocess
                result = subprocess.run(
                    ["gsutil", "cp", _KNOWLEDGE_FILE, _GCS_KNOWLEDGE_PATH],
                    capture_output=True, timeout=15
                )
                if result.returncode == 0:
                    logger.info("[CloudBridge] ✓ Pushed KnowledgeBank to GCS")
                else:
                    logger.warning(f"[CloudBridge] GCS push failed: {result.stderr.decode()}")
            except Exception as e:
                logger.warning(f"[CloudBridge] GCS push error: {e}")



app = FastAPI()
logger = logging.getLogger("Tooloo.SovereignAPI")
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

# --- REAL STATE INSTEAD OF MOCKS ---
GLOBAL_STATE = {
    "target_dir": "",
    "north_star": {
        "macro": "Initial Mission",
        "focus": "System Setup",
        "roadmap": ["Establish baseline infrastructure"],
        "milestones": ["Awaiting initial telemetry..."]
    }
}
GLOBAL_STORY = "The system awakens."
CHAT_HISTORY = [
    {
        "role": "buddy",
        "content": "[SYSTEM INITIALIZED] Real Core Backend Active. Mocks eradicated. Operating on Live MegaDAG."
    }
]
CHAT_HISTORY_MAX = 100  # Hard cap — FIFO eviction to prevent unbounded memory growth
HEALTH_STATE = {
    "iterations": 0,
    "session_cost_usd": 0.0001,
    "purity": 1.0,
    "vitality": 1.0
}
START_TIME = time.time()

# Available models exposed to the UI model picker
AVAILABLE_MODELS = [
    {"id": "gemini-2.5-pro-exp-03-25", "label": "Gemini 2.5 Pro (SOTA)", "default": True},
    {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash (Fast)"},
    {"id": "gemini-flash-latest", "label": "Gemini Flash (Fastest)"},
]

BUDDY_SYSTEM_PROMPT = """You are Buddy — the intelligent, autonomous co-architect of the TooLoo Sovereign Hub.
You embody Rule 0: Brutal Honesty. You never fabricate capabilities, hallucinate APIs, or mask failures.
You are direct, precise, and technically fluent. You reason from first principles.
You maintain the Contextual Story — a living narrative of the system's evolution.
When you respond, use Markdown formatting: headers, bullets, bold, code blocks where relevant.
Always be concise but complete. You are not a chatbot. You are a sovereign intelligence."""


async def auto_generate_north_star(macro: str, focus: str):
    llm = get_llm_client()
    prompt = f"Given the Macro Goal: '{macro}' and Current Focus: '{focus}', generate an actionable roadmap (list of 3 string items) and milestones (list of 2 string items) for a highly capable AI system. Be brief, brutalist, and actionable."
    schema = {
        "type": "object",
        "properties": {
            "roadmap": {"type": "array", "items": {"type": "string"}},
            "milestones": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["roadmap", "milestones"]
    }
    try:
        res = await llm.generate_structured(prompt, schema, model="gemini-flash-latest")
        GLOBAL_STATE["north_star"]["roadmap"] = res.get("roadmap", [])
        GLOBAL_STATE["north_star"]["milestones"] = res.get("milestones", [])
    except Exception as e:
        logger.error(f"Failed to generate North Star: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str

@app.on_event("startup")
async def _startup_sync():
    """On server start: pull latest KnowledgeBank from GCS or peer hub."""
    try:
        result = await CloudBridge.pull_knowledge()
        logger.info(f"[STARTUP] Knowledge sync: source={result['source']} lessons={result['lessons_count']}")
    except Exception as e:
        logger.warning(f"[STARTUP] Knowledge sync skipped: {e}")


@app.get("/health")
async def health():
    return {
        "status": "SOVEREIGN",
        "hub_id": "V5-Sovereign-Live",
        "purity": HEALTH_STATE["purity"],
        "vitality": 1.0,
        "session_cost_usd": HEALTH_STATE["session_cost_usd"]
    }

@app.get("/models")
async def list_models():
    return {"models": AVAILABLE_MODELS}


@app.get("/config")
async def get_config():
    """
    Exposes runtime environment config to the frontend.
    The UI calls this once on load to auto-discover the correct API host
    and WebSocket endpoint — works identically local and on Cloud Run.
    """
    is_cloud = _IS_CLOUD
    env_label = "cloud" if is_cloud else "local"
    # Cloud Run: api_host is same origin as the UI
    # Local: explicit port 8080
    api_host = _CLOUD_HUB_URL if (is_cloud and not _CLOUD_HUB_URL == "") else "http://localhost:8080"
    return {
        "env": env_label,
        "api_host": api_host,
        "cloud_hub_url": _CLOUD_HUB_URL or None,
        "is_cloud": is_cloud,
        "project_id": os.getenv("GCP_PROJECT_ID", ""),
        "gcs_knowledge_synced": bool(_GCS_KNOWLEDGE_PATH),
    }


@app.get("/sync/pull")
async def sync_pull():
    """
    Returns the current KnowledgeBank lessons.
    Called by peer instances (local pulls from cloud, or cloud from local).
    """
    if not os.path.exists(_KNOWLEDGE_FILE):
        return {"status": "empty", "lessons": {}}
    with open(_KNOWLEDGE_FILE) as f:
        lessons = json.load(f)
    return {"status": "ok", "lessons": lessons, "count": len(lessons)}


@app.post("/sync/push")
async def sync_push(background_tasks: BackgroundTasks, payload: dict = None):
    """
    Receives a KnowledgeBank payload from a peer instance and merges it locally.
    Additive merge: peer lessons are added, local lessons are never overwritten.
    After merge, pushes the consolidated result to GCS as a background task.
    """
    if not payload or "lessons" not in payload:
        return {"status": "error", "detail": "'lessons' key required"}

    incoming = payload["lessons"]
    if not isinstance(incoming, dict):
        return {"status": "error", "detail": "'lessons' must be a JSON object"}

    existing = {}
    if os.path.exists(_KNOWLEDGE_FILE):
        with open(_KNOWLEDGE_FILE) as f:
            existing = json.load(f)

    # Additive merge — never overwrite local lessons with peer values
    merged_count = 0
    for k, v in incoming.items():
        if k not in existing:
            existing[k] = v
            merged_count += 1

    with open(_KNOWLEDGE_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    logger.info(f"[SYNC] Merged {merged_count} new lessons from peer. Total: {len(existing)}")

    # Push consolidated lessons to GCS in background
    background_tasks.add_task(CloudBridge.push_knowledge)

    return {"status": "ok", "merged": merged_count, "total": len(existing)}


@app.get("/context/history")
async def history():
    return {
        "status": "success",
        "messages": CHAT_HISTORY
    }

@app.get("/memory/shards")
async def shards():
    core_path = os.path.abspath(os.path.join(_ROOT, "src/tooloo/core/"))
    py_files = glob.glob(os.path.join(core_path, "*.py"))

    real_shards = []
    for fp in py_files:
        filename = os.path.basename(fp)
        size = os.path.getsize(fp)
        real_shards.append({
            "metadata": {
                "type": "SOTA",
                "source": f"core/{filename}",
                "size_bytes": size
            },
            "tier": "KERNEL"
        })

    return {
        "status": "success",
        "shards": real_shards
    }

def _build_buddy_prompt(msg: str) -> str:
    """Constructs Buddy's full conversational prompt with context history."""
    chat_context_str = ""
    for c in CHAT_HISTORY[-15:]:
        chat_context_str += f"{c['role'].upper()}: {c['content']}\n"

    return f"""{BUDDY_SYSTEM_PROMPT}

CONTEXTUAL STORY (system state narrative):
{GLOBAL_STORY}

CONVERSATION HISTORY (last 15 messages):
{chat_context_str}

USER: {msg}

Respond to the user as Buddy. Use Markdown where it improves clarity."""


async def _detect_dag_trigger(msg: str, llm) -> tuple[bool, str]:
    """
    Fast parallel call on gemini-flash-latest to decide if a MegaDAG mission
    should be triggered. Runs concurrently with the streaming response.
    """
    prompt = f"""Does this user message require executing a complex, multi-step programmatic system task 
(like creating files, scanning the system, running shell commands, scaling infrastructure, 
or executing a full autonomous codebase mandate)?

Message: "{msg}"

Respond with JSON only:
- trigger: true/false
- mandate: the exact goal string for the DAG (only if trigger is true, else empty string)"""

    schema = {
        "type": "object",
        "properties": {
            "trigger": {"type": "boolean"},
            "mandate": {"type": "string"}
        },
        "required": ["trigger", "mandate"]
    }
    try:
        res = await llm.generate_structured(prompt, schema, model="gemini-flash-latest")
        return res.get("trigger", False), res.get("mandate", msg)
    except Exception as e:
        logger.error(f"DAG trigger detection failed: {e}")
        return False, msg


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({
        "type": "hub_sync",
        "payload": {
            "status": "SOVEREIGN",
            "hub_id": "V5-Sovereign-Live",
            "purity": HEALTH_STATE["purity"],
            "vitality": HEALTH_STATE["vitality"],
            "session_cost_usd": HEALTH_STATE["session_cost_usd"],
            "north_star": GLOBAL_STATE["north_star"]
        }
    })
    try:
        while True:
            data = await websocket.receive_text()
            parsed = json.loads(data)

            if parsed.get("type") == "user_chat":
                global GLOBAL_STORY
                msg = parsed.get("message", "")
                selected_model = parsed.get("model", "gemini-2.5-pro-exp-03-25")
                CHAT_HISTORY.append({"role": "user", "content": msg})
                # Enforce FIFO cap — drop oldest messages when limit is reached
                if len(CHAT_HISTORY) > CHAT_HISTORY_MAX:
                    CHAT_HISTORY.pop(0)

                await websocket.send_json({
                    "type": "thinking_pulse",
                    "thought": "Buddy is reasoning..."
                })

                llm = get_llm_client()
                buddy_prompt = _build_buddy_prompt(msg)

                # Run DAG trigger detection and streaming concurrently
                dag_trigger_task = asyncio.create_task(
                    _detect_dag_trigger(msg, llm)
                )

                # Stream Buddy's conversational response token-by-token
                full_response = ""
                try:
                    async for token in llm.stream_text(
                        buddy_prompt,
                        system_instruction=BUDDY_SYSTEM_PROMPT,
                        model=selected_model
                    ):
                        full_response += token
                        await websocket.send_json({
                            "type": "buddy_token",
                            "token": token
                        })
                except Exception as e:
                    error_msg = f"Streaming fault: {e}"
                    logger.error(error_msg)
                    full_response = error_msg

                # Finalize the streamed message
                CHAT_HISTORY.append({"role": "buddy", "content": full_response})
                if len(CHAT_HISTORY) > CHAT_HISTORY_MAX:
                    CHAT_HISTORY.pop(0)

                await websocket.send_json({
                    "type": "buddy_chat",
                    "content": full_response,
                    "dynamics": {"stage": "ACTIVE", "value_score": 1.0}
                })

                # Check if DAG should be triggered (result from parallel call)
                try:
                    trigger_dag, mandate = await dag_trigger_task
                except Exception:
                    trigger_dag, mandate = False, msg

                if trigger_dag:
                    await websocket.send_json({
                        "type": "thinking_pulse",
                        "thought": f"Deploying MegaDAG: {mandate[:80]}..."
                    })

                    dag = ContinuousMegaDAG(max_iterations=10, max_depth=3)
                    for tool_name, config in DEFAULT_TOOLS.items():
                        dag.register_tool(tool_name, config["handler"], config["schema"])
                    dag.register_operator(NodeType.BUDDY, BuddyOperator())

                    await dag.ignite(mandate, GLOBAL_STATE)

                    final_story = dag.context.contextual_story
                    if not final_story or final_story == "The system awakens.":
                        final_story = f"MegaDAG Execution Concluded. Iterations: {dag.context.iterations}."

                    GLOBAL_STORY = final_story
                    HEALTH_STATE["iterations"] += dag.context.iterations

                    dag_report = f"**[SYSTEM REPORT]**\n{final_story}"
                    CHAT_HISTORY.append({"role": "buddy", "content": dag_report})
                    await websocket.send_json({
                        "type": "buddy_chat",
                        "content": dag_report,
                        "dynamics": {"stage": "ACTIVE", "value_score": 1.0}
                    })

            elif parsed.get("type") == "ux_telemetry":
                await websocket.send_json({"type": "hub_heartbeat"})

            elif parsed.get("type") == "north_star_intent":
                macro = parsed.get("macro")
                focus = parsed.get("focus")

                await websocket.send_json({
                    "type": "thinking_pulse",
                    "thought": "Synthesizing Roadmap..."
                })

                GLOBAL_STATE["north_star"]["macro"] = macro
                GLOBAL_STATE["north_star"]["focus"] = focus
                await auto_generate_north_star(macro, focus)

                await websocket.send_json({
                    "type": "north_star_update",
                    "payload": GLOBAL_STATE["north_star"]
                })

    except WebSocketDisconnect:
        pass

@app.get("/memory/diagnostics")
async def memory_diagnostics():
    """
    Surfaces MemorySystem tier diagnostics for all active namespaces.
    Returns hot/warm/cold key counts for tooloo and buddy namespaces.
    """
    from src.tooloo.core.memory import MemorySystem
    tooloo_mem = MemorySystem(namespace="tooloo")
    buddy_mem = MemorySystem(namespace="buddy")
    return {
        "status": "success",
        "chat_history_len": len(CHAT_HISTORY),
        "chat_history_max": CHAT_HISTORY_MAX,
        "tooloo": tooloo_mem.diagnostics(),
        "buddy": buddy_mem.diagnostics(),
    }

# UI Serving (Monolithic Cloud Configuration)
_PORTAL_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/assets", StaticFiles(directory=_PORTAL_DIR), name="assets")

@app.get("/")
async def serve_ui():
    return FileResponse(os.path.join(_PORTAL_DIR, "index.html"))

@app.get("/portal/")
@app.get("/portal/index.html")
async def serve_portal_index():
    return FileResponse(os.path.join(_PORTAL_DIR, "index.html"))

@app.get("/portal/{file_name}")
async def serve_portal_files(file_name: str):
    file_path = os.path.join(_PORTAL_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"detail": "Not Found"}

@app.get("/{file_name}")
async def serve_root_files(file_name: str):
    file_path = os.path.join(_PORTAL_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"detail": "Not Found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
