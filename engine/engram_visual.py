# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining engram_visual.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.937056
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/engram_visual.py — Visual Engram generator.

Converts TooLoo pipeline execution state into a lightweight VisualEngram that
drives the multi-layer SVG frontend via CSS custom properties + client-side
CSS transitions and JS tweens.

The engram is a semantic control signal:
  • NOT pixel coordinates or SVG path instructions
  • Describes cognitive state: intent, confidence, mode, layer configs, colors
  • The browser's GPU interpolates from current visual state to new state

Visual layer architecture:
  Background (bg):  Ambient neural-net dot field — knowledge substrate
  Midground  (mg):  Live cognitive DAG graph (nodes + edges from /v2/dag)
  Foreground (fg):  Pipeline stage diagram (7 nodes with confidence arcs)

Sources (priority):
  1. Gemini live — concise vivid narrative (1 sentence, ≤ 12 words)
  2. Structured fallback — deterministic mapping (always offline-safe)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from engine.config import GEMINI_API_KEY, GEMINI_MODEL

if TYPE_CHECKING:
    from engine.jit_booster import JITBoostResult
    from engine.router import RouteResult
    from engine.tribunal import TribunalResult

# ── Gemini client ─────────────────────────────────────────────────────────────
_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        _gemini_client = _genai_mod.Client(api_key=GEMINI_API_KEY)
    except Exception:  # pragma: no cover
        pass

# ── Intent → visual palette ───────────────────────────────────────────────────
_PALETTE: dict[str, dict[str, str]] = {
    "BUILD":      {"primary": "#6C63FF", "secondary": "#9B8FFF", "glow": "rgba(108,99,255,0.55)",   "particle": "#c4bfff"},
    "DEBUG":      {"primary": "#F5A623", "secondary": "#FFD080", "glow": "rgba(245,166,35,0.55)",    "particle": "#ffe4a0"},
    "AUDIT":      {"primary": "#FF4757", "secondary": "#FF8592", "glow": "rgba(255,71,87,0.55)",     "particle": "#ffb3bb"},
    "DESIGN":     {"primary": "#00D2FF", "secondary": "#60E8FF", "glow": "rgba(0,210,255,0.55)",     "particle": "#a0f3ff"},
    "EXPLAIN":    {"primary": "#3498DB", "secondary": "#5DADE2", "glow": "rgba(52,152,219,0.55)",    "particle": "#a3d4f5"},
    "IDEATE":     {"primary": "#2ED573", "secondary": "#7BED9F", "glow": "rgba(46,213,115,0.55)",    "particle": "#adfdd0"},
    "SPAWN_REPO": {"primary": "#FFD700", "secondary": "#FFF176", "glow": "rgba(255,215,0,0.55)",     "particle": "#fff5b0"},
    "BLOCKED":    {"primary": "#888899", "secondary": "#aaaacc", "glow": "rgba(100,100,120,0.35)",   "particle": "#ccccdd"},
    "NONE":       {"primary": "#6C63FF", "secondary": "#9B8FFF", "glow": "rgba(108,99,255,0.25)",    "particle": "#c4bfff"},
}

_STAGE_NARRATIVES: dict[str, str] = {
    "idle":         "Cognitive field at rest — awaiting your mandate",
    "routing":      "Classifying intent across keyword topology",
    "boosting":     "JIT SOTA signals amplifying confidence",
    "auditing":     "Tribunal scanning for OWASP threat patterns",
    "planning":     "Topological sorter mapping execution waves",
    "scoping":      "Scope evaluator sizing the parallelism envelope",
    "executing":    "JIT executor fanning out cognitive threads",
    "refining":     "Refinement loop evaluating result fidelity",
    "blocked":      "Circuit breaker open — routing suspended",
    "conversation": "Conversational engine reasoning in context",
}

_NARRATIVE_PROMPT = (
    "You are TooLoo's visual cognition narrator. Write one vivid present-tense "
    "phrase (max 12 words, no punctuation, no quotes) describing what the AI "
    "is doing right now. "
    "intent={intent} confidence={confidence:.0%} mode={mode} clean={clean}. "
    "Be poetic and specific."
)


