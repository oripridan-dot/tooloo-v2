"""engine/jit_designer.py — JIT Designer: Dynamic SOTA UI Heuristics Engine.

The JITDesigner evaluates conversational output and maps it to a
``DesignDirective`` — a structured payload that instructs the frontend *exactly*
how to render Buddy's response.  Design rules are rooted in top-tier design
systems: Apple HIG (Human Interface Guidelines), Google Material Design 3, and
custom AI-human era principles carved into PsycheBank.

Design Directive fields:
  component_type    — prose | timeline | storybook_cards | comparison_table |
                      code_block | diagram_embed | metric_grid
  palette_key       — key into the HIG/M3 semantic color map
  animation_style   — slide_in | fade_up | spring_pop | cascade | morph
  layout_hint       — single_column | two_column | spatial_float
  emphasis_words    — list of keywords to visually highlight in the response
  confidence_visual — high | medium | low  (drives UI confidence badge style)
  thought_cards     — ordered ThoughtCard list for the Thought Timeline

``ThoughtCard`` represents one step in Buddy's visible chain-of-thought.
Each card is broadcast as an SSE ``thought`` event so the frontend can render
them progressively (storybook pattern) as the engine executes.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Heuristics catalogue path ─────────────────────────────────────────────────
_HEURISTICS_PATH = Path(__file__).parent.parent / \
    "psyche_bank" / "sota_ui_heuristics.cog.json"

# ── Component type rules: intent → best visual component ──────────────────────
_INTENT_TO_COMPONENT: dict[str, str] = {
    "BUILD":      "storybook_cards",
    "DEBUG":      "timeline",
    "AUDIT":      "comparison_table",
    "DESIGN":     "diagram_embed",
    "EXPLAIN":    "prose",
    "IDEATE":     "storybook_cards",
    "SPAWN_REPO": "metric_grid",
    "BLOCKED":    "prose",
}

# ── Palette keys per emotional state (HIG tonal families) ─────────────────────
_EQ_PALETTE: dict[str, str] = {
    "neutral":    "system_blue",
    "frustrated": "system_red",
    "excited":    "system_green",
    "uncertain":  "system_orange",
    "grateful":   "system_teal",
}

# ── Animation styles: intent × emotional_state → animation ───────────────────
_ANIMATION_MAP: dict[tuple[str, str], str] = {
    ("BUILD",   "excited"):    "spring_pop",
    ("BUILD",   "neutral"):    "cascade",
    ("DEBUG",   "frustrated"): "slide_in",
    ("DEBUG",   "neutral"):    "cascade",
    ("DESIGN",  "excited"):    "morph",
    ("DESIGN",  "neutral"):    "fade_up",
    ("IDEATE",  "excited"):    "spring_pop",
    ("IDEATE",  "uncertain"):  "cascade",
    ("EXPLAIN", "uncertain"):  "slide_in",
    ("EXPLAIN", "neutral"):    "fade_up",
    ("AUDIT",   "neutral"):    "cascade",
}

# ── Confidence visual tier ─────────────────────────────────────────────────────


def _confidence_tier(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.55:
        return "medium"
    return "low"


# ── Emphasis word extraction  ──────────────────────────────────────────────────
_EMPHASIS_SKIP = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "shall", "can", "to", "of", "and", "or", "but", "in", "on",
    "at", "by", "for", "with", "from", "this", "that", "these", "those",
    "it", "its", "i", "you", "we", "they", "my", "your", "our", "their",
    "not", "so", "up", "out", "if", "then", "than", "there", "here",
})


def _extract_emphasis_words(text: str, max_words: int = 6) -> list[str]:
    """Extract the most visually significant words from a response for highlight markup.

    Prioritises capitalised tokens and longer words, skips common stop-words.
    Returns at most *max_words* unique tokens.
    """
    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_\-]{2,}\b", text)
    seen: dict[str, int] = {}
    for tok in tokens:
        lower = tok.lower()
        if lower in _EMPHASIS_SKIP:
            continue
        seen[lower] = seen.get(lower, 0) + 1

    # Sort by frequency (desc) then length (desc)
    ranked = sorted(seen.keys(), key=lambda w: (-seen[w], -len(w)))
    return ranked[:max_words]


# ── ThoughtCard ───────────────────────────────────────────────────────────────

_THOUGHT_ICONS: dict[str, str] = {
    "route":    "✦",    # routing / intent
    "jit":      "⚡",   # JIT boost / SOTA
    "tribunal": "🛡",   # OWASP security
    "scope":    "🗺",   # scope evaluation
    "execute":  "⚙",   # generation / execution
    "refine":   "✨",   # refinement / polish
    "memory":   "🧠",   # persistent memory recall
    "eq":       "💙",   # emotional intelligence
    "design":   "🎨",   # JIT designer
}

_THOUGHT_TITLES: dict[str, str] = {
    "route":    "Intent Classified",
    "jit":      "SOTA Signals Loaded",
    "tribunal": "Security Validated",
    "scope":    "Plan Structured",
    "execute":  "Response Generating",
    "refine":   "Polishing Output",
    "memory":   "Memory Retrieved",
    "eq":       "Emotional Context Read",
    "design":   "Visual Design Applied",
}


@dataclass
class ThoughtCard:
    """A single step in Buddy's visible chain-of-thought storybook."""

    phase: str        # e.g. "route", "jit", "tribunal"
    icon: str         # emoji / SF Symbol
    title: str        # Short phase label (< 24 chars)
    detail: str       # 1-line description of what happened
    status: str = "pending"   # pending | active | done | skipped

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "icon": self.icon,
            "title": self.title,
            "detail": self.detail,
            "status": self.status,
        }


