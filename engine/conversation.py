"""
engine/conversation.py — Conversational Buddy process engine.

Provides multi-turn session memory, intent-aware DAG planning, Gemini-powered
response generation (keyword fallback), tone modulation per intent, clarification
detection, and follow-up suggestion generation.

Visual Artifact Protocol:
  Buddy can emit structured ``<visual_artifact>`` XML blocks inside its response.
  Each block carries a ``type``, ``content``, and optional ``metadata``.  The
  ConversationEngine parses these blocks from the LLM response and returns them
  as structured ``VisualArtifact`` objects in ``ConversationResult.visual_artifacts``.

  Supported artifact types:
    html_component    — standalone HTML/JS component (rendered in sandboxed iframe)
    svg_animation     — GSAP-driven SVG to control the #buddyCanvas
    mermaid_diagram   — Mermaid.js diagram source
    chart_json        — Chart.js config JSON

  The ``_SYSTEM_PROMPT`` always instructs the model to prefer visual output for
  demonstrative answers, so Buddy will naturally produce artifacts when relevant.

Pipeline per turn:
  ConversationEngine.process(text, route, session_id)
    → _needs_clarification?  → build clarifying question (wave 0)
    → _plan()                → ConversationPlan (waves: understand → respond → suggest)
    → _generate_response()   → Gemini-2.0-flash or keyword fallback
    → _parse_visual_artifacts() → list[VisualArtifact]
    → _suggest_followups()   → 3 actionable chips per intent
    → ConversationResult (stored in session, returned to caller)
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from engine.config import GEMINI_API_KEY, VERTEX_DEFAULT_MODEL, _vertex_client as _vertex_client_cfg
from engine.router import RouteResult
from engine.model_garden import get_garden

if TYPE_CHECKING:
    from engine.jit_booster import JITBoostResult

# ── Vertex AI client (primary — enterprise-grade Model Garden via unified SDK) ───────
_vertex_client = _vertex_client_cfg

# ── Gemini Direct client (secondary fallback — consumer API) ─────────────────────
_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        _gemini_client = _genai_mod.Client(api_key=GEMINI_API_KEY)
    except Exception:  # pragma: no cover
        pass

# ── Valid visual artifact types ───────────────────────────────────────────────
_VALID_ARTIFACT_TYPES: frozenset[str] = frozenset(
    {"html_component", "svg_animation", "mermaid_diagram", "chart_json"}
)

# ── Visual artifact XML pattern ────────────────────────────────────────────────
_ARTIFACT_RE = re.compile(
    r'<visual_artifact\s+type="([^"]+)"(?:\s+title="([^"]*)")?'
    r'(?:\s+height="([^"]*)")?'
    r'(?:\s+interactive="([^"]*)")?'
    r'\s*>(.*?)</visual_artifact>',
    re.DOTALL | re.IGNORECASE,
)

# ── VLT patch XML pattern (spatial 3D material/position diffs) ────────────────
_VLT_PATCH_RE = re.compile(
    r'<vlt_patch\s*>(.*?)</vlt_patch>',
    re.DOTALL | re.IGNORECASE,
)


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class VLTPatch:
    """Differential Vector Layout Tree patch — morphs the spatial 3D environment.

    Emitted inside ``<vlt_patch>`` XML blocks by the LLM. Parsed and broadcast
    as a ``vlt_patch`` SSE event so the Spatial Engine can GSAP-tween node
    materials and positions in real time without a page reload.
    """

    patches: list[dict[str, Any]]
    transition_ms: int = 400

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "vlt_patch",
            "patches": self.patches,
            "transition_ms": self.transition_ms,
        }


@dataclass
class VisualArtifact:
    """A structured visual payload emitted by Buddy alongside text responses.

    Fields:
        artifact_id:  Unique ID for frontend deduplication / caching.
        type:         One of html_component | svg_animation | mermaid_diagram | chart_json.
        content:      Raw code / JSON / SVG / Mermaid source to render.
        metadata:     Optional dict with title, recommended_height, interactive, etc.
    """

    artifact_id: str
    type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
        }


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class ConversationTurn:
    """Single exchange stored in a session."""

    turn_id: str
    role: str  # "user" | "buddy"
    text: str
    intent: str
    confidence: float
    response: str
    tone: str
    # frustrated | excited | uncertain | grateful | neutral
    emotional_state: str = "neutral"
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "role": self.role,
            "text": self.text,
            "intent": self.intent,
            "confidence": self.confidence,
            "response": self.response,
            "tone": self.tone,
            "emotional_state": self.emotional_state,
            "ts": self.ts,
        }


@dataclass
class ConversationSession:
    """Ordered turn history for one chat session."""

    session_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())

    def add_turn(self, turn: ConversationTurn) -> None:
        self.turns.append(turn)

    def last_n(self, n: int = 5) -> list[ConversationTurn]:
        return self.turns[-n:]

    def intent_history(self) -> list[str]:
        return [t.intent for t in self.turns if t.role == "user"]

    def emotional_arc(self) -> list[str]:
        """Return the emotional states of the last few user turns."""
        return [
            t.emotional_state for t in self.turns
            if t.role == "user" and getattr(t, "emotional_state", "neutral") != "neutral"
        ][-3:]

    def last_topic_summary(self) -> str:
        """Return a very brief summary of the most recent topic if available."""
        user_turns = [t for t in self.turns if t.role == "user"]
        if len(user_turns) >= 2:
            return user_turns[-2].text[:80]
        return ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_count": len(self.turns),
            "created_at": self.created_at,
            "intent_history": self.intent_history(),
            "emotional_arc": self.emotional_arc(),
        }


@dataclass
class ConversationPhase:
    """One wave-ordered step in the conversation execution plan."""

    name: str
    description: str
    wave: int

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "wave": self.wave}


@dataclass
class ConversationPlan:
    """DAG-ordered plan for a single conversational turn."""

    mandate_id: str
    intent: str
    phases: list[ConversationPhase]
    needs_clarification: bool = False
    clarification_question: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandate_id": self.mandate_id,
            "intent": self.intent,
            "phases": [p.to_dict() for p in self.phases],
            "waves": len(self.phases),
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
        }


@dataclass
class ConversationResult:
    """Full result of a single processed turn."""

    session_id: str
    turn_id: str
    response_text: str
    plan: ConversationPlan
    suggestions: list[str]
    tone: str
    intent: str
    confidence: float
    latency_ms: float
    model_used: str
    emotional_state: str = "neutral"
    visual_artifacts: list[VisualArtifact] = field(default_factory=list)
    vlt_patches: list[VLTPatch] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "response_text": self.response_text,
            "plan": self.plan.to_dict(),
            "suggestions": self.suggestions,
            "tone": self.tone,
            "intent": self.intent,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "model_used": self.model_used,
            "emotional_state": self.emotional_state,
            "visual_artifacts": [a.to_dict() for a in self.visual_artifacts],
            "vlt_patches": [p.to_dict() for p in self.vlt_patches],
        }


# ── Emotional state detection ─────────────────────────────────────────────────

_FRUSTRATION_SIGNALS = frozenset({
    "broken", "stuck", "failing", "failed", "doesn't work", "won't work",
    "not working", "can't", "cannot", "why is", "why does", "help",
    "confused", "lost", "wrong", "error", "keeps", "still", "again",
    "tired", "frustrated", "annoying", "terrible", "awful", "impossible",
})

_EXCITEMENT_SIGNALS = frozenset({
    "amazing", "awesome", "love this", "love it", "great", "excellent",
    "finally", "perfect", "brilliant", "fantastic", "let's go", "lets go",
    "excited", "can't wait", "cant wait", "this is cool",
})

_UNCERTAINTY_SIGNALS = frozenset({
    "not sure", "maybe", "wondering", "would it be", "could we", "is it possible",
    "what if", "how do i", "how should", "should i", "do you think", "best way",
})

_GRATITUDE_SIGNALS = frozenset({
    "thanks", "thank you", "cheers", "appreciate", "helpful", "that helped",
    "that worked", "good job", "well done", "nice",
})


def _detect_emotional_state(text: str) -> str:
    """Lightweight scan of user message for emotional context.

    Returns one of: 'frustrated' | 'excited' | 'uncertain' | 'grateful' | 'neutral'.
    """
    lower = text.lower()
    for signal in _FRUSTRATION_SIGNALS:
        if signal in lower:
            return "frustrated"
    for signal in _GRATITUDE_SIGNALS:
        if signal in lower:
            return "grateful"
    for signal in _EXCITEMENT_SIGNALS:
        if signal in lower:
            return "excited"
    for signal in _UNCERTAINTY_SIGNALS:
        if signal in lower:
            return "uncertain"
    return "neutral"


# ── Cognitive empathy openers ──────────────────────────────────────────────────
# Keyed by (emotional_state, intent) — fall back to (emotional_state, *) then neutral.

_EMPATHY_OPENERS: dict[tuple[str, str], str] = {
    ("frustrated", "DEBUG"): "I can see this has been a battle — let's dig in together and track it down.",
    ("frustrated", "BUILD"): "No worries, let's clear the path and get this moving.",
    ("frustrated", "AUDIT"): "Auditing systems is exactly how we catch the hidden culprits. Let's find what's biting you.",
    ("frustrated", "EXPLAIN"): "Let me take a different angle on this — sometimes it just needs a fresh framing.",
    ("frustrated", "IDEATE"): "Sometimes the best ideas come exactly when you're stuck. Let's flip the perspective.",
    ("frustrated", "DESIGN"): "Design problems can be stubborn. Let's step back and find the root constraint.",
    ("excited", "BUILD"): "That energy is contagious! Let's ride it and make this happen.",
    ("excited", "IDEATE"): "Love it — let's take that spark and turn it into something real.",
    ("excited", "DESIGN"): "Great vision. Let's shape it into something you'll be proud of.",
    ("excited", "SPAWN_REPO"): "Let's scaffold this properly so it starts strong and scales well.",
    ("uncertain", "BUILD"): "Good instinct to pause and think it through. Here's how I'd approach it:",
    ("uncertain", "DESIGN"): "Design decisions feel clearer once we name the constraints. Let me help with that.",
    ("uncertain", "EXPLAIN"): "Totally understandable — there's a lot of nuance here. Let me unpack it step by step.",
    ("uncertain", "IDEATE"): "Uncertainty is actually the best place to ideate from. Let's explore the space.",
    ("grateful", "BUILD"): "Happy it's working! Here's what I'd do next:",
    ("grateful", "EXPLAIN"): "Great — building on that, here's the next layer:",
    ("frustrated", "*"): "I hear you — let's work through this together.",
    ("excited", "*"): "Great energy! Here's what I'm thinking:",
    ("uncertain", "*"): "Good question to sit with. Here's how I'd frame it:",
    ("grateful", "*"): "Really glad that helped! Here's a natural next step:",
}


def _get_empathy_opener(emotional_state: str, intent: str) -> str:
    """Return an appropriate empathy opener for the given emotional state + intent."""
    if emotional_state == "neutral":
        return ""
    specific = _EMPATHY_OPENERS.get((emotional_state, intent), "")
    if specific:
        return specific
    return _EMPATHY_OPENERS.get((emotional_state, "*"), "")


# ── Tone + follow-up maps ─────────────────────────────────────────────────────

_TONE: dict[str, str] = {
    "BUILD":      "constructive",
    "DEBUG":      "analytical",
    "AUDIT":      "precise",
    "DESIGN":     "creative",
    "EXPLAIN":    "pedagogical",
    "IDEATE":     "exploratory",
    "SPAWN_REPO": "architectural",
    "BLOCKED":    "cautious",
}

_FOLLOWUPS: dict[str, list[str]] = {
    "BUILD": [
        "Want me to write tests for this too?",
        "Should I add type hints throughout?",
        "Ready to wire up CI/CD when you are.",
    ],
    "DEBUG": [
        "Want a regression test to lock this fix in?",
        "Should I trace the full call path for you?",
        "Want a plain-English root-cause summary?",
    ],
    "AUDIT": [
        "Want findings ranked by severity and risk?",
        "Should I write up remediation steps for each?",
        "Want a dependency licence scan too?",
    ],
    "DESIGN": [
        "Want a dark-mode variant of this?",
        "Should I check WCAG contrast ratios?",
        "Want me to turn this into a component spec?",
    ],
    "EXPLAIN": [
        "Want a diagram to go with this?",
        "Should I write this up as a runbook?",
        "Want a few questions to test your understanding?",
    ],
    "IDEATE": [
        "Want me to prototype the strongest idea?",
        "Should I map risk vs. effort for each option?",
        "Want to see what's already been built in this space?",
    ],
    "SPAWN_REPO": [
        "Want me to generate a GitHub Actions workflow?",
        "Should I scaffold a README and contributing guide?",
        "Want a commit message convention set up too?",
    ],
    "BLOCKED": [
        "Reset the circuit breaker from the toolbar",
        "Tell me what you were trying to do — I can reroute",
        "Want me to review the confidence threshold settings?",
    ],
}

_CLARIFICATION_Q: dict[str, str] = {
    "BUILD": "What are we building? A quick description of the component or feature helps me hit the ground running.",
    "DEBUG": "What's going wrong? The error message, stack trace, or even just what you expected vs. what happened is a great start.",
    "AUDIT": "What should I look at — security vulnerabilities, stale dependencies, performance, or something else?",
    "DESIGN": "What's the target platform, and is there an existing design system I should stay consistent with?",
    "EXPLAIN": "How familiar are you with this already? I'll pitch the explanation at exactly the right level.",
    "IDEATE": "What's the core problem we're trying to solve? I'll generate ideas that actually fit your constraints.",
    "SPAWN_REPO": "What's the project about — tech stack, purpose, and any structure preferences? I'll scaffold it properly.",
}

_KEYWORD_RESPONSES: dict[str, str] = {
    "BUILD": (
        "On it. I'll break this into recon → design → build → validate waves so nothing gets skipped. "
        "Every generated artefact gets an OWASP scan before it lands — you'll see the plan take shape in real time."
    ),
    "DEBUG": (
        "Let's track this down. I'll trace the failure path step by step, pinpoint the root cause, "
        "and apply the smallest fix that sticks. I'll add a regression test so it can't sneak back in."
    ),
    "AUDIT": (
        "Running a thorough audit — I'll check for security misconfigs, outdated dependencies, "
        "and licence risks, then rank every finding by severity so you know exactly what to tackle first."
    ),
    "DESIGN": (
        "Switching to design mode. I'll map the requirements, produce a component-level design, "
        "and validate WCAG 2.1 AA contrast and responsive behaviour. Let me know if you have a design system to stay within."
    ),
    "EXPLAIN": (
        "Happy to walk you through this. I'll build the picture layer by layer — starting simple, "
        "adding depth as we go. Want a diagram or runbook alongside the explanation? Just say so."
    ),
    "IDEATE": (
        "Let's explore the possibility space. I'll generate and score several approaches — each with "
        "a risk/effort estimate and a concrete first step — so you can see the tradeoffs clearly."
    ),
    "SPAWN_REPO": (
        "Let's build this right from day one. I'll scaffold the structure, CI/CD pipeline, "
        "and documentation baseline. Every generated file gets a Tribunal pass before it goes in."
    ),
    "BLOCKED": (
        "The circuit breaker has tripped — that's a safety gate, not a failure. "
        "Reset it from the toolbar, then tell me what you were trying to do and I'll find you a path through."
    ),
}

_SYSTEM_PROMPT = (
    "You are Buddy — the cognitive partner and host of TooLoo V2. Your purpose is not just to "
    "process requests, but to genuinely support the person behind each message. You understand "
    "that people come to you with real goals, real frustrations, and real excitement, and your job "
    "is to meet them where they are.\n\n"
    "PERSONALITY: Warm, direct, and genuinely interested. You care about outcomes, not just outputs. "
    "You adapt your tone — calm and methodical when someone is stuck, energised when they're "
    "building something exciting, patient and clear when they're learning. You do not pad "
    "responses with filler, but you also do not strip out the human element. A short acknowledgment "
    "of the person's situation is always appropriate before diving into the answer.\n\n"
    "COGNITIVE SUPPORT PRINCIPLES:\n"
    "1. Acknowledge the person's state before answering — one sentence is enough.\n"
    "2. Match complexity to need — simple questions deserve simple answers; complex problems "
    "deserve structured walkthroughs.\n"
    "3. Use 'we' and 'let's' when working through something together.\n"
    "4. Reference prior conversation naturally — 'Building on what we discussed...' or "
    "'Since you're already working on X...' shows you've been listening.\n"
    "5. End with an invitation — a question, a next step, or a follow-up option — so the "
    "conversation can continue naturally.\n"
    "6. If someone seems confused or lost, slow down and offer to rephrase or diagram it.\n"
    "7. Celebrate small wins — 'That approach is solid' or 'You're on the right track' costs "
    "nothing and means a lot.\n\n"
    "RESPONSE LENGTH: Match the depth of the answer to the complexity of the question. "
    "Conversational questions get conversational answers (2-4 sentences). Technical deep-dives "
    "get structured, thorough responses. Never truncate a necessary explanation.\n\n"
    "INTERNAL DETAILS: Never expose internal engine names, node IDs, or implementation details "
    "unless specifically asked. Speak in outcomes and capabilities, not in system internals.\n\n"
    "VISUAL LANGUAGE: When a visual would answer the user better than text, embed one or more "
    "<visual_artifact> blocks. Prefer visuals for architecture diagrams, UI components, data "
    "charts, and animated concepts.\n\n"
    'Syntax: <visual_artifact type="<TYPE>" title="<TITLE>" height="<PX>" interactive="true|false">\n'
    "<CONTENT>\n"
    "</visual_artifact>\n\n"
    "Supported types:\n"
    "  html_component  — standalone HTML/CSS/JS widget (sandboxed in iframe)\n"
    "  svg_animation   — GSAP SVG targeting #buddyCanvas nodes\n"
    "  mermaid_diagram — Mermaid.js diagram source\n"
    "  chart_json      — Chart.js configuration JSON\n\n"
    "Security: never include fetch(), XMLHttpRequest, or parent frame access in html_component.\n\n"
    "SPATIAL UI: The frontend shows a live 3D DAG constellation. When changing the visual/material "
    "state of the spatial environment, emit a <vlt_patch> block with a JSON array of node patches. "
    "This fires real-time GSAP tweens in the browser.\n"
    "Patch schema per node: {\"node_id\": \"route|jit|tribunal|scope|execute|refine\", "
    "\"material\": {\"emissive\": 0.0-2.0, \"roughness\": 0.0-1.0, \"opacity\": 0.0-1.0}, "
    "\"coordinates\": {\"x\": float, \"y\": float, \"rotation_y\": degrees}}\n"
    "Example: <vlt_patch>[{\"node_id\":\"execute\",\"material\":{\"emissive\":1.5}}]</vlt_patch>\n"
    "Only emit vlt_patch when the mandate explicitly asks for a spatial/visual change."
)


def _parse_vlt_patches(text: str) -> list[VLTPatch]:
    """Extract ``<vlt_patch>`` JSON blocks from a model response.

    Returns validated ``VLTPatch`` objects.  Malformed JSON is silently dropped.
    Each patch list is capped at 20 entries to prevent abuse.
    """
    import json as _json  # local import avoids circular at module init

    results: list[VLTPatch] = []
    for match in _VLT_PATCH_RE.finditer(text):
        raw = (match.group(1) or "").strip()
        if not raw:
            continue
        try:
            data = _json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(data, list):
            results.append(VLTPatch(patches=data[:20]))
        elif isinstance(data, dict) and "patches" in data:
            results.append(VLTPatch(
                patches=data["patches"][:20],
                transition_ms=int(data.get("transition_ms", 400)),
            ))
    return results


def _parse_visual_artifacts(text: str) -> list[VisualArtifact]:
    """Extract all ``<visual_artifact>`` blocks from a model response.

    Returns a list of validated ``VisualArtifact`` objects.  Blocks with
    unknown types are silently dropped to prevent frontend render errors.
    Content is length-capped at 64 KB.
    """
    artifacts: list[VisualArtifact] = []
    for match in _ARTIFACT_RE.finditer(text):
        artifact_type = (match.group(1) or "").strip().lower()
        title = (match.group(2) or "").strip()
        height = (match.group(3) or "").strip()
        interactive_str = (match.group(4) or "false").strip().lower()
        content = (match.group(5) or "").strip()

        if artifact_type not in _VALID_ARTIFACT_TYPES:
            continue  # skip unknown types
        if not content:
            continue
        if len(content) > 65_536:  # 64 KB hard cap — reject oversized artifacts
            continue

        artifacts.append(VisualArtifact(
            artifact_id=f"va-{uuid.uuid4().hex[:8]}",
            type=artifact_type,
            content=content,
            metadata={
                "title": title,
                "recommended_height": int(height) if height.isdigit() else 400,
                "interactive": interactive_str == "true",
            },
        ))
    return artifacts


def _build_context_block(session: ConversationSession) -> str:
    """Return a compact, recent-turn summary for the LLM prompt.

    Includes emotional state markers so the LLM can track how the user's
    mood and context have evolved across turns.
    """
    recent = session.last_n(6)
    if not recent:
        return ""
    lines = []
    for t in recent:
        if t.role == "user":
            emotional_note = f" [{t.emotional_state}]" if getattr(
                t, "emotional_state", "neutral") != "neutral" else ""
            lines.append(f"User ({t.intent}{emotional_note}): {t.text}")
        elif t.role == "buddy" and t.response:
            # Only first 200 chars to stay concise in context
            preview = t.response[:200] + ("…" if len(t.response) > 200 else "")
            lines.append(f"Buddy: {preview}")
    return "\n".join(lines)


# ── Engine ────────────────────────────────────────────────────────────────────


class ConversationEngine:
    """
    Multi-turn conversational Buddy engine.

    Lifecycle per turn:
      1. Retrieve / create ConversationSession
      2. Evaluate clarification need (confidence < threshold + no prior context)
      3. Build ConversationPlan (wave-ordered phases)
      4. Generate response (Gemini-2.0-flash -> keyword fallback)
      5. Surface follow-up suggestion chips
      6. Store turn pair (user + buddy) in session
      7. Return ConversationResult

    Confidence tiers (keyword-fallback path):
      < CLARIFICATION_THRESHOLD  → ask a targeted clarifying question
      < MEDIUM_CONFIDENCE_THRESHOLD → proceed with best-guess intent, hedge audibly
      >= MEDIUM_CONFIDENCE_THRESHOLD → confident response, no hedge
    """

    _CLARIFICATION_THRESHOLD = 0.30   # below this + no prior context -> ask
    # below this -> state the guess, invite correction
    _MEDIUM_CONFIDENCE_THRESHOLD = 0.65

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationSession] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def process(
        self,
        text: str,
        route: RouteResult,
        session_id: str,
        jit_result: JITBoostResult | None = None,
    ) -> ConversationResult:
        """Plan and execute a conversational turn; return structured result."""
        t0 = time.monotonic()
        turn_id = f"t-{uuid.uuid4().hex[:8]}"
        session = self._get_or_create(session_id)
        tone = _TONE.get(route.intent, "neutral")
        emotional_state = _detect_emotional_state(text)

        # Store user turn before planning (provides context)
        session.add_turn(ConversationTurn(
            turn_id=turn_id,
            role="user",
            text=text,
            intent=route.intent,
            confidence=route.confidence,
            response="",
            tone=tone,
            emotional_state=emotional_state,
        ))

        plan = self._plan(route, session)
        response_text, model_used = self._generate_response(
            route, session, plan, jit_result=jit_result, emotional_state=emotional_state)
        suggestions = _FOLLOWUPS.get(route.intent, [])

        # Parse visual artifacts and VLT patches from the model response
        artifacts = _parse_visual_artifacts(response_text)
        vlt_patches = _parse_vlt_patches(response_text)
        # Strip XML blocks from the text response (clean display text)
        clean_text = _ARTIFACT_RE.sub("", response_text).strip()
        clean_text = _VLT_PATCH_RE.sub("", clean_text).strip()

        session.add_turn(ConversationTurn(
            turn_id=f"{turn_id}-b",
            role="buddy",
            text=clean_text,
            intent=route.intent,
            confidence=route.confidence,
            response=clean_text,
            tone=tone,
            emotional_state="neutral",
        ))

        return ConversationResult(
            session_id=session_id,
            turn_id=turn_id,
            response_text=clean_text,
            plan=plan,
            suggestions=suggestions,
            tone=tone,
            intent=route.intent,
            confidence=route.confidence,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            model_used=model_used,
            emotional_state=emotional_state,
            visual_artifacts=artifacts,
            vlt_patches=vlt_patches,
        )

    def get_session(self, session_id: str) -> ConversationSession | None:
        return self._sessions.get(session_id)

    def session_history(self, session_id: str) -> list[dict[str, Any]]:
        session = self._sessions.get(session_id)
        return [t.to_dict() for t in session.turns] if session else []

    def clear_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    # ── Planning ───────────────────────────────────────────────────────────────

    def _plan(self, route: RouteResult, session: ConversationSession) -> ConversationPlan:
        mandate_id = f"conv-{uuid.uuid4().hex[:6]}"
        needs_clar = self._needs_clarification(route, session)
        phases: list[ConversationPhase] = []
        wave = 0

        if needs_clar:
            phases.append(ConversationPhase(
                name="clarify",
                description="Low confidence — ask a targeted clarifying question",
                wave=wave,
            ))
            wave += 1

        phases.append(ConversationPhase(
            name="understand",
            description=f"Parse intent={route.intent} (confidence={route.confidence:.2f})",
            wave=wave,
        ))
        wave += 1

        phases.append(ConversationPhase(
            name="respond",
            description="Generate intent-aware, tone-modulated response",
            wave=wave,
        ))
        wave += 1

        phases.append(ConversationPhase(
            name="suggest_followup",
            description="Surface 3 actionable follow-up suggestions",
            wave=wave,
        ))

        return ConversationPlan(
            mandate_id=mandate_id,
            intent=route.intent,
            phases=phases,
            needs_clarification=needs_clar,
            clarification_question=(
                _CLARIFICATION_Q.get(
                    route.intent, "Could you clarify what outcome you are looking for?")
                if needs_clar else ""
            ),
        )

    def _needs_clarification(self, route: RouteResult, session: ConversationSession) -> bool:
        """True when confidence is low and there is no prior conversational context."""
        return (
            route.confidence < self._CLARIFICATION_THRESHOLD
            and len(session.intent_history()) <= 1
            and route.intent != "BLOCKED"
        )

    # ── Response generation ───────────────────────────────────────────────────

    def _generate_response(
        self,
        route: RouteResult,
        session: ConversationSession,
        plan: ConversationPlan,
        jit_result: JITBoostResult | None = None,
        vertex_model_id: str | None = None,
        emotional_state: str = "neutral",
    ) -> tuple[str, str]:
        """Return (response_text, model_used_label).

        Priority: Vertex AI (Model Garden) → Gemini Direct → keyword fallback.
        Prepends an empathy opener when emotional state is non-neutral.
        """
        if plan.needs_clarification:
            return plan.clarification_question, "clarification"

        model_id = vertex_model_id or VERTEX_DEFAULT_MODEL

        # 1. ModelGarden — dispatches to best available provider (Google or Anthropic)
        garden = get_garden()
        try:
            text = garden.call(model_id, self._build_prompt(
                route, session, jit_result, emotional_state=emotional_state))
            return text, garden.source_for(model_id)
        except Exception:
            pass  # fall through to Gemini Direct

        # 2. Gemini Direct — secondary fallback (model name always mirrors Vertex)
        if _gemini_client is not None:
            try:
                return self._call_gemini(
                    route, session, jit_result, emotional_state=emotional_state
                ), VERTEX_DEFAULT_MODEL
            except Exception:
                pass  # fall through to keyword fallback

        # 3. Keyword fallback — enrich with emotional context + session continuity
        base = _KEYWORD_RESPONSES.get(route.intent, route.buddy_line)

        # Reference prior conversation warmly if available
        prior_topic = session.last_topic_summary()
        if prior_topic:
            base = f"Building on what we were working on — {base}"

        # Gracefully acknowledge medium confidence
        if route.confidence < self._MEDIUM_CONFIDENCE_THRESHOLD:
            base = self._hedge_response(base, route)

        # Prepend empathy opener for non-neutral emotional states
        empathy = _get_empathy_opener(emotional_state, route.intent)
        if empathy:
            base = f"{empathy} {base}"

        # Append SOTA validation signals so the user sees concrete evidence
        if jit_result and jit_result.signals:
            top = jit_result.signals[:2]
            signals_text = "; ".join(top)
            base = (
                f"{base}\n\n"
                f"Current best practice ({jit_result.source}): {signals_text}."
            )

        return base, "keyword-fallback"

    def _hedge_response(self, response: str, route: RouteResult) -> str:
        """Prefix response with a warm, human-like confidence acknowledgment."""
        pct = round(route.confidence * 100)
        if pct <= 20:
            opener = (
                f"I'm reading between the lines here (~{pct}% match on "
                f"{route.intent}) — this is my best guess, so correct me if I'm off."
            )
        elif pct <= 40:
            opener = (
                f"I'm treating this as {route.intent} (~{pct}% confident). "
                f"If that's not right, just tell me — I'll adjust."
            )
        else:
            opener = (
                f"Reading this as {route.intent} (about {pct}% match). "
                f"Let me know if you had something different in mind."
            )
        return f"{opener} {response}"

    def _build_prompt(
        self,
        route: RouteResult,
        session: ConversationSession,
        jit_result: JITBoostResult | None = None,
        emotional_state: str = "neutral",
    ) -> str:
        """Assemble the full prompt string from session context + JIT signals."""
        context = _build_context_block(session)
        context_section = f"\n\nRecent conversation:\n{context}" if context else ""

        # Include emotional state so the LLM can respond appropriately
        emotional_note = ""
        if emotional_state != "neutral":
            emotional_note = f"\n\nUser's current emotional state: {emotional_state}. Acknowledge this naturally before answering."

        jit_section = ""
        if jit_result and jit_result.signals:
            jit_section = (
                f"\n\nSOTA signals fetched JIT ({jit_result.source}, "
                f"boosted confidence {jit_result.boosted_confidence:.0%}):\n"
                + "\n".join(f"- {s}" for s in jit_result.signals)
            )
        return (
            f"{_SYSTEM_PROMPT}{context_section}{emotional_note}{jit_section}\n\n"
            f"Intent: {route.intent} (confidence {route.confidence:.0%})\n"
            f"User: {route.mandate_text}"
        )

    def _call_vertex(
        self,
        route: RouteResult,
        session: ConversationSession,
        jit_result: JITBoostResult | None = None,
        model_id: str = "",
        emotional_state: str = "neutral",
    ) -> str:
        """Call Vertex AI Model Garden with session context + JIT signals."""
        prompt = self._build_prompt(
            route, session, jit_result, emotional_state=emotional_state)
        resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
            model=model_id or VERTEX_DEFAULT_MODEL, contents=prompt
        )
        return resp.text.strip()

    def _call_gemini(
        self,
        route: RouteResult,
        session: ConversationSession,
        jit_result: JITBoostResult | None = None,
        emotional_state: str = "neutral",
    ) -> str:
        prompt = self._build_prompt(
            route, session, jit_result, emotional_state=emotional_state)
        resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
            model=VERTEX_DEFAULT_MODEL, contents=prompt)
        return resp.text.strip()

    # ── Session management ────────────────────────────────────────────────────

    def _get_or_create(self, session_id: str) -> ConversationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(
                session_id=session_id)
        return self._sessions[session_id]
