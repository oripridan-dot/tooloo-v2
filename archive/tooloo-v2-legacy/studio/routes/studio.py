"""
studio/routes/studio.py — AI Creation Studio V2 endpoints & WebSockets.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from engine.image_gen import ImageGenEngine
from engine.creative_director import CreativeDirector
from engine.prototype_gen import PrototypeGenEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["studio"])

_STATIC = Path(__file__).parent.parent / "static"

_image_gen_engine = ImageGenEngine()
_creative_director = CreativeDirector()
_prototype_gen_engine = PrototypeGenEngine()

_studio_sessions: dict[str, dict] = {}

def _new_session() -> dict:
    return {
        "phase": "discover",
        "history": [],
        "prototype_html": "",
        "iteration_count": 0,
    }

@router.get("/studio", response_class=HTMLResponse, include_in_schema=False)
async def serve_studio() -> HTMLResponse:
    html = (_STATIC / "studio_ui.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)

class StoryboardImageRequest(BaseModel):
    prompt: str

@router.get("/storyboard", response_class=HTMLResponse, include_in_schema=False)
async def serve_storyboard() -> HTMLResponse:
    html = (_STATIC / "storyboard.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)

@router.post("/v2/storyboard/image")
async def storyboard_image(req: StoryboardImageRequest) -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, _image_gen_engine.generate, req.prompt, "16:9", "cinematic"
    )
    if result.success:
        return {"image_base64": result.image_base64}
    return {"error": result.error}

@router.get("/v2/studio/styles")
async def studio_styles() -> dict[str, Any]:
    return {
        "styles": ImageGenEngine.available_styles(),
        "aspect_ratios": ImageGenEngine.available_aspect_ratios(),
    }

@router.websocket("/ws/studio")
async def ws_studio(ws: WebSocket) -> None:
    await ws.accept()
    session_id = f"studio-{uuid.uuid4().hex[:8]}"
    _studio_sessions[session_id] = _new_session()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "text": "Invalid JSON"})
                continue

            prompt = str(msg.get("text", "")).strip()
            if not prompt:
                await ws.send_json({"type": "error", "text": "Empty prompt"})
                continue

            session = _studio_sessions.get(session_id, _new_session())
            phase = session["phase"]
            history = session["history"]
            style = str(msg.get("style", "cinematic"))
            aspect_ratio = str(msg.get("aspect_ratio", "16:9"))

            if msg.get("action") == "phase_change" and msg.get("phase"):
                new_phase = str(msg["phase"])
                session["phase"] = new_phase
                session["iteration_count"] = 0
                await ws.send_json({
                    "type": "phase_change",
                    "phase": new_phase,
                    "reason": f"Moving to {new_phase} phase as requested.",
                })
                phase = new_phase

            history.append({"role": "user", "text": prompt})

            history_str = ""
            if len(history) > 1:
                history_str = "\n".join([f"{h['role']}: {h['text']}" for h in history[-8:]])

            t0 = time.monotonic()
            loop = asyncio.get_event_loop()

            await ws.send_json({"type": "status", "text": "Buddy is thinking..."})

            brief = await loop.run_in_executor(
                None, _creative_director.guide, prompt, phase, history_str, session["iteration_count"]
            )

            buddy_response = brief.get("response", "Let's keep going.")
            action = brief.get("action", "ask")
            enhanced_prompt = brief.get("enhanced_prompt", prompt)
            next_steps = brief.get("next_steps", "")

            await ws.send_json({"type": "chat", "text": buddy_response})
            history.append({"role": "assistant", "text": buddy_response})

            if action == "generate_image":
                await ws.send_json({"type": "status", "text": "Generating mockup..."})
                result = await loop.run_in_executor(
                    None, _image_gen_engine.generate, enhanced_prompt, aspect_ratio, style
                )
                if result.success:
                    await ws.send_json({
                        "type": "image",
                        "data": result.image_base64,
                        "aspect_ratio": result.aspect_ratio,
                        "style": result.style,
                    })
                else:
                    await ws.send_json({"type": "error", "text": f"Image generation failed: {result.error}"})
                session["iteration_count"] += 1

            elif action == "generate_prototype":
                await ws.send_json({"type": "status", "text": "Building interactive prototype..."})
                proto_result = await loop.run_in_executor(
                    None, _prototype_gen_engine.generate, enhanced_prompt, session.get("prototype_html", ""), history_str
                )
                if proto_result.success:
                    session["prototype_html"] = proto_result.html
                    await ws.send_json({"type": "prototype", "html": proto_result.html})
                else:
                    await ws.send_json({"type": "error", "text": f"Prototype generation failed: {proto_result.error}"})
                session["iteration_count"] += 1

            if brief.get("suggest_phase_change"):
                suggested = brief.get("suggested_phase", "")
                reason = brief.get("phase_reason", "")
                if suggested:
                    await ws.send_json({
                        "type": "phase_suggestion", "suggested_phase": suggested, "reason": reason
                    })

            if next_steps and action != "ask":
                await ws.send_json({"type": "chat", "text": next_steps})
                history.append({"role": "assistant", "text": next_steps})

            latency_ms = round((time.monotonic() - t0) * 1000, 2)
            await ws.send_json({
                "type": "done",
                "latency_ms": latency_ms,
                "session_id": session_id,
                "phase": session["phase"],
            })

            session["history"] = history
            _studio_sessions[session_id] = session

    except WebSocketDisconnect:
        _studio_sessions.pop(session_id, None)
    except Exception as exc:
        logger.exception("Studio WebSocket error: %s", exc)
        _studio_sessions.pop(session_id, None)
