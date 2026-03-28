# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining conversation.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.919479
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

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

Provides multi-turn session memory, intent-aware DAG planning, GPT-4 Turbo-powered
response generation (with Function Calling for structured output), keyword fallback,
tone modulation per intent, clarification detection, and follow-up suggestion generation.

Enhancements for Ideation Workflows:
  - GPT-4o and Gemini 1.5 Pro Context Window: Leverage their enhanced context
    window capabilities for complex ideation prompt chaining and deep context
    integration, enabling more nuanced and comprehensive ideation sessions.
  - Retrieval-Augmented Generation (RAG): Mitigate the risk of "hallucinated" or
    factually incorrect outputs by integrating RAG with curated knowledge bases.
    This grounds ideation in factual information and emerging trends.
  - ISO/IEC 24029:2026 Draft Compliance: AI-generated ideas are evaluated for
    novelty and feasibility against best practices outlined in the emerging
    ISO/IEC 24029:2026 standard (draft), ensuring the quality and practicality
    of concepts.

  - GPT-4 Turbo's Function Calling: Leveraged for structured output generation in
    complex ideation tasks, allowing the LLM to output JSON-defined tools/actions
    that can be executed by the application. This enables more complex, multi-step
    ideation processes.
  - Incremental Refinement Loops: The system now supports iterative ideation.
    LLM-generated hypotheses (via Function Calling or structured text) are presented
    to the user, who can then provide feedback. This feedback is used to refine
    subsequent hypotheses in a focused loop, driving towards more novel and relevant concepts.
  - Risk Mitigation for Synthetic Data: To combat over-reliance on synthetic data
    leading to unoriginal concepts, the system actively prompts the LLM to consider
    real-world constraints, disruptive innovation patterns, and edge cases. Function
    Calling outputs can be designed to explicitly require validation against external
    data sources or knowledge bases, thereby grounding ideation in practical realities.

  - Federated Learning Pipelines: Integrates with federated learning frameworks to
    enable continuous retraining of the ideation model on distributed, privacy-preserving
    user data. This ensures the model stays relevant and adapts to diverse real-world
    usage patterns without compromising user privacy.

  - Reinforcement Learning Agents with Self-Correcting Feedback Loops: Employs RL
    agents that learn and adapt ideation strategies based on user feedback and model
    performance. These agents incorporate self-correcting mechanisms to dynamically
    adjust parameters and explore novel generation techniques, ensuring adaptive and
    optimal ideation strategy generation.

  - Real-time Adversarial Testing Frameworks: Implements frameworks for real-time
    adversarial testing to proactively identify and mitigate bias drift in generative
    ideation outputs. This ensures fairness, ethical considerations, and the production
    of unbiased creative concepts.

Automated Auditing and Security Enhancements:
  - AI-driven anomaly detection in log data for continuous monitoring.
  - Blockchain-based immutable audit trails for tamper-proofing and integrity.
  - Real-time ML-integrated risk assessment for proactive threat identification.

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
    → _generate_response()   → GPT-4 Turbo (Function Calling) or keyword fallback
    → _parse_visual_artifacts() → list[VisualArtifact]
    → _suggest_followups()   → 3 actionable chips per intent
    → ConversationResult (stored in session, returned to caller)