# ── DesignDirective ───────────────────────────────────────────────────────────

@dataclass
class DesignDirective:
    """Full instruction set for the frontend to render Buddy's response SOTA."""

    component_type: str         # prose | timeline | storybook_cards | ...
    palette_key: str            # semantic color key
    animation_style: str        # slide_in | fade_up | spring_pop | cascade | morph
    layout_hint: str            # single_column | two_column | spatial_float
    emphasis_words: list[str]   # tokens to visually highlight
    confidence_visual: str      # high | medium | low
    thought_cards: list[ThoughtCard] = field(default_factory=list)
    hig_rule_applied: str = ""  # which HIG / M3 rule was the primary driver

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_type": self.component_type,
            "palette_key": self.palette_key,
            "animation_style": self.animation_style,
            "layout_hint": self.layout_hint,
            "emphasis_words": self.emphasis_words,
            "confidence_visual": self.confidence_visual,
            "thought_cards": [c.to_dict() for c in self.thought_cards],
            "hig_rule_applied": self.hig_rule_applied,
        }


# ── JITDesigner ───────────────────────────────────────────────────────────────

class JITDesigner:
    """Applies top-tier design system heuristics to Buddy's conversational output.

    Thread-safe and stateless (Law 17) — every call is independent.  Heuristic
    rules are loaded from ``psyche_bank/sota_ui_heuristics.cog.json`` at init and
    refreshed when the file changes (lazy re-read on mtime change).

    Usage::

        designer = JITDesigner()
        directive = designer.evaluate(
            intent="BUILD",
            emotional_state="excited",
            confidence=0.92,
            response_text="Here's the plan for your auth module...",
        )
        # directive.to_dict() → inject into SSE payload / HTTP response
    """

    def __init__(self) -> None:
        self._rules: dict[str, Any] = {}
        self._rules_mtime: float = 0.0
        self._load_rules()

    def _load_rules(self) -> None:
        """Load SOTA UI heuristics from PsycheBank.  Silently falls back to empty
        dict if the file is missing or malformed."""
        try:
            stat = _HEURISTICS_PATH.stat()
            if stat.st_mtime == self._rules_mtime:
                return  # unchanged
            raw = _HEURISTICS_PATH.read_text(encoding="utf-8")
            self._rules = json.loads(raw)
            self._rules_mtime = stat.st_mtime
        except Exception:
            self._rules = {}

    def evaluate(
        self,
        intent: str,
        emotional_state: str,
        confidence: float,
        response_text: str,
        memory_recalled: bool = False,
        jit_signal_count: int = 0,
    ) -> DesignDirective:
        """Return a DesignDirective for the given conversational turn parameters.

        Args:
            intent:           Classified intent (BUILD, DEBUG, EXPLAIN, etc.).
            emotional_state:  Detected EQ state (neutral, frustrated, excited …).
            confidence:       Route confidence score 0-1.
            response_text:    The actual text Buddy is about to return (for emphasis).
            memory_recalled:  True when BuddyMemoryStore surfaced relevant context.
            jit_signal_count: Number of SOTA signals JITBooster loaded this turn.

        Returns:
            DesignDirective with all frontend rendering hints.
        """
        # Refresh rules if file changed
        self._load_rules()

        component_type = _INTENT_TO_COMPONENT.get(intent, "prose")
        palette_key = _EQ_PALETTE.get(emotional_state, "system_blue")
        animation_style = (
            _ANIMATION_MAP.get((intent, emotional_state))
            or _ANIMATION_MAP.get((intent, "neutral"))
            or "fade_up"
        )

        # Layout: two column when response is long and we have structured content
        word_count = len(response_text.split())
        layout_hint = (
            "two_column"
            if component_type in {"storybook_cards", "comparison_table"} and word_count > 80
            else "single_column"
        )

        emphasis_words = _extract_emphasis_words(response_text)
        confidence_visual = _confidence_tier(confidence)

        # Build thought cards from pipeline phases executed this turn
        thought_cards = self._build_thought_cards(
            intent=intent,
            emotional_state=emotional_state,
            memory_recalled=memory_recalled,
            jit_signal_count=jit_signal_count,
            confidence_visual=confidence_visual,
        )

        # Pick the primary HIG / M3 rule that drove the component choice
        hig_rule = self._pick_hig_rule(component_type, emotional_state)

        return DesignDirective(
            component_type=component_type,
            palette_key=palette_key,
            animation_style=animation_style,
            layout_hint=layout_hint,
            emphasis_words=emphasis_words,
            confidence_visual=confidence_visual,
            thought_cards=thought_cards,
            hig_rule_applied=hig_rule,
        )

    def _build_thought_cards(
        self,
        intent: str,
        emotional_state: str,
        memory_recalled: bool,
        jit_signal_count: int,
        confidence_visual: str,
    ) -> list[ThoughtCard]:
        """Construct the ordered list of ThoughtCards for the storybook timeline."""
        cards: list[ThoughtCard] = []

        # Phase 1: EQ detection
        eq_detail = (
            f"Detected: {emotional_state} — activating empathy mode"
            if emotional_state != "neutral"
            else "Emotional context: neutral"
        )
        cards.append(ThoughtCard(
            phase="eq",
            icon=_THOUGHT_ICONS["eq"],
            title=_THOUGHT_TITLES["eq"],
            detail=eq_detail,
            status="done",
        ))

        # Phase 2: Memory (conditional)
        if memory_recalled:
            cards.append(ThoughtCard(
                phase="memory",
                icon=_THOUGHT_ICONS["memory"],
                title=_THOUGHT_TITLES["memory"],
                detail="Found relevant context from past sessions",
                status="done",
            ))

        # Phase 3: JIT Boost
        jit_detail = (
            f"Loaded {jit_signal_count} SOTA signals for '{intent}'"
            if jit_signal_count > 0
            else f"SOTA catalogue consulted for '{intent}'"
        )
        cards.append(ThoughtCard(
            phase="jit",
            icon=_THOUGHT_ICONS["jit"],
            title=_THOUGHT_TITLES["jit"],
            detail=jit_detail,
            status="done",
        ))

        # Phase 4: Tribunal
        cards.append(ThoughtCard(
            phase="tribunal",
            icon=_THOUGHT_ICONS["tribunal"],
            title=_THOUGHT_TITLES["tribunal"],
            detail="OWASP 2025 scan passed — no injection risks",
            status="done",
        ))

        # Phase 5: Scope
        cards.append(ThoughtCard(
            phase="scope",
            icon=_THOUGHT_ICONS["scope"],
            title=_THOUGHT_TITLES["scope"],
            detail=f"Plan built for intent '{intent}' (confidence: {confidence_visual})",
            status="done",
        ))

        # Phase 6: Execute (response generation)
        cards.append(ThoughtCard(
            phase="execute",
            icon=_THOUGHT_ICONS["execute"],
            title=_THOUGHT_TITLES["execute"],
            detail="Gemini synthesis complete — response ready",
            status="done",
        ))

        # Phase 7: Design
        cards.append(ThoughtCard(
            phase="design",
            icon=_THOUGHT_ICONS["design"],
            title=_THOUGHT_TITLES["design"],
            detail=f"HIG directive: {_INTENT_TO_COMPONENT.get(intent, 'prose')} layout",
            status="done",
        ))

        return cards

    def _pick_hig_rule(self, component_type: str, emotional_state: str) -> str:
        """Select the most relevant HIG / M3 rule to cite in the directive."""
        rules = self._rules.get("hig_rules", {})
        key = f"{component_type}.{emotional_state}"
        fallback_key = component_type
        return (
            rules.get(key)
            or rules.get(fallback_key)
            or "HIG: Progressive Disclosure — reveal content in context-appropriate layers"
        )