# ── DTOs ──────────────────────────────────────────────────────────────────────

@dataclass
class LayerConfig:
    opacity: float = 1.0
    scale: float = 1.0
    blur: float = 0.0
    translate_z: float = 0.0
    rotate_x: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "opacity": round(self.opacity, 3),
            "scale":   round(self.scale, 3),
            "blur":    round(self.blur, 2),
            "translate_z": round(self.translate_z, 1),
            "rotate_x":    round(self.rotate_x, 2),
        }


@dataclass
class VisualEngram:
    """
    Semantic control signal for the multi-layer SVG frontend.

    This is NOT a pixel or coordinate instruction. It describes the cognitive
    state of TooLoo's pipeline. The browser's CSS engine transitions smoothly
    from the current visual state to this new state.

    Fields
    ------
    mode         : pipeline phase (idle | routing | boosting | auditing |
                   planning | scoping | executing | refining | blocked |
                   conversation)
    focus_node   : which pipeline stage is currently highlighted
    intensity    : 0.0–1.0, derived from boosted confidence
    color_*      : palette colors for the intent (drive SVG CSS variables)
    pulse_rate   : Hz — focus node pulse speed
    layer_fg/mg/bg : parallax layer configs (opacity, scale, blur, z, rotateX)
    narrative    : concise description of cognitive state (Gemini or structured)
    """
    engram_id: str
    ts: str
    mode: str
    intent: str
    focus_node: str
    intensity: float
    color_primary: str
    color_secondary: str
    color_glow: str
    color_particle: str
    pulse_rate: float
    wave_count: int
    node_count: int
    tribunal_clear: bool
    signals: list[str]
    layer_fg: LayerConfig
    layer_mg: LayerConfig
    layer_bg: LayerConfig
    narrative: str
    source: str  # "gemini" | "structured"

    def to_dict(self) -> dict[str, Any]:
        return {
            "engram_id":       self.engram_id,
            "ts":              self.ts,
            "mode":            self.mode,
            "intent":          self.intent,
            "focus_node":      self.focus_node,
            "intensity":       round(self.intensity, 4),
            "color_primary":   self.color_primary,
            "color_secondary": self.color_secondary,
            "color_glow":      self.color_glow,
            "color_particle":  self.color_particle,
            "pulse_rate":      round(self.pulse_rate, 3),
            "wave_count":      self.wave_count,
            "node_count":      self.node_count,
            "tribunal_clear":  self.tribunal_clear,
            "signals":         self.signals,
            "layer_fg":        self.layer_fg.to_dict(),
            "layer_mg":        self.layer_mg.to_dict(),
            "layer_bg":        self.layer_bg.to_dict(),
            "narrative":       self.narrative,
            "source":          self.source,
        }


# ── Generator ─────────────────────────────────────────────────────────────────

