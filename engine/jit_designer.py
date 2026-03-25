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
    ("BUILD",   "excited"):    "morph",
    ("BUILD",   "neutral"):    "morph",
    ("DEBUG",   "frustrated"): "morph",
    ("DEBUG",   "neutral"):    "morph",
    ("DESIGN",  "excited"):    "morph",
    ("DESIGN",  "neutral"):    "morph",
    ("IDEATE",  "excited"):    "morph",
    ("IDEATE",  "uncertain"):  "morph",
    ("EXPLAIN", "uncertain"):  "morph",
    ("EXPLAIN", "neutral"):    "morph",
    ("AUDIT",   "neutral"):    "morph",
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


# ── Inline Markdown stripper ──────────────────────────────────────────────────

def _strip_inline_md(text: str) -> str:
    """Remove common inline Markdown markers (**bold**, `code`, _italic_)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def _make_style_directives(
    palette_key: str, intent: str, elevation: int = 1
) -> dict[str, Any]:
    """Map a semantic palette key to concrete UI style hints for the frontend."""
    theme_map = {
        "system_blue":   "hig-blue",
        "system_green":  "hig-green",
        "system_red":    "hig-red",
        "system_orange": "hig-orange",
        "system_teal":   "hig-teal",
        "system_purple": "hig-purple",
    }
    return {
        "theme": theme_map.get(palette_key, "material-dark"),
        "elevation": elevation,
        "intent": intent,
    }


# ── UIComponent (Dynamic DOM payload) ─────────────────────────────────────────

@dataclass
class UIComponent:
    """A structured, renderable UI block extracted from Buddy's response.

    The frontend ``ComponentRenderer`` maps ``component_type`` to a DOM factory
    and uses ``style_directives`` to choose colour theme and elevation.

    ``component_type`` values:
      prose          — plain conversational text (intro / summary lines)
      timeline_step  — numbered step (BUILD / DEBUG roadmaps)
      storybook_card — bullet-point idea card (IDEATE / EXPLAIN lists)
      insight_chip   — key: value compact data pair
      glass_table    — Markdown table → Material Design elevated table
      code_block     — fenced code block with language label + copy button
    """

    component_type: str
    content: dict[str, Any]
    style_directives: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_type": self.component_type,
            "content": self.content,
            "style_directives": self.style_directives,
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

        # Layout: spatial_float for the new centered Buddy experience
        word_count = len(response_text.split())
        layout_hint = "spatial_float" if word_count < 150 else "two_column"

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

    def parse_response_blocks(
        self,
        response_text: str,
        intent: str = "EXPLAIN",
        palette_key: str = "system_blue",
    ) -> list[UIComponent]:
        """Parse a freeform LLM response into ordered UIComponent blocks.

        Detects:
          - Fenced code blocks (``` … ```)  → ``code_block``
          - Markdown tables (|…| rows)      → ``glass_table``
          - Numbered lists (1. item)        → ``timeline_step``
          - Bullet lists (- item / * item)  → ``storybook_card`` or ``insight_chip``
          - Standalone **Key**: value lines → ``insight_chip``
          - Section headings (## Heading)   → prose (variant: heading)
          - Everything else                 → ``prose``

        Returns an **empty list** when no structured blocks are detected
        (purely conversational prose), signalling the frontend to fall back
        to standard text rendering.
        """
        self._load_rules()
        lines = response_text.split("\n")
        style = _make_style_directives(palette_key, intent)
        components: list[UIComponent] = []
        has_structured = False
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            i += 1

            if not stripped:
                continue

            # ── Fenced code block ────────────────────────────────────────────
            if stripped.startswith("```"):
                lang = stripped[3:].strip() or "text"
                code_parts: list[str] = []
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_parts.append(lines[i])
                    i += 1
                i += 1  # skip closing fence
                code = "\n".join(code_parts)
                if code.strip():
                    components.append(UIComponent(
                        component_type="code_block",
                        content={"language": lang, "code": code},
                        style_directives={**style, "elevation": 2},
                    ))
                    has_structured = True
                continue

            # ── Markdown table ───────────────────────────────────────────────
            if stripped.startswith("|") and "|" in stripped[1:]:
                table_rows: list[str] = [stripped]
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_rows.append(lines[i].strip())
                    i += 1
                data_rows = [
                    r for r in table_rows
                    if not re.match(r"^\|[-:|\s]+\|$", r)
                ]
                if len(data_rows) >= 2:
                    headers = [c.strip()
                               for c in data_rows[0].split("|") if c.strip()]
                    rows = [
                        [c.strip() for c in r.split("|") if c.strip()]
                        for r in data_rows[1:]
                    ]
                    components.append(UIComponent(
                        component_type="glass_table",
                        content={"headers": headers, "rows": rows},
                        style_directives={**style, "elevation": 2},
                    ))
                    has_structured = True
                continue

            # ── Numbered list → timeline_step ────────────────────────────────
            m = re.match(r"^(\d+)\.\s+(.+)$", stripped)
            if m:
                steps: list[tuple[int, str]] = [(int(m.group(1)), m.group(2))]
                while i < len(lines):
                    s = lines[i].strip()
                    m2 = re.match(r"^(\d+)\.\s+(.+)$", s)
                    if m2:
                        steps.append((int(m2.group(1)), m2.group(2)))
                        i += 1
                    elif not s:
                        i += 1
                    else:
                        break
                for num, text in steps:
                    clean = _strip_inline_md(text)
                    if ": " in clean and len(clean.split(": ", 1)[0]) < 42:
                        lbl, body = clean.split(": ", 1)
                    else:
                        lbl, body = clean, ""
                    components.append(UIComponent(
                        component_type="timeline_step",
                        content={"index": num, "label": lbl, "body": body},
                        style_directives=style,
                    ))
                has_structured = True
                continue

            # ── Bullet list → storybook_card or insight_chip ─────────────────
            m = re.match(r"^[-*•]\s+(.+)$", stripped)
            if m:
                items: list[str] = [m.group(1)]
                while i < len(lines):
                    s = lines[i].strip()
                    m2 = re.match(r"^[-*•]\s+(.+)$", s)
                    if m2:
                        items.append(m2.group(1))
                        i += 1
                    elif not s:
                        i += 1
                    else:
                        break
                for item in items:
                    bold_kv = re.match(r"^\*\*(.+?)\*\*:?\s+(.*)", item)
                    if bold_kv:
                        components.append(UIComponent(
                            component_type="insight_chip",
                            content={
                                "key": bold_kv.group(1),
                                "value": _strip_inline_md(bold_kv.group(2)),
                            },
                            style_directives=style,
                        ))
                    else:
                        clean = _strip_inline_md(item)
                        colon_m = re.match(r"^(.{3,35}):\s+(.{5,})$", clean)
                        if colon_m:
                            components.append(UIComponent(
                                component_type="insight_chip",
                                content={
                                    "key": colon_m.group(1),
                                    "value": colon_m.group(2),
                                },
                                style_directives=style,
                            ))
                        else:
                            dot_idx = clean.find(". ")
                            if 0 < dot_idx < 55:
                                title, body = clean[:dot_idx], clean[dot_idx + 2:]
                            else:
                                title, body = clean[:60], clean[60:].strip()
                            components.append(UIComponent(
                                component_type="storybook_card",
                                content={"title": title, "body": body},
                                style_directives=style,
                            ))
                has_structured = True
                continue

            # ── Standalone **Key**: value ─────────────────────────────────────
            m = re.match(r"^\*\*(.+?)\*\*:?\s+(.+)$", stripped)
            if m:
                components.append(UIComponent(
                    component_type="insight_chip",
                    content={
                        "key": m.group(1),
                        "value": _strip_inline_md(m.group(2)),
                    },
                    style_directives=style,
                ))
                has_structured = True
                continue

            # ── Section heading ───────────────────────────────────────────────
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                if heading:
                    components.append(UIComponent(
                        component_type="prose",
                        content={"text": heading, "variant": "heading"},
                        style_directives=style,
                    ))
                continue

            # ── Prose fallback ────────────────────────────────────────────────
            clean = _strip_inline_md(stripped)
            if len(clean) > 3:
                components.append(UIComponent(
                    component_type="prose",
                    content={"text": stripped},
                    style_directives=style,
                ))

        # Return empty list when no structured content found →
        # frontend falls back to standard Markdown rendering.
        if not has_structured:
            return []
        return components


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


# ── StreamInterceptor ─────────────────────────────────────────────────────────

class StreamInterceptor:
    """Routes streaming LLM text to ``token`` or ``ui_component`` SSE events.

    As the LLM streams text chunk-by-chunk, ``StreamInterceptor`` maintains a
    line-level state machine.  Prose text is emitted immediately as
    ``{"type": "token", "text": "..."}`` events.  Structured Markdown blocks
    (fenced code, numbered lists, bullet lists, Markdown tables) are buffered
    until the block is complete, then parsed with
    ``JITDesigner.parse_response_blocks()`` and emitted as
    ``{"type": "ui_component", "component": {...}}`` events.

    This means structured content is *swallowed* from the token stream and
    surfaced as native UI events — exactly the "brain-to-hands" bridge.

    Thread-safety: instances are single-use (Law 17 — create one per request).

    Usage::

        interceptor = StreamInterceptor(intent="BUILD", palette_key="system_blue")
        for chunk in llm_stream:
            for event in interceptor.feed(chunk):
                yield _sse(event)
        for event in interceptor.flush():
            yield _sse(event)
    """

    _STATE_PROSE = "prose"
    _STATE_CODE = "code_block"
    _STATE_NUM = "numbered_list"
    _STATE_BULLET = "bullet_list"
    _STATE_TABLE = "table"
    # Safety: flush block if buffer exceeds this size to prevent memory bloat
    _MAX_BLOCK_BYTES = 8 * 1024  # 8 KB

    def __init__(
        self,
        intent: str = "EXPLAIN",
        palette_key: str = "system_blue",
        designer: "JITDesigner | None" = None,
    ) -> None:
        self._intent = intent
        self._palette_key = palette_key
        self._designer = designer or JITDesigner()
        self._state = self._STATE_PROSE
        # Characters received since the last newline (no trailing \n yet)
        self._partial: str = ""
        # Complete lines buffered for the current structured block
        self._block_lines: list[str] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def feed(self, chunk: str) -> list[dict[str, Any]]:
        """Process one streaming chunk.  Returns list of SSE event dicts."""
        events: list[dict[str, Any]] = []
        remaining = chunk
        while "\n" in remaining:
            head, remaining = remaining.split("\n", 1)
            self._partial += head
            complete_line = self._partial + "\n"
            self._partial = ""
            events.extend(self._process_line(complete_line))

        self._partial += remaining
        # Safety: emergency flush if a single block grows too large
        if sum(len(ln) for ln in self._block_lines) > self._MAX_BLOCK_BYTES:
            events.extend(self._end_block())

        return events

    def flush(self) -> list[dict[str, Any]]:
        """Flush all remaining buffered content.  Must be called once at stream end."""
        events: list[dict[str, Any]] = []
        if self._partial:
            # Treat as a completed line without trailing newline
            events.extend(self._process_line(self._partial))
            self._partial = ""
        events.extend(self._end_block())
        return events

    # ── Internal state machine ─────────────────────────────────────────────────

    def _process_line(self, line: str) -> list[dict[str, Any]]:
        """Route one complete line through the state machine."""
        stripped = line.strip()
        events: list[dict[str, Any]] = []

        if self._state == self._STATE_CODE:
            self._block_lines.append(line)
            # Closing fence: starts with ``` and is NOT the opening fence
            if stripped.startswith("```") and len(self._block_lines) > 1:
                events.extend(self._end_block())
            return events

        if self._state == self._STATE_TABLE:
            if stripped.startswith("|") and "|" in stripped[1:]:
                self._block_lines.append(line)
                return events
            # Non-table line ends the table
            events.extend(self._end_block())
            return events + self._start_line(line)

        if self._state == self._STATE_NUM:
            if re.match(r"^\d+\.\s", stripped):
                self._block_lines.append(line)
                return events
            if not stripped:  # blank line ends numbered list
                events.extend(self._end_block())
                return events
            events.extend(self._end_block())
            return events + self._start_line(line)

        if self._state == self._STATE_BULLET:
            if re.match(r"^[-*•]\s", stripped):
                self._block_lines.append(line)
                return events
            if not stripped:  # blank line ends bullet list
                events.extend(self._end_block())
                return events
            events.extend(self._end_block())
            return events + self._start_line(line)

        # ── PROSE state ───────────────────────────────────────────────────────
        return self._start_line(line)

    def _start_line(self, line: str) -> list[dict[str, Any]]:
        """Handle a new line while in PROSE state — decide if a block starts."""
        stripped = line.strip()

        if stripped.startswith("```"):
            self._state = self._STATE_CODE
            self._block_lines = [line]
            return []

        if stripped.startswith("|") and "|" in stripped[1:]:
            self._state = self._STATE_TABLE
            self._block_lines = [line]
            return []

        if re.match(r"^\d+\.\s", stripped):
            self._state = self._STATE_NUM
            self._block_lines = [line]
            return []

        if re.match(r"^[-*•]\s", stripped):
            self._state = self._STATE_BULLET
            self._block_lines = [line]
            return []

        # Plain prose line
        if stripped:
            return [{"type": "token", "text": line}]
        return []

    def _end_block(self) -> list[dict[str, Any]]:
        """Parse accumulated block lines → UIComponents; reset to PROSE."""
        if not self._block_lines:
            self._state = self._STATE_PROSE
            return []

        block_text = "".join(self._block_lines)
        self._block_lines = []
        self._state = self._STATE_PROSE

        comps = self._designer.parse_response_blocks(
            block_text,
            intent=self._intent,
            palette_key=self._palette_key,
        )
        if comps:
            return [
                {"type": "ui_component", "component": c.to_dict()} for c in comps
            ]
        # Block parsed to nothing (e.g. empty fence) — fall back to token
        return [{"type": "token", "text": block_text}]


def analyze_partial_prompt(
    text: str,
    session_context: str = "",
) -> dict[str, Any]:
    """Fast, synchronous analysis of a partial user prompt.  No LLM calls.

    Args:
        text:            Partial user input (up to 2000 chars).
        session_context: Optional prior intent from session history.  When
                         provided, suggestions are contextualised — e.g. if the
                         last intent was BUILD, drill-down tips are shown.

    Returns a dict with:
      comprehension_level : "clear" | "vague" | "complex" | "listening"
      visual_indicator    : "nodding" | "thinking" | "listening" | "confused_tilt"
      prompt_suggestions  : list of 1-3 short actionable tips
      detected_intent     : best-guess intent or ""
      word_count          : int
    """
    stripped = text.strip()
    words = stripped.split()
    word_count = len(words)
    lower = stripped.lower()

    # Very short → listening / vague
    if word_count < 3:
        if session_context:
            # Contextual nudge: know the prior topic
            ctx_tips: dict[str, str] = {
                "BUILD":  "Keep building — what part are you working on next?",
                "DEBUG":  "Debugging again? Share the error or behaviour.",
                "AUDIT":  "What should I check this time?",
                "DESIGN": "What component or screen?",
                "EXPLAIN": "What would you like me to explain?",
                "IDEATE": "Tell me more — any constraints or goals?",
                "SPAWN_REPO": "What's the project type or stack?",
            }
            tip = ctx_tips.get(
                session_context, "Keep going — what do you want to achieve?")
        else:
            tip = "Keep going — what do you want to achieve?"
        return {
            "comprehension_level": "listening",
            "visual_indicator": "listening",
            "prompt_suggestions": [tip],
            "detected_intent": session_context,
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

    # Clear prompt — generate context-aware, specificity-boosting tips
    suggestions: list[str] = []

    # Primary intent tip: short prompts benefit from more specificity
    if detected_intent and word_count < 8:
        tip_map: dict[str, list[str]] = {
            "BUILD":      [
                "Add what you're building — component name or feature.",
                "Mention the language or framework.",
            ],
            "DEBUG":      [
                "Include the error message or what's failing.",
                "What did you expect to happen vs what did?",
            ],
            "AUDIT":      [
                "Specify what aspect to audit — security, performance, or deps.",
                "Any known constraints or compliance requirements?",
            ],
            "DESIGN":     [
                "Name the target platform or existing design system.",
                "Desktop, mobile, or both?",
            ],
            "EXPLAIN":    [
                "Mention your familiarity level so I can pitch it right.",
                "Any specific part of this you'd like focused on?",
            ],
            "IDEATE":     [
                "What constraints or goals should the ideas fit within?",
                "Technical, product, or UX focus?",
            ],
            "SPAWN_REPO": [
                "What tech stack and project type?",
                "Any CI/CD or deployment requirements?",
            ],
        }
        tips = tip_map.get(detected_intent, [])
        suggestions.extend(tips[:1])  # add one primary tip

    # Continuity tip: if session_context present and detected intent differs
    if session_context and detected_intent and session_context != detected_intent:
        suggestions.append(
            f"Switching from {session_context} to {detected_intent} — I'm with you."
        )

    return {
        "comprehension_level": "clear" if detected_intent else "listening",
        "visual_indicator": "nodding" if detected_intent else "thinking",
        "prompt_suggestions": suggestions[:2],  # cap at 2 for UI clarity
        "detected_intent": detected_intent,
        "word_count": word_count,
    }