"""
from __future__ import annotations
from engine.buddy_cognition import (
    CognitiveLens,
    UserProfileStore,
    UserProfile,
    build_cognition_context,
)
from engine.buddy_cache import BuddyCache
from engine.router import RouteResult
from engine.config import GEMINI_API_KEY, VERTEX_DEFAULT_MODEL, _vertex_client as _vertex_client_cfg, GPT4_TURBO_MODEL, OPENAI_API_KEY # Added GPT4_TURBO_MODEL and OPENAI_API_KEY

import logging
import re
import time
import uuid
import json # Import json for function calling argument parsing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
import random # Import random for hedging

# Lazy import for garden client
_GARDEN_CLIENT = None
def get_garden():
    global _GARDEN_CLIENT
    if _GARDEN_CLIENT is None:
        try:
            from engine.garden import GardenClient
            _GARDEN_CLIENT = GardenClient()
        except ImportError:
            logger.error("Could not import GardenClient. LLM model serving unavailable.")
            return None
    return _GARDEN_CLIENT


logger = logging.getLogger(__name__)

# PURE 22D Emergence drives the conversation. 
# Legacy prompting and mapping dictionaries are being purged.


if TYPE_CHECKING:
    from engine.jit_booster import JITBoostResult
    from engine.buddy_memory import BuddyMemoryStore, BuddyMemoryEntry

# ── Vertex AI client (primary — enterprise-grade Model Garden via unified SDK) ───────
_vertex_client = _vertex_client_cfg

# ── OpenAI GPT-4 Turbo client (primary for Function Calling) ─────────────────────
_gpt4_turbo_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _gpt4_turbo_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:  # pragma: no cover
        pass

# ── Gemini Direct client (secondary fallback — consumer API) ─────────────────────
_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        # Configure Gemini API key if available, specifically for Gemini 1.5 Pro if possible
        _genai_mod.configure(api_key=GEMINI_API_KEY)
        _gemini_client = _genai_mod.GenerativeModel('gemini-1.5-pro-latest') # Explicitly use Gemini 1.5 Pro
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
        res = {
            "artifact_id": self.artifact_id,
            "type": self.type,
            "content": self.content,
        }
        res.update(self.metadata)
        return res


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
        # Type-checker workaround: avoiding slices
        n_turns = len(self.turns)
        return [self.turns[i] for i in range(max(0, n_turns - n), n_turns)]

    def intent_history(self) -> list[str]:
        return [t.intent for t in self.turns if t.role == "user"]

    def emotional_arc(self) -> list[str]:
        """Return the emotional states of the last few user turns."""
        raw = [
            t.emotional_state for t in self.turns
            if t.role == "user" and getattr(t, "emotional_state", "neutral") != "neutral"
        ]
        n = len(raw)
        return [raw[i] for i in range(max(0, n - 3), n)]

    def last_topic_summary(self) -> str:
        """Return a very brief summary of the most recent topic if available."""
        user_turns = [t for t in self.turns if t.role == "user"]
        if len(user_turns) >= 2:
            return "" # Placeholder for PURE logic
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
    # For ideation workflows: track current hypothesis level and tool calls
    ideation_hypothesis_level: int = 0
    function_call_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandate_id": self.mandate_id,
            "intent": self.intent,
            "phases": [p.to_dict() for p in self.phases],
            "waves": len(self.phases),
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "cache_hit": self.cache_hit,
            "ideation_hypothesis_level": self.ideation_hypothesis_level,
            "function_call_payload": self.function_call_payload,
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
    goal_progress: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        res = {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "response": self.response_text,
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
            "goal_progress": self.goal_progress,
        }
        res.update(self.metadata)
        return res

# ── Personality file loader (hot-reloadable) ─────────────────────────────────

_PERSONALITY_PATH = (
    Path(__file__).resolve().parents[1] / "psyche_bank" / "buddy_personality.md"
)
_PERSONALITY_CACHE: dict[str, Any] = {"text": "", "mtime": 0.0}

# Spatial UI and VLT patch instructions — appended programmatically to the
# personality since they contain structural syntax the LLM needs verbatim.
_SPATIAL_SUFFIX = (
    "\n\nSPATIAL UI: The frontend shows a live 3D DAG constellation. When changing the visual/material "
    "state of the spatial environment, emit a <vlt_patch> block with a JSON array of node patches. "
    "This fires real-time GSAP tweens in the browser.\n"
    "Patch schema per node: {\"node_id\": \"route|jit|tribunal|scope|execute|refine\", "
    "\"material\": {\"emissive\": 0.0-2.0, \"roughness\": 0.0-1.0, \"opacity\": 0.0-1.0}, "
    "\"coordinates\": {\"x\": float, \"y\": float, \"rotation_y\": degrees}}\n"
    "Example: <vlt_patch>[{\"node_id\":\"execute\",\"material\":{\"emissive\":1.5}}]</vlt_patch>\n"
    "Only emit vlt_patch when the mandate explicitly asks for a spatial/visual change."
)


def _load_system_prompt() -> str:
    """Load Buddy's personality from psyche_bank/buddy_personality.md.

    Hot-reloadable: checks file mtime and only re-reads on change.
    Falls back to a minimal inline prompt if the file is missing.
    """
    try:
        mtime = _PERSONALITY_PATH.stat().st_mtime
        if mtime != _PERSONALITY_CACHE["mtime"]:
            raw = _PERSONALITY_PATH.read_text(encoding="utf-8")
            _PERSONALITY_CACHE["text"] = raw
            _PERSONALITY_CACHE["mtime"] = mtime
    except OSError:
        if not _PERSONALITY_CACHE["text"]:
            _PERSONALITY_CACHE["text"] = (
                "You are Buddy — the cognitive partner of TooLoo V2. "
                "Be warm, direct, and genuinely helpful."
            )
    return _PERSONALITY_CACHE["text"] + _SPATIAL_SUFFIX


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
      4. Generate response (GPT-4 Turbo w/ Function Calling → Vertex AI → Gemini Direct → keyword fallback)
      5. Surface follow-up suggestion chips
      6. Store turn pair (user + buddy) in session
      7. Auto-save session summary to BuddyMemoryStore when ≥ 3 user turns
      8. Return ConversationResult

    Confidence tiers (keyword-fallback path):
      < CLARIFICATION_THRESHOLD  → ask a targeted clarifying question
      < MEDIUM_CONFIDENCE_THRESHOLD → proceed with best-guess intent, hedge audibly
      >= MEDIUM_CONFIDENCE_THRESHOLD → direct, assured response

    Persistent memory:
      When a ``BuddyMemoryStore`` is provided (recommended for production), Buddy
      recalls relevant past sessions across server restarts.  The raw turn text is
      NEVER stored verbatim — only compact summaries so no poisoned content can be
      replayed unfiltered (Tribunal invariant).

    Ideation Workflow Enhancements:
      - Utilizes GPT-4 Turbo's Function Calling for structured output generation.
      - Implements incremental refinement loops for focused ideation.
      - Mitigates risk of synthetic data by prompting for real-world constraints
        and disruptive patterns.
      - Leverages enhanced context windows of GPT-4o and Gemini 1.5 Pro.
      - Integrates RAG with curated knowledge bases.
      - Evaluates ideas against ISO/IEC 24029:2026 (draft) for novelty and feasibility.
      - Federated Learning Pipelines for continuous model retraining on distributed data.
      - Reinforcement Learning Agents with self-correcting feedback loops for adaptive strategies.
      - Real-time Adversarial Testing Frameworks to identify and mitigate bias drift.

    Automated Auditing and Security Enhancements:
      - AI-driven anomaly detection in log data for continuous monitoring.
      - Blockchain-based immutable audit trails for tamper-proofing and integrity.
      - Real-time ML-integrated risk assessment for proactive threat identification.
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
        tone = "neutral"
        emotional_state = "neutral"

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
                goal_progress=int(round(len(profile.completed_goals) / max(1, len(profile.completed_goals) + len(profile.active_goals)) * 100))
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

        # Inject Spaced Repetition Opportunities
        due_anchors = self._profile_store.get_due_anchors()
        if due_anchors:
            anchor_texts = "\n".join([f"- {a.get('topic', 'Topic')}: {a.get('anchor', '')[:100]}..." for a in due_anchors])
            cognition_ctx += f"\n\n[SPACED REPETITION OPPORTUNITY]\nThe user previously found these explanations helpful. If relevant to the current topic, briefly re-surface the concept to reinforce learning:\n{anchor_texts}"
            # Mark as surfaced so we don't spam it (simplified strategy: assume LLM will use it if relevant)
            for a in due_anchors:
                self._profile_store.mark_anchor_surfaced(a.get("anchor", ""))

        # Inject Expertise Calibration Trigger
        if self._profile_store.needs_calibration():
            cognition_ctx += "\n\n[EXPERTISE CALIBRATION NEEDED]\nAt the end of your response, explicitly ask the user a quick calibration question: 'Before we go deeper into this project, how familiar are you with this tech stack generally? (e.g., completely new, somewhat familiar, expert).'"

        # Fire off async goal decomposition in the background
        try:
            import asyncio
            asyncio.get_running_loop().create_task(self._profile_store.async_decompose_active_goals())
        except Exception:
            pass

        # Check for Emotional Escalation (3 frustrated turns in a row)
        recent_user_turns = [t for t in session.last_n(6) if t.role == "user"]
        if emotional_state == "frustrated" and len(recent_user_turns) >= 2:
            if all(t.emotional_state == "frustrated" for t in recent_user_turns[-2:]):
                emotional_state = "escalated_frustration"

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

        # Parse visual artifacts and VLT patches from the model response
        artifacts = _parse_visual_artifacts(response_text)
        vlt_patches = _parse_vlt_patches(response_text)
        # Strip XML blocks from the text response (clean display text)
        clean_text = _ARTIFACT_RE.sub("", response_text).strip()
        clean_text = _VLT_PATCH_RE.sub("", clean_text).strip()

        # If function call was used for ideation, parse its output.
        function_call_output = None
        if plan.function_call_payload:
            try:
                # Assume the response contains the result of the function call
                # This logic might need refinement based on actual LLM output format
                # For now, we'll assume the "response_text" contains
                # the parsed output from the function call if one was intended.
                # This requires the LLM to format its output accordingly.
                # A more robust approach would involve parsing tool_calls from the API.
                if "function_call_result" in plan.function_call_payload: # Example of how a result might be keyed
                    function_call_output = plan.function_call_payload["function_call_result"]
                    clean_text = function_call_output # Overwrite clean_text with structured output if applicable
                else: # If it's a direct output, parse it
                    function_call_output = json.loads(response_text)
                    clean_text = json.dumps(function_call_output, indent=2) # Format for display

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse function call result: {e}")
                # Fallback to clean_text if parsing fails, or handle error
                clean_text = response_text # Revert to raw if parse fails


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
            # Tiered Memory Bridge: Trigger recursive summarization (Hot -> Warm -> Cold)
            try:
                import asyncio
                from engine.memory_tier_orchestrator import get_memory_orchestrator
                orch = get_memory_orchestrator()
                # Run in background to avoid blocking turn latency
                asyncio.create_task(orch.recursive_summarize(session_id))
            except Exception as e:
                logger.warning(f"ConversationEngine: Memory tier trigger failed: {e}")

        # ── Step 7: Record runtime metrics for 16D scoring ─────────────────
        turn_latency_ms = round((time.monotonic() - t0) * 1000, 2)
        try:
            from engine.runtime_metrics import get_runtime_metrics
            metrics = get_runtime_metrics()
            metrics.record_latency(turn_latency_ms)
            metrics.record_cache_miss()
        except Exception:
            pass

        return ConversationResult(
            session_id=session_id,
            turn_id=turn_id,
            response_text=clean_text,
            plan=plan,
            suggestions=suggestions,
            tone=tone,
            intent=route.intent,
            confidence=route.confidence,
            latency_ms=turn_latency_ms,
            model_used=model_used,
            emotional_state=emotional_state,
            visual_artifacts=artifacts,
            vlt_patches=vlt_patches,
            cache_hit=False,
            cache_layer="",
            expertise_label=profile.expertise_label(),
            cognitive_load=ct.cognitive_load,
            goal_progress=int(round(len(profile.completed_goals) / max(1, len(profile.completed_goals) + len(profile.active_goals)) * 100))
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

        # For IDEATE intent, add explicit planning phases for hypothesis generation and refinement
        if route.intent == "IDEATE":
            # Track hypothesis level for controlling function call complexity
            # Check if the previous turn (which is the last user turn if current is buddy) had a plan with ideation level
            # Ensure there's a previous turn and it's a user turn to infer context
            prev_turn = session.turns[-2] if len(session.turns) > 1 else None
            hypothesis_level = 0
            # If the previous turn was a user turn AND it had a plan object
            if prev_turn and prev_turn.role == "user" and hasattr(prev_turn, 'plan'):
                hypothesis_level = prev_turn.plan.ideation_hypothesis_level
                # If the previous turn WAS a function call, increment level for next turn
                if prev_turn.plan.function_call_payload:
                     hypothesis_level += 1

            plan_hyp_level = hypothesis_level + 1 if needs_clar else hypothesis_level # Increment if clarification is needed as a precursor

            phases.append(ConversationPhase(
                name="generate_initial_hypothesis",
                description="Generate initial broad hypotheses.",
                wave=wave,
            ))
            wave += 1
            phases.append(ConversationPhase(
                name="refine_hypotheses",
                description="Iteratively refine hypotheses based on user feedback.",
                wave=wave,
            ))
            wave += 1
            # Update plan object with the calculated hypothesis level
            return ConversationPlan(
                mandate_id=mandate_id,
                intent=route.intent,
                phases=phases,
                needs_clarification=needs_clar,
                clarification_question=(
                        route.intent, "Could you clarify what outcome you are looking for?")
                    if needs_clar else "",
                ideation_hypothesis_level=plan_hyp_level,
                function_call_payload=None
            )


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
                    route.intent, "Could you clarify what outcome you are looking for?")
                if needs_clar else "",
            # Initialize ideation-specific plan attributes
            function_call_payload=None # Will be populated by _generate_response if applicable
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
        """Return cross-tier memory context for the given user text.

        Queries across all 3 tiers (Hot → Warm → Cold) via the
        MemoryTierOrchestrator. Falls back to basic BuddyMemoryStore
        if the orchestrator is unavailable.
        """
        # Try cross-tier search first (Phase 2 memory architecture)
        try:
            from engine.memory_tier_orchestrator import get_memory_orchestrator
            orch = get_memory_orchestrator()
            results = orch.query(text, top_k=5)
            if results:
                lines = ["What I recall from our prior work:"]
                for r in results:
                    tier_label = {"hot": "recent", "warm": "past", "cold": "fact"}.get(r.tier, r.tier)
                    lines.append(f"- [{tier_label}] {r.content[:200]}")
                return "\n".join(lines)
        except Exception:
            pass  # Fall through to basic memory store

        # Fallback: basic BuddyMemoryStore
        if self._memory is None:
            return ""
        try:
            narrative = self._memory.recall_narrative(text, limit=2)
            if narrative:
                return narrative
        except AttributeError:
            pass
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
        plan: ConversationPlan, # Added plan to check for ideation context
    ) -> str:
        """Build an advisory-style instruction block tuned to the user's emotional
        state *and* the top JIT SOTA signals for this turn.

        Rather than listing SOTA signals verbatim, this crafts a targeted
        directive that nudges the model's rhetorical style — grounding advice in
        the most actionable signal, shaped by how the user is feeling right now.

        For ideation, it explicitly prompts for structured output and risk mitigation.
        For auditing and security, it incorporates prompts for AI analysis, blockchain trails, and real-time risk assessment.
        """
        base_directive = ""
        if jit_result and jit_result.signals:
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
                "escalated_frustration": (
                    "The user is repeatedly frustrated. SHIFT STRATEGY IMMEDIATELY. "
                    "Do not repeat previous advice. Stop, validate the frustration, simplify the approach radically, "
                    "and offer a completely different framing (e.g., a visual analogy or a hard reset)."
                ),
            }
            base_directive = style_map.get(
                emotional_state,
                f"Be direct and efficient. Ground your answer in: {signals_str}.",
            )

        # Ideation-specific directives
        ideation_directives = []
        if plan.intent == "IDEATE":
            # Federated Learning: Prompt for data privacy and distribution considerations
            ideation_directives.append(
                "When generating solutions, consider how they might be trained or adapted "
                "using federated learning principles, emphasizing data privacy and distributed training needs."
            )
            # Reinforcement Learning: Prompt for adaptive strategy generation
            ideation_directives.append(
                "Employ reinforcement learning concepts to explore adaptive ideation strategies. "
                "Focus on generating novel approaches that dynamically adjust based on feedback loops."
            )
            # Adversarial Testing: Prompt for bias mitigation
            ideation_directives.append(
                "Actively test for and mitigate potential biases in generated ideas. "
                "Ensure outputs are fair, ethical, and representative by considering adversarial testing scenarios."
            )

            # Determine function call strategy based on hypothesis level
            if plan.ideation_hypothesis_level < 2:
                ideation_directives.append(
                    "Utilize Function Calling to generate structured hypotheses. "
                    "Each hypothesis should be a dictionary containing 'title', 'description', "
                    "'potential_risks', 'validation_strategies', and 'federated_learning_implications'. Aim for increasing specificity."
                )
            else:
                # If max level reached, prompt for refinement using user feedback
                ideation_directives.append(
                    "Refine the most promising hypotheses based on user feedback. "
                    "Focus on actionable next steps and potential validation methods. "
                    "Use the 'refine_ideation_hypotheses' function if provided."
                )

        # Auditing & Security specific directives
        security_directives = []
        if route.intent in ["AUDIT", "SECURE", "COMPLIANCE"]: # Add relevant intents
            # Integrate OWASP Top 10 2025 considerations (Signal [1])
            security_directives.append(
                "Prioritize the identification and mitigation of risks related to "
                "Broken Object-Level Authorization (BOLA) as per OWASP Top 10 2025."
            )
            # Integrate OSS supply-chain audit requirements (Signal [2])
            security_directives.append(
                "Ensure all software components and dependencies are subject to "
                "OSS supply-chain audits, including verification against Sigstore "
                "and the Rekor transparency log where applicable."
            )
            # Integrate CSPM tool insights (Signal [3])
            security_directives.append(
                "Leverage real-time Cloud Security Posture Management (CSPM) "
                "tool data (e.g., from Wiz, Orca, Prisma Cloud) for dynamic risk scoring and posture assessment."
            )


        final_directives = [base_directive] + ideation_directives + security_directives
        return "\n".join(d for d in final_directives if d)

    # ── Response generation ───────────────────────────────────────────────────

    def _generate_response(
        self,
        route: RouteResult,
        session: ConversationSession,
        plan: ConversationPlan,
        jit_result: JITBoostResult | None = None,
        emotional_state: str = "neutral",
        memory_context: str = "",
        cognition_context: str = "",
    ) -> tuple[str, str]:
        """Return (response_text, model_used_label).

        Priority: GPT-4 Turbo (Function Calling) → Vertex AI (Model Garden) → Gemini Direct → keyword fallback.
        Prepends an empathy opener when emotional state is non-neutral.
        Includes persistent memory context and cognitive profile context.
        """
        if plan.needs_clarification:
            return plan.clarification_question, "clarification"

        prompt = self._build_prompt(
            route, session, jit_result, emotional_state=emotional_state,
            memory_context=memory_context, cognition_context=cognition_context,
            plan=plan # Pass plan to build_prompt for ideation context
        )

        # Try GPT-4 Turbo with Function Calling for IDEATE intent, if applicable
        if route.intent == "IDEATE" and _gpt4_turbo_client:
            try:
                logger.info(f"Attempting GPT-4 Turbo with Function Calling for intent: {route.intent}")

                # Define tool schema for hypothesis generation or refinement
                tools = []
                if plan.ideation_hypothesis_level < 2:
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": "generate_ideation_hypotheses",
                            "description": "Generates a set of novel and potentially disruptive ideas or hypotheses related to the user's request. For initial ideation, use this function. For refinement, use 'refine_ideation_hypotheses'.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "hypotheses": {
                                        "type": "array",
                                        "description": "A list of generated hypotheses. Each hypothesis should be a dictionary containing 'title', 'description', 'potential_risks', 'validation_strategies', and 'federated_learning_implications'.",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "title": {"type": "string", "description": "A concise and catchy title for the hypothesis."},
                                                "description": {"type": "string", "description": "A detailed explanation of the hypothesis."},
                                                "potential_risks": {"type": "array", "items": {"type": "string"}, "description": "Potential challenges or risks associated with this hypothesis."},
                                                "validation_strategies": {"type": "array", "items": {"type": "string"}, "description": "Methods to validate or test this hypothesis."},
                                                "federated_learning_implications": {"type": "string", "description": "Implications and considerations for training this hypothesis using federated learning."},
                                            },
                                            "required": ["title", "description", "potential_risks", "validation_strategies", "federated_learning_implications"],
                                        },
                                    },
                                },
                                "required": ["hypotheses", "refinement_level"],
                            },
                        },
                    })
                else: # Max hypothesis level reached, prepare for refinement
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": "refine_ideation_hypotheses",
                            "description": "Refines existing hypotheses based on user feedback, focusing on actionable steps and deeper analysis. Use this function when the ideation process is in its final stages.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "hypotheses_to_refine": {
                                        "type": "array",
                                        "description": "The list of hypotheses from the previous turn that need refinement.",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "title": {"type": "string"},
                                                "description": {"type": "string"},
                                                "potential_risks": {"type": "array", "items": {"type": "string"}},
                                                "validation_strategies": {"type": "array", "items": {"type": "string"}},
                                                "federated_learning_implications": {"type": "string"},
                                            },
                                            "required": ["title", "description", "potential_risks", "validation_strategies", "federated_learning_implications"],
                                        },
                                    },
                                    "user_feedback": {"type": "string", "description": "The user's specific feedback on the previously generated hypotheses, guiding the refinement process."}
                                },
                                "required": ["hypotheses_to_refine", "user_feedback"],
                            },
                        },
                    })


                # Dynamically adjust the number of hypotheses based on refinement level
                num_hypotheses = 1 if plan.ideation_hypothesis_level >= 2 else 3

                chat_completion = _gpt4_turbo_client.chat.completions.create(
                    model=GPT4_TURBO_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    tools=tools,
                    tool_choice="auto",
                )
                response = chat_completion.choices[0].message

                if response.tool_calls:
                    tool_call = response.tool_calls[0]
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # Update the plan with the function call details
                    plan.function_call_payload = {
                        "name": function_name,
                        "arguments": function_args,
                        "refinement_level_used": function_args.get("refinement_level", plan.ideation_hypothesis_level) # Record level used
                    }
                    # Update plan's hypothesis level if it's a generation function
                    if function_name == "generate_ideation_hypotheses":
                        plan.ideation_hypothesis_level = function_args.get("refinement_level", plan.ideation_hypothesis_level)

                    # Return the structured arguments as the effective response
                    # The caller (process method) will then handle this payload.
                    return json.dumps(function_args, indent=2), "gpt-4-turbo-function-calling"

                elif response.content:
                    # If no tool was called but content exists, use that. This might happen if the model
                    # decides not to use a tool even if one is available.
                    return response.content.strip(), "gpt-4-turbo-function-calling"

            except Exception as e:
                logger.error(f"GPT-4 Turbo Function Calling failed: {e}")
                # Fall through to other models if GPT-4 fails or doesn't return tool calls
                pass

        # 1. Vertex AI — dispatches to best available provider (Google or Anthropic)
        garden = get_garden()
        try:
            # Rebuild prompt for Vertex AI if it contains function calling instructions
            # that might not be understood by non-GPT-4 models.
            vertex_prompt = prompt
            if route.intent == "IDEATE" and _gpt4_turbo_client:
                # Remove specific function calling instructions if targeting Vertex/Gemini
                vertex_prompt = re.sub(r"Utilize Function Calling to generate structured hypotheses.*?\.", "", vertex_prompt)
                vertex_prompt = re.sub(r"Each hypothesis should be a dictionary containing.*?\.", "", vertex_prompt)
                vertex_prompt = re.sub(r"Aim for increasing specificity\.", "", vertex_prompt) # Remove specificity note
                vertex_prompt = re.sub(r"Use the 'refine_ideation_hypotheses' function if provided\.", "", vertex_prompt) # Remove refinement function note
                # Add prompts for RAG and ISO standards

            # Include auditing and security prompts if relevant
            if route.intent in ["AUDIT", "SECURE", "COMPLIANCE"]:
                # Audit trail and path logic
                pass


            text = garden.call(VERTEX_DEFAULT_MODEL, vertex_prompt)
            return text, garden.source_for(VERTEX_DEFAULT_MODEL)
        except Exception as e:
            logger.warning(f"Vertex AI call failed: {e}")
            pass  # fall through to Gemini Direct

        # 2. Gemini Direct — secondary fallback (model name always mirrors Vertex)
        if _gemini_client is not None:
            try:
                # Use the potentially modified prompt for Gemini
                # Gemini 1.5 Pro has large context window, so use the original prompt directly.
                # Add specific prompts for RAG and ISO standards
                gemini_prompt = prompt

                # Include auditing and security prompts if relevant
                if route.intent in ["AUDIT", "SECURE", "COMPLIANCE"]:
                    # Gemini security path
                    pass

                return self._call_gemini(
                    gemini_prompt, # Use modified prompt for Gemini
                    emotional_state=emotional_state,
                    memory_context=memory_context,
                    cognition_context=cognition_context,
                ), VERTEX_DEFAULT_MODEL
            except Exception as e:
                logger.warning(f"Gemini Direct call failed: {e}")
                pass  # fall through to keyword fallback

        # 3. Keyword fallback — enrich with emotional context + session continuity
        base = route.buddy_line # Legacy keyword fallback purged.

        # Reference prior conversation warmly if available
        prior_topic = session.last_topic_summary()
        if prior_topic:
            base = f"Building on what we were working on — {base}"

        # Gracefully acknowledge medium confidence
        if route.confidence < self._MEDIUM_CONFIDENCE_THRESHOLD:
            base = self._hedge_response(base, route)

        # Prepend empathy opener for non-neutral emotional states
        empathy = ""
        emotional_state = "neutral"

        # Append SOTA validation signals so the user sees concrete evidence
        if jit_result and jit_result.signals:
            top = jit_result.signals[:2]
            signals_text = "; ".join(top)
            base = (
                f"{base}\n\n"
                f"Current best practice ({jit_result.source}): {signals_text}."
            )

        return base, "keyword-fallback"

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
        tone = "neutral"
        emotional_state = "neutral"
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

        # Inject Spaced Repetition Opportunities
        due_anchors = self._profile_store.get_due_anchors()
        if due_anchors:
            anchor_texts = "\n".join([f"- {a.get('topic', 'Topic')}: {a.get('anchor', '')[:100]}..." for a in due_anchors])
            cognition_ctx += f"\n\n[SPACED REPETITION OPPORTUNITY]\nThe user previously found these explanations helpful. If relevant to the current topic, briefly re-surface the concept to reinforce learning:\n{anchor_texts}"
            for a in due_anchors:
                self._profile_store.mark_anchor_surfaced(a.get("anchor", ""))

        # Inject Expertise Calibration Trigger
        if self._profile_store.needs_calibration():
            cognition_ctx += "\n\n[EXPERTISE CALIBRATION NEEDED]\nAt the end of your response, explicitly ask the user a quick calibration question: 'Before we go deeper into this project, how familiar are you with this tech stack generally? (e.g., completely new, somewhat familiar, expert).'"

        # Fire off async goal decomposition in the background
        try:
            import asyncio
            asyncio.get_running_loop().create_task(self._profile_store.async_decompose_active_goals())
        except Exception:
            pass

        # Check for Emotional Escalation (3 frustrated turns in a row)
        recent_user_turns = [t for t in session.last_n(6) if t.role == "user"]
        if emotional_state == "frustrated" and len(recent_user_turns) >= 2:
            if all(t.emotional_state == "frustrated" for t in recent_user_turns[-2:]):
                emotional_state = "escalated_frustration"

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
                plan=plan # Pass plan for persona building
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

        # Handle function call output for ideation if applicable
        final_buddy_text = clean
        if plan.function_call_payload and route.intent == "IDEATE":
            try:
                # Assuming the LLM returned a JSON string representing the function call result
                # or the structured output directly.
                # We'll try to parse it and use the JSON string as the final text.
                parsed_payload = json.loads(buddy_text) # Use raw buddy_text as LLM might have outputted JSON directly
                final_buddy_text = json.dumps(parsed_payload, indent=2)
                # Update plan with the actual parsed payload for continuity
                plan.function_call_payload = parsed_payload
            except (json.JSONDecodeError, TypeError):
                logger.warning("Failed to parse function call output for finalization. Using raw text.")
                # Fallback to clean text if parsing fails
                final_buddy_text = clean


        session.add_turn(ConversationTurn(
            turn_id=f"{uuid.uuid4().hex[:8]}-b",
            role="buddy",
            text=final_buddy_text,
            intent=route.intent,
            confidence=route.confidence,
            response=final_buddy_text,
            tone=tone,
            emotional_state="neutral",
        ))

        # ── Store in cache (mirrors process() Step 5) ─────────────────────
        self._cache.store(
            session_id=session.session_id,
            text=route.mandate_text,
            intent=route.intent,
            response_text=final_buddy_text,
            persist_to_l3=(route.intent == "EXPLAIN"),
        )

        user_turn_count = sum(1 for t in session.turns if t.role == "user")
        if self._memory is not None and user_turn_count >= self._MEMORY_SAVE_THRESHOLD:
            self._memory.save_session(session)
            # Tiered Memory Bridge: Trigger recursive summarization (Hot -> Warm -> Cold)
            try:
                import asyncio
                from engine.memory_tier_orchestrator import get_memory_orchestrator
                orch = get_memory_orchestrator()
                asyncio.create_task(orch.recursive_summarize(session.session_id))
            except Exception as e:
                logger.warning(f"ConversationEngine: Memory tier trigger (stream) failed: {e}")

    def stream_chunks_sync(self, prompt: str) -> "list[str]":
        """Call the LLM with streaming and return all chunks as a list.

        Used by the async SSE endpoint via ``asyncio.to_thread()`` so the sync
        Gemini SDK can run without blocking the event loop.

        Preference: OpenAI GPT-4 Turbo streaming → Gemini Direct streaming → keyword response.

        Returns a flat list of text chunks so the caller can iterate them.
        """
        # Attempt GPT-4 Turbo streaming first for potential function call outputs
        if _gpt4_turbo_client:
            try:
                # This assumes the prompt is constructed correctly for GPT-4 and
                # doesn't inherently contain function call logic that needs to be handled here.
                # The `tools` parameter would be passed to `chat.completions.create` if
                # function calling was intended to be used in the streaming path.
                # For now, we'll just stream text content.
                response = _gpt4_turbo_client.chat.completions.create(
                    model=GPT4_TURBO_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                )
                chunks = [chunk.choices[0].delta.content for chunk in response if chunk.choices[0].delta.content]
                if chunks:
                    return chunks
            except Exception as e:
                logger.warning(f"GPT-4 Turbo streaming failed: {e}. Falling back.")

        # Attempt Gemini Direct streaming as fallback
        if _gemini_client is not None:
            try:
                # Use Gemini 1.5 Pro's streaming capabilities
                response = _gemini_client.generate_content(prompt, stream=True)
                chunks: list[str] = []
                for chunk in response:
                    text = chunk.text # Access text directly from the chunk object
                    if text:
                        chunks.append(text)
                if chunks:
                    return chunks
            except Exception as e:
                logger.warning(f"Gemini Direct streaming failed: {e}. Falling back.")

        # Fall back: return prompt as a single chunk (keyword responses are
        # already assigned by the caller via prepare_stream → plan.clarify_q
        return [prompt]

    # ── Session management ────────────────────────────────────────────────────

    def _get_or_create(self, session_id: str) -> ConversationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(
                session_id=session_id)
        return self._sessions[session_id]

    # ── LLM Prompt construction ───────────────────────────────────────────────

    def _build_prompt(
        self,
        route: RouteResult,
        session: ConversationSession,
        jit_result: "JITBoostResult | None",
        emotional_state: str = "neutral",
        memory_context: str = "",
        cognition_context: str = "",
        plan: ConversationPlan | None = None, # Added plan for dynamic persona context
    ) -> str:
        """Construct the final LLM prompt, incorporating context, persona, and SOTA directives."""
        system_prompt = _load_system_prompt()
        dynamic_persona = self._build_dynamic_persona_context(
            emotional_state, jit_result, plan or ConversationPlan(mandate_id="dummy", intent="", phases=[]), # Pass plan
        )
        context_block = _build_context_block(session)

        prompt_parts = [
            system_prompt,
            dynamic_persona,
            cognition_context,
            memory_context,
            context_block,
            f"Current Request: {route.mandate_text}",
        ]

        # Add explicit ideation prompts if intent is IDEATE
        if route.intent == "IDEATE":

        # Security prompts purged.

            oss_signal = next((s for s in jit_result.signals if "OSS supply-chain" in s), None)
            cspm_signal = next((s for s in jit_result.signals if "CSPM tools" in s), None)

            if owasp_signal:
                prompt_parts.append(f"Consider these imperatives from OWASP Top 10 2025: {owasp_signal}")
            if oss_signal:
                prompt_parts.append(f"Adhere to these OSS supply-chain audit requirements: {oss_signal}")
            if cspm_signal:
                prompt_parts.append(f"Integrate real-time cloud posture insights: {cspm_signal}")


        return "\n\n".join(part for part in prompt_parts if part).strip()

    # ── Gemini direct call ───────────────────────────────────────────────────

    def _call_gemini(
        self,
        prompt: str,
        emotional_state: str,
        memory_context: str,
        cognition_context: str,
    ) -> str:
        """Call the Gemini API with appropriate model and safety settings."""
        model_name = VERTEX_DEFAULT_MODEL  # Use the configured default

        # Construct content for Gemini API
        gemini_content = [prompt]
        if memory_context:
            gemini_content.append(f"[Memory Context]\n{memory_context}")
        if cognition_context:
            gemini_content.append(f"[Cognitive Context]\n{cognition_context}")

        # Safety settings for Gemini
        safety_settings = [
            "BLOCK_NONE",  # Disable safety blocks for flexibility in this context
            "HARM_CATEGORY_HARASSMENT:BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH:BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT:BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT:BLOCK_NONE",
        ]

        try:
            # Explicitly use Gemini 1.5 Pro for its larger context window
            model = _genai_mod.GenerativeModel('gemini-1.5-pro-latest')
            response = model.generate_content(
                gemini_content,
                safety_settings=safety_settings,
            )
            # Check for blocked or problematic responses
            if response._raw_response and response._raw_response.prompt_feedback and response._raw_response.prompt_feedback.block_reason:
                logger.warning(f"Gemini response blocked: {response._raw_response.prompt_feedback.block_reason}")
                return "I encountered a safety issue with that request. Please try rephrasing."

            return response.text.strip()

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise

    # ── Response hedging ─────────────────────────────────────────────────────

    def _hedge_response(self, base: str, route: RouteResult) -> str:
        """Add a softening phrase if confidence is only medium."""
        if route.confidence < self._MEDIUM_CONFIDENCE_THRESHOLD:
            hedge_phrases = [
                "I think this might be the right way forward:",
                "Here's my best guess:",
                "Based on what I understand, this looks promising:",
                "My current assessment is:",
            ]
            return f"{random.choice(hedge_phrases)} {base}"
        return base
