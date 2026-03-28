# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining director.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.934311
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""engine/director.py — The Cinematic Director for TooLoo V2.

This component translates raw system events (DAG transitions, tool calls,
memory hits) into "Cinematic Mandates" (Mood, Camera, Narration) for the
frontend stage.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class CinematicState:
    mood: str = "idle"         # idle | thinking | executing | alert | success
    camera: str = "portrait"    # portrait | wide | closeup
    narration: str = ""        # Current subtitles
    intensity: float = 1.0     # Animation speed / glow intensity
    palette: str = "system_blue"

class Director:
    """The Director engine.

    Listens to system signals and computes the visual 'performance' for the UI.
    Uses a lookup-table for deterministic states by default, but can be
    extended with LLM-generated narration.
    """

    def __init__(self, broadcast_fn: Callable[[dict[str, Any]], None]):
        self._broadcast = broadcast_fn
        self._state = CinematicState()
        self._last_n_narration: list[str] = []

    def update_state(self, **kwargs):
        """Update the cinematic state and broadcast if changed."""
        changed = False
        for k, v in kwargs.items():
            if hasattr(self._state, k) and getattr(self._state, k) != v:
                setattr(self._state, k, v)
                changed = True
        
        if changed:
            self._broadcast({
                "type": "cinematic",
                "mood": self._state.mood,
                "camera": self._state.camera,
                "narration": self._state.narration,
                "intensity": self._state.intensity,
                "palette": self._state.palette
            })

    def narrate(self, text: str, mood: str | None = None):
        """Push a narration event with an optional mood shift."""
        if text == self._state.narration:
            return
            
        update = {"narration": text}
        if mood:
            update["mood"] = mood
            
        self.update_state(**update)

    def on_dag_transition(self, node_id: str, state: str):
        """Map DAG transitions to cinematic beats."""
        mapping = {
            "TRIBUNAL": ("thinking", "portrait", "Scanning for security constraints..."),
            "SCOPE": ("thinking", "wide", "Mapping the architectural scope..."),
            "EXECUTE": ("executing", "closeup", "Executing system mandates..."),
            "REFINE": ("thinking", "portrait", "Polishing the output..."),
            "SUCCESS": ("success", "portrait", "Mandate fulfilled."),
            "ERROR": ("alert", "closeup", "System block detected."),
        }

        # Simplistic node_id prefix matching
        for key, (mood, camera, text) in mapping.items():
            if key in node_id.upper():
                self.update_state(mood=mood, camera=camera, narration=text)
                return

    def on_bus_event(self, level: str, payload: dict[str, Any]):
        """Map generic bus events to cinematic mandates."""
        event_type = payload.get("type", "generic")
        
        # 1. Map System Events to Puppeteer States
        if event_type == "plan":
            self.update_state(mood="thinking", narration="Designing execution strategy...")
            self._broadcast({"type": "puppeteer", "action": "scanning"})
        elif event_type == "execution":
            self.update_state(mood="executing", narration="Fanning out DAG mandates...")
            self._broadcast({"type": "puppeteer", "action": "orbiting"})
        elif event_type == "tribunal_result":
            passed = payload.get("passed", True)
            if not passed:
                self.update_state(mood="alert", narration="Tribunal alert: Policy violation!")
                self._broadcast({"type": "puppeteer", "action": "rigid"})
        
        # 2. Level-based overrides
        if level == "CRITICAL":
            self.update_state(mood="alert", narration="System critical alert detected.")
            self._broadcast({"type": "puppeteer", "action": "rigid"})
        elif level == "MEMORY_HIT":
            self.narrate("Refining with persistent context...", mood="thinking")
        elif level == "JIT_BOOST":
            self.narrate("Injecting SOTA signals...", mood="thinking")

    def handle_cognitive_state(self, mood: str, load: str):
        """Map CognitiveLens states to buddy animations (Puppeteer)."""
        self._broadcast({
            "type": "puppeteer",
            "action": "cognitive_shift",
            "mood": mood,
            "load": load,
            "narration": f"Buddy state: {mood.upper()} // Load: {load.upper()}"
        })