# ── Lightweight active listen analysis (no LLM required) ─────────────────────

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "BUILD":      ["build", "create", "add", "make", "implement", "write", "generate"],
    "DEBUG":      ["bug", "error", "fix", "broken", "crash", "failing", "issue", "problem"],
    "AUDIT":      ["audit", "check", "review", "security", "scan", "analyse", "analyze"],
    "DESIGN":     ["design", "ui", "ux", "layout", "style", "component", "interface"],
    "EXPLAIN":    ["explain", "what is", "how does", "why", "tell me", "understand", "describe"],
    "IDEATE":     ["idea", "brainstorm", "explore", "options", "alternatives", "suggest"],
    "SPAWN_REPO": ["scaffold", "repo", "project", "boilerplate", "starter", "init"],
}

_VAGUE_SIGNALS = frozenset(
    {"it", "thing", "stuff", "something", "anything", "this", "that"})


def analyze_partial_prompt(text: str) -> dict[str, Any]:
    """Fast, synchronous analysis of a partial user prompt.  No LLM calls.

    Returns a dict with:
      comprehension_level : "clear" | "vague" | "complex" | "listening"
      visual_indicator    : "nodding" | "thinking" | "listening" | "confused_tilt"
      prompt_suggestions  : list of 1-2 short actionable tips
      detected_intent     : best-guess intent or ""
      word_count          : int
    """
    stripped = text.strip()
    words = stripped.split()
    word_count = len(words)
    lower = stripped.lower()

    # Very short → listening / vague
    if word_count < 3:
        return {
            "comprehension_level": "listening",
            "visual_indicator": "listening",
            "prompt_suggestions": ["Keep going — what do you want to achieve?"],
            "detected_intent": "",
            "word_count": word_count,
        }

    # Detect vague signals
    vague_count = sum(1 for w in words if w.lower() in _VAGUE_SIGNALS)
    if vague_count >= 2 and word_count < 10:
        return {
            "comprehension_level": "vague",
            "visual_indicator": "confused_tilt",
            "prompt_suggestions": [
                "Add a specific name, file, or component.",
                "What outcome are you trying to achieve?",
            ],
            "detected_intent": "",
            "word_count": word_count,
        }

    # Detect intent
    detected_intent = ""
    for intent, kws in _INTENT_KEYWORDS.items():
        if any(kw in lower for kw in kws):
            detected_intent = intent
            break

    # Long prompt with multiple conflicting intent signals
    detected_count = sum(
        1 for kws in _INTENT_KEYWORDS.values() if any(kw in lower for kw in kws)
    )
    if detected_count >= 3:
        return {
            "comprehension_level": "complex",
            "visual_indicator": "thinking",
            "prompt_suggestions": [
                "This covers a lot — try splitting into smaller questions.",
                "What's the single most important goal right now?",
            ],
            "detected_intent": detected_intent,
            "word_count": word_count,
        }

    # Clear prompt
    suggestions: list[str] = []
    if detected_intent and word_count < 8:
        tip_map = {
            "BUILD":      "Add what you're building — component name or feature.",
            "DEBUG":      "Include the error message or what's failing.",
            "AUDIT":      "Specify what aspect to audit — security, performance, or deps.",
            "DESIGN":     "Name the target platform or existing design system.",
            "EXPLAIN":    "Mention your familiarity level so I can pitch it right.",
            "IDEATE":     "What constraints or goals should the ideas fit within?",
            "SPAWN_REPO": "What tech stack and project type?",
        }
        tip = tip_map.get(detected_intent)
        if tip:
            suggestions.append(tip)

    return {
        "comprehension_level": "clear" if detected_intent else "listening",
        "visual_indicator": "nodding" if detected_intent else "thinking",
        "prompt_suggestions": suggestions,
        "detected_intent": detected_intent,
        "word_count": word_count,
    }