class VisualEngramGenerator:
    """
    Generates VisualEngrams from pipeline execution state.

    Thread-safe: each call is stateless; _last is a simple cache for the
    ``current()`` convenience accessor.
    """

    def __init__(self) -> None:
        self._last: VisualEngram | None = None

    # ── Public surface ────────────────────────────────────────────────────────

    def idle(self) -> VisualEngram:
        """Emit an idle engram — cognitive field at rest, low intensity."""
        p = _PALETTE["BUILD"]
        engram = VisualEngram(
            engram_id=f"ve-{uuid.uuid4().hex[:8]}",
            ts=datetime.now(UTC).isoformat(),
            mode="idle", intent="NONE", focus_node="none",
            intensity=0.22,
            color_primary=p["primary"], color_secondary=p["secondary"],
            color_glow=p["glow"], color_particle=p["particle"],
            pulse_rate=0.22,
            wave_count=0, node_count=0,
            tribunal_clear=True, signals=[],
            layer_fg=LayerConfig(opacity=0.18, scale=0.93,
                                 blur=1.5, translate_z=60.0, rotate_x=4.0),
            layer_mg=LayerConfig(opacity=0.32, scale=1.0,
                                 blur=0.0, translate_z=0.0,  rotate_x=0.0),
            layer_bg=LayerConfig(opacity=0.70, scale=1.01,
                                 blur=0.0, translate_z=-40.0, rotate_x=-1.0),
            narrative=_STAGE_NARRATIVES["idle"],
            source="structured",
        )
        self._last = engram
        return engram

    def from_mandate(
        self,
        *,
        route: "RouteResult",
        jit_result: "JITBoostResult | None" = None,
        tribunal_result: "TribunalResult | None" = None,
        plan: list[list[str]] | None = None,
        scope: Any = None,
        refinement: Any = None,
    ) -> VisualEngram:
        """Generate a VisualEngram from a completed mandate pipeline run."""
        return self._build(
            route=route, jit_result=jit_result,
            tribunal_result=tribunal_result, plan=plan,
            scope=scope, refinement=refinement, is_chat=False,
        )

    def from_chat(
        self,
        *,
        route: "RouteResult",
        jit_result: "JITBoostResult | None" = None,
        tribunal_result: "TribunalResult | None" = None,
    ) -> VisualEngram:
        """Generate a VisualEngram from a chat pipeline run."""
        return self._build(
            route=route, jit_result=jit_result,
            tribunal_result=tribunal_result, is_chat=True,
        )

    def current(self) -> VisualEngram:
        """Return the most recent engram, or idle if none has been generated."""
        return self._last or self.idle()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build(
        self,
        *,
        route: "RouteResult",
        jit_result: "JITBoostResult | None",
        tribunal_result: "TribunalResult | None",
        plan: "list[list[str]] | None" = None,
        scope: Any = None,
        refinement: Any = None,
        is_chat: bool = False,
    ) -> VisualEngram:
        intent = route.intent
        confidence = jit_result.boosted_confidence if jit_result else route.confidence
        p = _PALETTE.get(intent, _PALETTE["BUILD"])
        tribunal_clear = tribunal_result.passed if tribunal_result else True

        # Determine pipeline mode from how far the pipeline has progressed
        if intent == "BLOCKED":
            mode, focus = "blocked", "router"
        elif is_chat:
            mode, focus = "conversation", "jit_booster"
        elif refinement is not None:
            mode, focus = "refining", "refinement"
        elif scope is not None:
            mode, focus = "scoping", "scope"
        elif plan is not None:
            mode, focus = "executing", "executor"
        elif not tribunal_clear:
            mode, focus = "auditing", "tribunal"
        elif jit_result is not None:
            mode, focus = "boosting", "jit_booster"
        else:
            mode, focus = "routing", "router"

        # Tribunal violation overrides focus regardless of pipeline stage
        if not tribunal_clear:
            mode, focus = "auditing", "tribunal"

        intensity = min(max(confidence, 0.0), 1.0)
        wave_count = len(plan) if plan else 0
        node_count = sum(len(w) for w in plan) if plan else 0
        signals = (jit_result.signals[:3] if jit_result else [])
        pulse_rate = self._pulse_rate(mode, intensity)
        layer_fg, layer_mg, layer_bg = self._layers(mode, intensity)
        narrative = self._narrative(intent, confidence, mode, tribunal_clear)

        engram = VisualEngram(
            engram_id=f"ve-{uuid.uuid4().hex[:8]}",
            ts=datetime.now(UTC).isoformat(),
            mode=mode, intent=intent, focus_node=focus,
            intensity=intensity,
            color_primary=p["primary"], color_secondary=p["secondary"],
            color_glow=p["glow"], color_particle=p["particle"],
            pulse_rate=pulse_rate,
            wave_count=wave_count, node_count=node_count,
            tribunal_clear=tribunal_clear, signals=signals,
            layer_fg=layer_fg, layer_mg=layer_mg, layer_bg=layer_bg,
            narrative=narrative, source="structured",
        )
        self._last = engram
        return engram

    def _pulse_rate(self, mode: str, intensity: float) -> float:
        base: dict[str, float] = {
            "idle": 0.22, "routing": 0.80, "boosting": 1.25,
            "auditing": 1.65, "planning": 0.90, "scoping": 0.90,
            "executing": 1.95, "refining": 0.60, "blocked": 0.12,
            "conversation": 0.65,
        }
        return round(base.get(mode, 0.5) * (0.7 + intensity * 0.6), 3)

    def _layers(
        self, mode: str, intensity: float,
    ) -> tuple[LayerConfig, LayerConfig, LayerConfig]:
        """Compute parallax layer configs based on pipeline mode and confidence."""
        if mode == "idle":
            return (
                LayerConfig(opacity=0.18, scale=0.93, blur=1.5,
                            translate_z=60.0,  rotate_x=4.0),
                LayerConfig(opacity=0.32, scale=1.0,  blur=0.0,
                            translate_z=0.0,   rotate_x=0.0),
                LayerConfig(opacity=0.70, scale=1.01, blur=0.0,
                            translate_z=-40.0, rotate_x=-1.0),
            )
        if mode == "blocked":
            return (
                LayerConfig(opacity=0.12, scale=0.87, blur=3.0,
                            translate_z=40.0,  rotate_x=7.0),
                LayerConfig(opacity=0.22, scale=0.93, blur=1.5,
                            translate_z=0.0,   rotate_x=2.5),
                LayerConfig(opacity=0.38, scale=0.97, blur=0.5,
                            translate_z=-40.0, rotate_x=0.0),
            )
        if mode in ("executing", "boosting"):
            s = 1.0 + intensity * 0.04
            return (
                LayerConfig(opacity=1.0,  scale=s,    blur=0.0,
                            translate_z=85.0,  rotate_x=0.0),
                LayerConfig(opacity=0.92, scale=1.0,  blur=0.0,
                            translate_z=0.0,   rotate_x=0.0),
                LayerConfig(opacity=0.28, scale=0.96, blur=1.0,
                            translate_z=-55.0, rotate_x=-2.0),
            )
        if mode == "auditing":
            return (
                LayerConfig(opacity=0.92, scale=1.0,  blur=0.0,
                            translate_z=72.0,  rotate_x=1.0),
                LayerConfig(opacity=0.78, scale=1.0,  blur=0.0,
                            translate_z=0.0,   rotate_x=0.0),
                LayerConfig(opacity=0.22, scale=0.96, blur=2.0,
                            translate_z=-48.0, rotate_x=-2.5),
            )
        # routing | planning | scoping | refining | conversation
        f = 0.52 + intensity * 0.48
        return (
            LayerConfig(opacity=f,    scale=1.0,  blur=0.0,
                        translate_z=68.0,  rotate_x=0.0),
            LayerConfig(opacity=0.72, scale=1.0,  blur=0.0,
                        translate_z=0.0,   rotate_x=0.0),
            LayerConfig(opacity=0.46, scale=1.0,  blur=0.0,
                        translate_z=-40.0, rotate_x=-1.0),
        )

    def _narrative(
        self, intent: str, confidence: float, mode: str, tribunal_clear: bool,
    ) -> str:
        """Generate narrative via Gemini when live, else deterministic fallback."""
        if _gemini_client:
            try:
                prompt = _NARRATIVE_PROMPT.format(
                    intent=intent, confidence=confidence,
                    mode=mode, clean=tribunal_clear,
                )
                resp = _gemini_client.models.generate_content(
                    model=GEMINI_MODEL, contents=prompt,
                )
                text = resp.text.strip().strip(".")
                if 3 <= len(text) <= 120:
                    return text
            except Exception:  # pragma: no cover
                pass
        # Structured fallback
        stage_text = _STAGE_NARRATIVES.get(
            mode, "Cognitive state transitioning")
        conf_str = (
            "high confidence" if confidence >= 0.85
            else "moderate confidence" if confidence >= 0.65
            else "low confidence"
        )
        tribunal_str = "" if tribunal_clear else " — tribunal violation detected"
        return f"{intent} at {conf_str}{tribunal_str} · {stage_text}"
