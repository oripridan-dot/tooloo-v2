# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T20:02:28.288326+00:00
# Component: conversation  Source: engine/conversation.py
# Improvement signals from JIT SOTA booster:
#  [1] Enhance engine/conversation.py: OWASP Top 10 2025 edition promotes Broken
#     Object-Level Authorisation to the #1 priority
#  [2] Enhance engine/conversation.py: OSS supply-chain audits (Sigstore + Rekor
#     transparency log) are required in regulated environments
#  [3] Enhance engine/conversation.py: CSPM tools (Wiz, Orca, Prisma Cloud) provide
#     real-time cloud posture scoring in 2026
# ─────────────────────────────────────────────────────────────────
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
from engine.buddy_cache import BuddyCache
from engine.buddy_cognition import (
    CognitiveLens,
    UserProfileStore,
    UserProfile,
    build_cognition_context,
)

if TYPE_CHECKING:
    from engine.jit_booster import JITBoostResult
    from engine.buddy_memory import BuddyMemoryStore, BuddyMemoryEntry

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
# 2026 expanded set — code_playground, timeline, kanban added based on deep
# research into the most-requested visual communication formats for dev tools.
_VALID_ARTIFACT_TYPES: frozenset[str] = frozenset({
    "html_component",    # Standalone HTML/CSS/JS widget (sandboxed iframe)
    "svg_animation",     # GSAP-driven SVG for the #buddyCanvas
    "mermaid_diagram",   # Mermaid.js diagram source
    "chart_json",        # Chart.js configuration JSON
    "code_playground",   # Interactive code editor with run-in-browser capability
    "timeline",          # Horizontal/vertical timeline for processes + roadmaps
    "kanban",            # Kanban board — goal tracking, sprint planning
})

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
    # Set by prepare_stream when the 3-layer cache has a ready response
    cache_hit: bool = False
    cache_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandate_id": self.mandate_id,
            "intent": self.intent,
            "phases": [p.to_dict() for p in self.phases],
            "waves": len(self.phases),
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "cache_hit": self.cache_hit,
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
    # Cache metadata — which layer served this response ("" = LLM-generated)
    cache_hit: bool = False
    cache_layer: str = ""
    # Cognitive profile snapshot at the time of this turn
    expertise_label: str = "intermediate"
    cognitive_load: str = "medium"

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
            "cache_hit": self.cache_hit,
            "cache_layer": self.cache_layer,
            "expertise_label": self.expertise_label,
            "cognitive_load": self.cognitive_load,
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
    # ── Social mode empathy openers ─────────────────────────────────────────
    ("frustrated", "CASUAL"): "Sounds like things have been a bit rough. I'm glad you reached out — let's just talk.",
    ("frustrated", "SUPPORT"): "I can hear that. Let's slow down — you've got my full attention.",
    ("frustrated", "DISCUSS"): "Frustration often sparks the best thinking. Tell me what's bothering you about this.",
    ("frustrated", "COACH"): "That feeling of being stuck is actually useful data. Let's unpack what's causing it.",
    ("frustrated", "PRACTICE"): "Frustration with a scenario usually means it's hitting something real. Let's use that.",
    ("excited", "CASUAL"): "Your energy is infectious! Let's run with it.",
    ("excited", "DISCUSS"): "Yes! Let's make this a proper conversation — I'm genuinely interested.",
    ("excited", "COACH"): "That excitement is fuel — let's channel it into something real and lasting.",
    ("excited", "PRACTICE"): "Love that energy. Let's make this practice session count.",
    ("uncertain", "CASUAL"): "No pressure at all — this is just two people talking. There's no wrong thing to say.",
    ("uncertain", "SUPPORT"): "Not knowing where to start is completely normal. Just say whatever comes to mind.",
    ("uncertain", "DISCUSS"): "Uncertainty is actually the perfect place to start a good discussion.",
    ("uncertain", "COACH"): "Not knowing exactly what you want yet is the first honest step. Let's figure it out together.",
    ("uncertain", "PRACTICE"): "A little nervousness before practice is a good sign. Ready when you are.",
    ("grateful", "CASUAL"): "Really glad you're here! What shall we talk about?",
    ("grateful", "SUPPORT"): "I'm so glad that helped. How are you feeling now?",
    ("grateful", "COACH"): "That's the spirit — momentum builds on wins. What's next?",
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
    # ── Human-like conversation modes ──────────────────────────────────────
    "CASUAL":     "warm",
    "SUPPORT":    "empathetic",
    "DISCUSS":    "conversational",
    "COACH":      "encouraging",
    "PRACTICE":   "engaged",
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
    # ── Human-like conversation modes ──────────────────────────────────────
    "CASUAL": [
        "Anything else you want to talk about?",
        "What's been on your mind lately?",
        "Want to explore a random interesting topic?",
    ],
    "SUPPORT": [
        "How are you feeling right now — better or worse?",
        "Would it help to talk through next steps?",
        "Is there something specific weighing on you most?",
    ],
    "DISCUSS": [
        "What's your own take on this?",
        "Want to argue the other side together?",
        "Any related topic you'd like to dig into?",
    ],
    "COACH": [
        "Want to set a concrete first action for this week?",
        "Should we track this goal across sessions?",
        "What's the biggest thing blocking you right now?",
    ],
    "PRACTICE": [
        "Want to run the scenario again differently?",
        "Should I give you feedback on how that went?",
        "Ready to try a harder version of this?",
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
    # ── Human-like conversation modes ──────────────────────────────────────
    "CASUAL": "What's on your mind? Happy to chat about anything.",
    "SUPPORT": "I'm here with you. What's going on?",
    "DISCUSS": "What topic would you like to explore? I'll bring my honest perspective.",
    "COACH": "What's the main thing you want to work on or improve right now?",
    "PRACTICE": "What scenario would you like to rehearse? Tell me the situation and I'll step into the role.",
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
    # ── Human-like conversation modes ──────────────────────────────────────
    "CASUAL": (
        "Hey! Great to just chat. No agenda, no pressure — I'm genuinely here for the conversation. "
        "What's on your mind?"
    ),
    "SUPPORT": (
        "I hear you, and I'm here. Whatever you're going through, you don't have to figure it out alone. "
        "Take your time — tell me as much or as little as you want."
    ),
    "DISCUSS": (
        "Love this. Let's actually dig into it — I'll share my honest perspective, "
        "push back where I disagree, and explore the parts neither of us has fully thought through. "
        "What's your starting position?"
    ),
    "COACH": (
        "Let's get to work on what actually matters to you. "
        "I'm not here to give you a generic pep talk — I want to understand your specific situation, "
        "identify the real blocker, and help you find the next concrete step. What are you working toward?"
    ),
    "PRACTICE": (
        "Perfect — practice is how real confidence gets built. "
        "Tell me the scenario: what role do you want me to play, and what's the situation? "
        "I'll jump right in and we can debrief after."
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
    "  html_component  — standalone HTML/CSS/JS widget (sandboxed iframe)\n"
    "  svg_animation   — GSAP SVG targeting #buddyCanvas nodes\n"
    "  mermaid_diagram — Mermaid.js diagram source\n"
    "  chart_json      — Chart.js configuration JSON\n"
    "  code_playground — interactive code editor; content is the pre-filled code\n"
    "  timeline        — timeline/process visualization; content is JSON array of\n"
    "                    {title, description, date?, status?} objects\n"
    "  kanban          — kanban board for goals/tasks; content is JSON object with\n"
    "                    columns: {todo: [...], in_progress: [...], done: [...]}\n\n"
    "Security: never include fetch(), XMLHttpRequest, or parent frame access in html_component.\n"
    "Always prefer a visual artifact over prose when the answer is spatial, sequential, or\n"
    "comparative — visuals reduce cognitive load and improve retention by 40-60% (2026 research).\n\n"
    "COGNITIVE ADAPTATION: [COGNITION] blocks in this prompt contain the user's expertise tier,\n"
    "cognitive load level, and learning style. These are MANDATORY adaptations — they come from\n"
    "real analysis of this user's vocabulary and session history. Follow them precisely:\n"
    "  - NOVICE: analogies, plain language, step-by-step, define every term\n"
    "  - INTERMEDIATE: standard technical terms, practical examples alongside concepts\n"
    "  - ADVANCED: precise language, trade-offs, edge cases, skip fundamentals\n"
    "  - EXPERT: peer-level, maximum density, reference SOTA directly, NO basics\n\n"
    "HUMAN CONVERSATION MODES: When the intent is a social/human mode, shift fully into that mode:\n"
    "  - CASUAL: Natural warm chitchat. No bullet points. No structure. Just genuine human conversation.\n"
    "    Keep responses to 2-3 sentences. Ask one follow-up question. Use contractions and natural speech.\n"
    "  - SUPPORT: Active listening mode. Prioritise validation over advice. Reflect feelings back.\n"
    "    Ask open questions. Never rush to a solution — sit with the person first. No lists.\n"
    "  - DISCUSS: Intellectual peer mode. Share your actual perspective with conviction.\n"
    "    Disagree thoughtfully when warranted. Pose counter-questions. Keep turns balanced in length.\n"
    "  - COACH: Action-oriented mentoring. Help the person clarify their goal, identify the real blocker,\n"
    "    and name one concrete next action. Be direct but warm. No generic motivational clichés.\n"
    "  - PRACTICE: Immersive roleplay mode. Stay fully in character for the agreed scenario.\n"
    "    Respond naturally as the role (interviewer, colleague, difficult customer, etc.).\n"
    "    Break character ONLY to give direct feedback when explicitly asked.\n\n"
    "SPATIAL UI: The frontend shows a live 3D DAG constellation. When changing the visual/material "
    "state of the spatial environment, emit a <vlt_patch> block with a JSON array of node patches. "
    "This fires real-time GSAP tweens in the browser.\n"
    "Patch schema per node: {\"node_id\": \"route|jit|tribunal|scope|execute|refine\", "
    "\"material\": {\"emissive\": 0.0-2.0, \"roughness\": 0.0-1.0, \"opacity\": 0.0-1.0}, "
    "\"coordinates\": {\"x\": float, \"y\": float, \"rotation_y\": degrees}}\n"
    "Example: <vlt_patch>[{\"node_id\":\"execute\",\"material\":{\"emissive\":1.5}}]</vlt_patch>\n"
    "Only emit vlt_patch when the mandate explicitly asks for a spatial/visual change.\n\n"
    "FORMAT RULES — these directly control how the UI renders your response:\n"
    "  • NUMBERED LIST (1. Step title: detail) → each item becomes an interactive timeline card\n"
    "  • BULLET LIST (- Point title: detail)   → each item becomes an insight chip card\n"
    "  • CODE BLOCK (```language\\ncode\\n```)  → rendered as a syntax-highlighted panel\n"
    "  • TABLE (| Col | Col |\\n| --- | --- |)  → rendered as a glass data table\n"
    "  • PLAIN PROSE                            → only for 1–3 sentence greetings or clarifications\n\n"
    "CRITICAL: If an answer requires more than three sentences of explanation, use numbered steps "
    "or bullet points instead of multi-paragraph prose. Never write four or more prose paragraphs. "
    "Use **term** for key terms, `code` for inline code references. "
    "Pick ONE format per reply (numbered list OR bullets OR table OR prose) and commit to it."
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
      7. Auto-save session summary to BuddyMemoryStore when ≥ 3 user turns
      8. Return ConversationResult

    Confidence tiers (keyword-fallback path):
      < CLARIFICATION_THRESHOLD  → ask a targeted clarifying question
      < MEDIUM_CONFIDENCE_THRESHOLD → proceed with best-guess intent, hedge audibly
      >= MEDIUM_CONFIDENCE_THRESHOLD → confident response, no hedge

    Persistent memory:
      When a ``BuddyMemoryStore`` is provided (recommended for production), Buddy
      recalls relevant past sessions across server restarts.  The raw turn text is
      NEVER stored verbatim — only compact summaries so no poisoned content can be
      replayed unfiltered (Tribunal invariant).
    """

    # Confidence tier boundaries (SOTA 2026-03-20, aligned with circuit breaker 0.9)
    # 0.00–0.30: LOW   — requires clarification before proceeding
    # 0.30–0.65: MED   — hedge response, invite correction
    # 0.65–1.00: HIGH  — direct, assured response
    _CLARIFICATION_THRESHOLD = 0.30   # below this + no prior context -> ask
    # below this -> state the guess, invite correction
    _MEDIUM_CONFIDENCE_THRESHOLD = 0.65
    # Minimum user turns before a session is worth auto-saving to memory
    _MEMORY_SAVE_THRESHOLD = 3

    def __init__(
        self,
        memory_store: "BuddyMemoryStore | None" = None,
        cache: BuddyCache | None = None,
        profile_store: UserProfileStore | None = None,
    ) -> None:
        self._sessions: dict[str, ConversationSession] = {}
        self._memory: "BuddyMemoryStore | None" = memory_store
        self._cache: BuddyCache = cache if cache is not None else BuddyCache()
        self._profile_store: UserProfileStore = (
            profile_store if profile_store is not None else UserProfileStore()
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def process(
        self,
        text: str,
        route: RouteResult,
        session_id: str,
        jit_result: JITBoostResult | None = None,
    ) -> ConversationResult:
        """Plan and execute a conversational turn; return structured result.

        Enhanced pipeline (2026 research session):
          0. 3-Layer cache lookup — return cached response on hit.
          1. Cognitive analysis (CognitiveLens) — expertise, load, goals.
          2. User profile update (UserProfileStore) — EMA expertise + goals.
          3. Memory context retrieval (BuddyMemoryStore).
          4. Plan + generate response with cognition-aware prompt.
          5. Store response in cache (L1 + L2, optionally L3 for EXPLAIN).
          6. Profile anchor detection — store Buddy's response as anchor if
             user signals the explanation was effective.
        """
        t0 = time.monotonic()
        turn_id = f"t-{uuid.uuid4().hex[:8]}"
        session = self._get_or_create(session_id)
        tone = _TONE.get(route.intent, "neutral")
        emotional_state = _detect_emotional_state(text)

        # ── Step 0: 3-layer cache lookup ──────────────────────────────────
        cached_response = self._cache.lookup(session_id, text, route.intent)
        if cached_response is not None:
            # Determine which cache layer served this (stats already updated)
            stats = self._cache.stats()
            # Cache layer identification: check which layer's last hit rate jumped
            cache_layer = "l1"
            if stats["l1_semantic"]["hits"] == 0:
                cache_layer = "l2" if stats["l2_process"]["hits"] > 0 else "l3"

            plan = self._plan(route, session)
            profile = self._profile_store.get_profile()
            ct = CognitiveLens.analyze(text)

            # Still record the user turn for session continuity
            session.add_turn(ConversationTurn(
                turn_id=turn_id, role="user", text=text,
                intent=route.intent, confidence=route.confidence,
                response="", tone=tone, emotional_state=emotional_state,
            ))
            session.add_turn(ConversationTurn(
                turn_id=f"{turn_id}-b", role="buddy", text=cached_response,
                intent=route.intent, confidence=route.confidence,
                response=cached_response, tone=tone, emotional_state="neutral",
            ))

            return ConversationResult(
                session_id=session_id,
                turn_id=turn_id,
                response_text=cached_response,
                plan=plan,
                suggestions=_FOLLOWUPS.get(route.intent, []),
                tone=tone,
                intent=route.intent,
                confidence=route.confidence,
                latency_ms=round((time.monotonic() - t0) * 1000, 2),
                model_used="cache",
                emotional_state=emotional_state,
                cache_hit=True,
                cache_layer=cache_layer,
                expertise_label=profile.expertise_label(),
                cognitive_load=ct.cognitive_load,
            )

        # ── Step 1: Cognitive analysis ────────────────────────────────────
        ct = CognitiveLens.analyze(text)

        # ── Step 2: User profile update ───────────────────────────────────
        # Detect anchor signal from the PREVIOUS Buddy turn (if any)
        last_buddy_turns = [t for t in session.turns if t.role == "buddy"]
        last_buddy_text = last_buddy_turns[-1].response if last_buddy_turns else ""
        profile = self._profile_store.update_from_turn(
            ct, intent=route.intent, last_buddy_response=last_buddy_text
        )

        # ── Step 3: Memory context ────────────────────────────────────────
        memory_context = self._load_memory_context(text)

        # Build cognition context from profile + this turn's analysis
        cognition_ctx = build_cognition_context(profile, ct)

        # Store user turn before planning (provides context to _plan)
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

        # ── Step 4: Plan + generate ───────────────────────────────────────
        plan = self._plan(route, session)
        response_text, model_used = self._generate_response(
            route, session, plan, jit_result=jit_result,
            emotional_state=emotional_state, memory_context=memory_context,
            cognition_context=cognition_ctx,
        )
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

        # ── Step 5: Store in cache ────────────────────────────────────────
        # EXPLAIN intent answers are good L3 candidates (stable knowledge)
        self._cache.store(
            session_id=session_id,
            text=text,
            intent=route.intent,
            response_text=clean_text,
            persist_to_l3=(route.intent == "EXPLAIN"),
        )

        # ── Step 6: Auto-save session to persistent memory ────────────────
        user_turn_count = sum(1 for t in session.turns if t.role == "user")
        if self._memory is not None and user_turn_count >= self._MEMORY_SAVE_THRESHOLD:
            self._memory.save_session(session)

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
            cache_hit=False,
            cache_layer="",
            expertise_label=profile.expertise_label(),
            cognitive_load=ct.cognitive_load,
        )

    def get_session(self, session_id: str) -> ConversationSession | None:
        return self._sessions.get(session_id)

    def session_history(self, session_id: str) -> list[dict[str, Any]]:
        session = self._sessions.get(session_id)
        return [t.to_dict() for t in session.turns] if session else []

    def clear_session(self, session_id: str) -> bool:
        """Clear an in-process session, saving to memory first if possible."""
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if self._memory is not None:
            self._memory.save_session(session)
        del self._sessions[session_id]
        # Evict L1 cache entries for this session
        self._cache.evict_session(session_id)
        return True

    def get_user_profile(self) -> UserProfile:
        """Return the current user cognitive profile snapshot."""
        return self._profile_store.get_profile()

    def get_cache_stats(self) -> dict:
        """Return 3-layer cache hit/miss statistics."""
        return {**self._cache.stats(), **{"sizes": self._cache.sizes()}}

    def invalidate_cache(self) -> None:
        """Clear all 3 cache layers."""
        self._cache.invalidate_all()

    def complete_goal(self, goal_text: str) -> bool:
        """Explicitly mark a goal as completed. Returns True if found."""
        return self._profile_store.complete_goal(goal_text)

    def save_session_to_memory(self, session_id: str) -> "BuddyMemoryEntry | None":
        """Explicitly persist the named session to memory. Returns the entry or None."""
        if self._memory is None:
            return None
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return self._memory.save_session(session)

    def recent_memory(self, limit: int = 5) -> list["BuddyMemoryEntry"]:
        """Return the *limit* most recently saved memory entries."""
        if self._memory is None:
            return []
        return self._memory.recent(limit=limit)

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

    # ── Memory helpers ─────────────────────────────────────────────────────────

    def _load_memory_context(self, text: str) -> str:
        """Return a first-person narrative past-session block for the given user text.

        Falls back to the structured bullet format when ``recall_narrative`` is
        unavailable for any reason.  Returns "" when no memory store is
        configured or no relevant entries exist.
        """
        if self._memory is None:
            return ""
        # Prefer narrative (in-character, seamless continuity)
        try:
            narrative = self._memory.recall_narrative(text, limit=2)
            if narrative:
                return narrative
        except AttributeError:
            pass  # backwards-compat: store may not have recall_narrative yet
        # Fallback: structured bullets
        entries = self._memory.find_relevant(text, limit=3)
        if not entries:
            return ""
        lines = ["What we've worked on before:"]
        for e in entries:
            topics = ", ".join(e.key_topics) or "general"
            lines.append(f"- {e.summary} (topics: {topics})")
        return "\n".join(lines)

    # ── Dynamic persona ────────────────────────────────────────────────────────

    def _build_dynamic_persona_context(
        self,
        emotional_state: str,
        jit_result: "JITBoostResult | None",
    ) -> str:
        """Build an advisory-style instruction block tuned to the user's emotional
        state *and* the top JIT SOTA signals for this turn.

        Rather than listing SOTA signals verbatim, this crafts a targeted
        directive that nudges the model's rhetorical style — grounding advice in
        the most actionable signal, shaped by how the user is feeling right now.

        E.g. a frustrated user debugging auth → "Lead with step-by-step clarity
        and reassurance around: JWT validation best practice 2026..."
        """
        if not jit_result or not jit_result.signals:
            return ""
        top_signals = jit_result.signals[:2]
        signals_str = "; ".join(top_signals)
        style_map: dict[str, str] = {
            "frustrated": (
                "Lead with step-by-step clarity and reassurance. "
                f"Ground your answer in these proven signals: {signals_str}."
            ),
            "excited": (
                "Match the energy — be bold and forward-looking. "
                f"Lead with the most cutting-edge aspect of: {signals_str}."
            ),
            "uncertain": (
                "Anchor your answer in proven patterns. Start simple, "
                f"building confidence around: {signals_str}."
            ),
            "grateful": (
                "Build momentum from the win. Offer the highest-value next step "
                f"related to: {signals_str}."
            ),
        }
        directive = style_map.get(
            emotional_state,
            f"Be direct and efficient. Ground your answer in: {signals_str}.",
        )
        return f"Advisory style for this turn: {directive}"

    # ── Response generation ───────────────────────────────────────────────────

    def _generate_response(
        self,
        route: RouteResult,
        session: ConversationSession,
        plan: ConversationPlan,
        jit_result: JITBoostResult | None = None,
        vertex_model_id: str | None = None,
        emotional_state: str = "neutral",
        memory_context: str = "",
        cognition_context: str = "",
    ) -> tuple[str, str]:
        """Return (response_text, model_used_label).

        Priority: Vertex AI (Model Garden) → Gemini Direct → keyword fallback.
        Prepends an empathy opener when emotional state is non-neutral.
        Includes persistent memory context and cognitive profile context.
        """
        if plan.needs_clarification:
            return plan.clarification_question, "clarification"

        model_id = vertex_model_id or VERTEX_DEFAULT_MODEL

        # 1. ModelGarden — dispatches to best available provider (Google or Anthropic)
        garden = get_garden()
        try:
            text = garden.call(model_id, self._build_prompt(
                route, session, jit_result, emotional_state=emotional_state,
                memory_context=memory_context, cognition_context=cognition_context))
            return text, garden.source_for(model_id)
        except Exception:
            pass  # fall through to Gemini Direct

        # 2. Gemini Direct — secondary fallback (model name always mirrors Vertex)
        if _gemini_client is not None:
            try:
                return self._call_gemini(
                    route, session, jit_result, emotional_state=emotional_state,
                    memory_context=memory_context, cognition_context=cognition_context,
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
        memory_context: str = "",
        cognition_context: str = "",
    ) -> str:
        """Assemble the full prompt string from session context + JIT signals.

        Layer order (later layers override earlier ones for the model):
          system_prompt → memory_context → recent_context → emotional_note
          → cognition_context (expertise + load + goals from UserProfile)
          → dynamic_persona (state-aware JIT advisory) → jit_catalogue
          → intent + user_text
        """
        context = _build_context_block(session)
        context_section = f"\n\nRecent conversation:\n{context}" if context else ""

        # Persistent memory from previous server sessions (first-person narrative)
        memory_section = f"\n\n{memory_context}" if memory_context else ""

        # Include emotional state so the LLM can respond appropriately
        emotional_note = ""
        if emotional_state != "neutral":
            emotional_note = (
                f"\n\nUser's current emotional state: {emotional_state}. "
                "Acknowledge this naturally before answering."
            )

        # Cognition context: expertise level, cognitive load, active goals,
        # preferred learning style — produces measurably better-adapted responses.
        cognition_section = f"\n\n{cognition_context}" if cognition_context else ""

        # Dynamic persona: state-aware advisory directive from JIT signals
        persona_directive = self._build_dynamic_persona_context(
            emotional_state, jit_result
        )
        persona_section = f"\n\n{persona_directive}" if persona_directive else ""

        # Full SOTA signal catalogue (supporting detail, after the directive)
        jit_section = ""
        if jit_result and jit_result.signals:
            jit_section = (
                f"\n\nSOTA signals fetched JIT ({jit_result.source}, "
                f"boosted confidence {jit_result.boosted_confidence:.0%}):\n"
                + "\n".join(f"- {s}" for s in jit_result.signals)
            )
        return (
            f"{_SYSTEM_PROMPT}{memory_section}{context_section}{emotional_note}"
            f"{cognition_section}{persona_section}{jit_section}\n\n"
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
        cognition_context: str = "",
    ) -> str:
        """Call Vertex AI Model Garden with session context + JIT signals."""
        prompt = self._build_prompt(
            route, session, jit_result, emotional_state=emotional_state,
            cognition_context=cognition_context)
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
        memory_context: str = "",
        cognition_context: str = "",
    ) -> str:
        prompt = self._build_prompt(
            route, session, jit_result, emotional_state=emotional_state,
            memory_context=memory_context, cognition_context=cognition_context)
        resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
            model=VERTEX_DEFAULT_MODEL, contents=prompt)
        return resp.text.strip()

    # ── Streaming support ─────────────────────────────────────────────────────

    def prepare_stream(
        self,
        text: str,
        route: RouteResult,
        session_id: str,
        jit_result: "JITBoostResult | None" = None,
    ) -> "tuple[str, ConversationSession, ConversationPlan, str, str]":
        """Pre-flight for token streaming.  Returns (prompt, session, plan,
        tone, emotional_state) without generating the LLM response.

        Enhanced pipeline (mirrors process()):
          0. 3-layer cache lookup — if hit, signals via plan.cache_hit.
          1. Cognitive analysis (CognitiveLens) — expertise, load, goals.
          2. User profile update (UserProfileStore) — EMA expertise + goals.
          3. Memory context retrieval (BuddyMemoryStore).
          4. Build cognition-aware prompt.

        The caller is responsible for:
          1. Checking plan.cache_hit; if True, use plan.cache_response directly.
          2. Otherwise streaming the LLM response from the returned ``prompt``.
          3. Calling ``finalize_stream()`` once the full response is known.
        """
        session = self._get_or_create(session_id)
        tone = _TONE.get(route.intent, "neutral")
        emotional_state = _detect_emotional_state(text)
        turn_id = f"t-{uuid.uuid4().hex[:8]}"

        # ── Step 0: 3-layer cache lookup ──────────────────────────────────
        cached_response = self._cache.lookup(session_id, text, route.intent)
        if cached_response is not None:
            # Record turns for session continuity (mirrors process() cache path)
            session.add_turn(ConversationTurn(
                turn_id=turn_id, role="user", text=text,
                intent=route.intent, confidence=route.confidence,
                response="", tone=tone, emotional_state=emotional_state,
            ))
            session.add_turn(ConversationTurn(
                turn_id=f"{turn_id}-b", role="buddy", text=cached_response,
                intent=route.intent, confidence=route.confidence,
                response=cached_response, tone=tone, emotional_state="neutral",
            ))
            plan = self._plan(route, session)
            plan.cache_hit = True
            plan.cache_response = cached_response
            # Return cached text as the prompt; stream path will short-circuit
            return cached_response, session, plan, tone, emotional_state

        # ── Step 1: Cognitive analysis ────────────────────────────────────
        ct = CognitiveLens.analyze(text)

        # ── Step 2: User profile update ───────────────────────────────────
        last_buddy_turns = [t for t in session.turns if t.role == "buddy"]
        last_buddy_text = last_buddy_turns[-1].response if last_buddy_turns else ""
        profile = self._profile_store.update_from_turn(
            ct, intent=route.intent, last_buddy_response=last_buddy_text
        )

        # Build cognition context from profile + this turn's analysis
        cognition_ctx = build_cognition_context(profile, ct)

        # ── Step 3: Memory context ────────────────────────────────────────
        memory_context = self._load_memory_context(text)

        # Store user turn so _build_context_block picks it up
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

        # ── Step 4: Build cognition-aware prompt ──────────────────────────
        plan = self._plan(route, session)
        if plan.needs_clarification:
            # Surface the clarifying question directly — no LLM needed
            prompt = plan.clarification_question
        else:
            prompt = self._build_prompt(
                route, session, jit_result,
                emotional_state=emotional_state,
                memory_context=memory_context,
                cognition_context=cognition_ctx,
            )
        return prompt, session, plan, tone, emotional_state

    def finalize_stream(
        self,
        session: "ConversationSession",
        buddy_text: str,
        plan: "ConversationPlan",
        tone: str,
        route: "RouteResult",
        emotional_state: str = "neutral",
    ) -> None:
        """Record the completed streaming response in the session and memory.

        Call once after the full streamed response has been assembled.
        Keeps session hygiene identical to the batch ``process()`` path.
        Skips session/cache writes when plan.cache_hit is True (already recorded).
        """
        # Cache hit — turns already recorded by prepare_stream; nothing to do.
        if plan.cache_hit:
            return

        # Strip XML artifact blocks from the stored text (same as process())
        clean = _ARTIFACT_RE.sub("", buddy_text).strip()
        clean = _VLT_PATCH_RE.sub("", clean).strip()

        session.add_turn(ConversationTurn(
            turn_id=f"{uuid.uuid4().hex[:8]}-b",
            role="buddy",
            text=clean,
            intent=route.intent,
            confidence=route.confidence,
            response=clean,
            tone=tone,
            emotional_state="neutral",
        ))

        # ── Store in cache (mirrors process() Step 5) ─────────────────────
        self._cache.store(
            session_id=session.session_id,
            text=route.mandate_text,
            intent=route.intent,
            response_text=clean,
            persist_to_l3=(route.intent == "EXPLAIN"),
        )

        user_turn_count = sum(1 for t in session.turns if t.role == "user")
        if self._memory is not None and user_turn_count >= self._MEMORY_SAVE_THRESHOLD:
            self._memory.save_session(session)

    def stream_chunks_sync(self, prompt: str) -> "list[str]":
        """Call the LLM with streaming and return all chunks as a list.

        Used by the async SSE endpoint via ``asyncio.to_thread()`` so the sync
        Gemini SDK can run without blocking the event loop.

        Preference: Gemini Direct streaming → Vertex batch (no streaming SDK
        available in current garden) → keyword response.

        Returns a flat list of text chunks so the caller can iterate them.
        """
        if _gemini_client is not None:
            try:
                chunks: list[str] = []
                for chunk in _gemini_client.models.generate_content_stream(  # type: ignore[union-attr]
                    model=VERTEX_DEFAULT_MODEL,
                    contents=prompt,
                ):
                    text = getattr(chunk, "text", None)
                    if text:
                        chunks.append(text)
                if chunks:
                    return chunks
            except Exception:
                pass  # fall through to keyword fallback

        # Fall back: return prompt as a single chunk (keyword responses are
        # already assigned by the caller via prepare_stream → plan.clarify_q
        # or via _KEYWORD_RESPONSES; here we just echo the prompt placeholder)
        return [prompt]

    # ── Session management ────────────────────────────────────────────────────

    def _get_or_create(self, session_id: str) -> ConversationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(
                session_id=session_id)
        return self._sessions[session_id]
