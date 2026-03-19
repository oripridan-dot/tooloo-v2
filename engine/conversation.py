"""
engine/conversation.py — Conversational Buddy process engine.

Provides multi-turn session memory, intent-aware DAG planning, Gemini-powered
response generation (keyword fallback), tone modulation per intent, clarification
detection, and follow-up suggestion generation.

Pipeline per turn:
  ConversationEngine.process(text, route, session_id)
    → _needs_clarification?  → build clarifying question (wave 0)
    → _plan()                → ConversationPlan (waves: understand → respond → suggest)
    → _generate_response()   → Gemini-2.0-flash or keyword fallback
    → _suggest_followups()   → 3 actionable chips per intent
    → ConversationResult (stored in session, returned to caller)
"""
from __future__ import annotations

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_count": len(self.turns),
            "created_at": self.created_at,
            "intent_history": self.intent_history(),
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
        }


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
        "Scaffold tests for this?",
        "Add type annotations?",
        "Set up a CI/CD pipeline?",
    ],
    "DEBUG": [
        "Add logging to trace the failure path?",
        "Add a regression test to lock the fix?",
        "Generate a root-cause summary?",
    ],
    "AUDIT": [
        "Generate a full dependency licence report?",
        "Open issues for each finding?",
        "Produce a remediation priority ranking?",
    ],
    "DESIGN": [
        "Create a component storybook entry?",
        "Suggest a dark-mode variant?",
        "Audit colour contrast for WCAG 2.1 AA?",
    ],
    "EXPLAIN": [
        "Create a diagram for this?",
        "Produce a runbook from this explanation?",
        "Generate a quiz to validate understanding?",
    ],
    "IDEATE": [
        "Build a prototype for one of these ideas?",
        "Create a risk / effort matrix?",
        "Research existing art for the top idea?",
    ],
    "SPAWN_REPO": [
        "Generate a GitHub Actions workflow?",
        "Scaffold a README template?",
        "Create a contributing guide?",
    ],
    "BLOCKED": [
        "Reset the circuit breaker via the toolbar",
        "Check recent mandates for the trigger pattern",
        "Review CIRCUIT_BREAKER_THRESHOLD in engine/config.py",
    ],
}

_CLARIFICATION_Q: dict[str, str] = {
    "BUILD": "Which component or service should I build — do you have a spec or example?",
    "DEBUG": "Can you share the error message, stack trace, or steps to reproduce?",
    "AUDIT": "Which aspect should I audit — security, dependencies, performance, or cost?",
    "DESIGN": "What are the target platform and design-system constraints?",
    "EXPLAIN": "What is your current understanding so I can pitch the explanation correctly?",
    "IDEATE": "What constraints or goals should shape the ideas I generate?",
    "SPAWN_REPO": "What tech stack, licence, and initial structure do you have in mind?",
}

_KEYWORD_RESPONSES: dict[str, str] = {
    "BUILD": (
        "I will implement that, breaking the work into recon → design → generate → validate waves. "
        "Tribunal will scan each node for OWASP violations before execution proceeds."
    ),
    "DEBUG": (
        "Entering analytical mode — I will trace the failure path, identify the root cause, "
        "and apply a minimal patch. A regression test will be added to lock the fix."
    ),
    "AUDIT": (
        "Running a precise audit — scanning for security misconfigs, stale dependencies, "
        "and licence issues. Findings will be ranked by severity with remediation steps."
    ),
    "DESIGN": (
        "Switching to creative mode — I will analyse the requirements and produce a "
        "component-level design. WCAG 2.1 AA contrast and responsive behaviour will be validated."
    ),
    "EXPLAIN": (
        "In pedagogical mode — I will walk you through the concept layer by layer, "
        "starting from first principles. Ask if you'd prefer a diagram or a runbook."
    ),
    "IDEATE": (
        "Entering exploratory mode — generating and scoring multiple strategic approaches. "
        "Each idea includes a risk/effort estimate and a concrete next step."
    ),
    "SPAWN_REPO": (
        "Architecting a new repository — I will scaffold the project structure, "
        "CI/CD pipeline, and documentation baseline. Tribunal validates the generated code."
    ),
    "BLOCKED": (
        "The circuit breaker has tripped. Reset the breaker via the toolbar before submitting "
        "new mandates. Review CIRCUIT_BREAKER_THRESHOLD in engine/config.py if this recurs."
    ),
}

_SYSTEM_PROMPT = (
    "You are Buddy, the conversational intelligence layer of TooLoo V2 — a SOTA mandate "
    "planning and execution engine. You are precise, constructive, and terse. You do not pad "
    "responses. You always reason about the most direct path to the user's goal. Never expose "
    "internal implementation details unless specifically asked. Respond in at most 3 sentences "
    "unless a longer answer is strictly necessary."
)


def _build_context_block(session: ConversationSession) -> str:
    """Return a compact, recent-turn summary for the LLM prompt."""
    recent = session.last_n(4)
    if not recent:
        return ""
    lines = []
    for t in recent:
        if t.role == "user":
            lines.append(f"User ({t.intent}): {t.text}")
        elif t.role == "buddy" and t.response:
            lines.append(f"Buddy: {t.response}")
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

        # Store user turn before planning (provides context)
        session.add_turn(ConversationTurn(
            turn_id=turn_id,
            role="user",
            text=text,
            intent=route.intent,
            confidence=route.confidence,
            response="",
            tone=tone,
        ))

        plan = self._plan(route, session)
        response_text, model_used = self._generate_response(
            route, session, plan, jit_result=jit_result)
        suggestions = _FOLLOWUPS.get(route.intent, [])

        session.add_turn(ConversationTurn(
            turn_id=f"{turn_id}-b",
            role="buddy",
            text=response_text,
            intent=route.intent,
            confidence=route.confidence,
            response=response_text,
            tone=tone,
        ))

        return ConversationResult(
            session_id=session_id,
            turn_id=turn_id,
            response_text=response_text,
            plan=plan,
            suggestions=suggestions,
            tone=tone,
            intent=route.intent,
            confidence=route.confidence,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            model_used=model_used,
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
    ) -> tuple[str, str]:
        """Return (response_text, model_used_label).

        Priority: Vertex AI (Model Garden) → Gemini Direct → keyword fallback.
        """
        if plan.needs_clarification:
            return plan.clarification_question, "clarification"

        model_id = vertex_model_id or VERTEX_DEFAULT_MODEL

        # 1. ModelGarden — dispatches to best available provider (Google or Anthropic)
        garden = get_garden()
        try:
            text = garden.call(model_id, self._build_prompt(
                route, session, jit_result))
            return text, garden.source_for(model_id)
        except Exception:
            pass  # fall through to Gemini Direct

        # 2. Gemini Direct — secondary fallback (model name always mirrors Vertex)
        if _gemini_client is not None:
            try:
                return self._call_gemini(route, session, jit_result), VERTEX_DEFAULT_MODEL
            except Exception:
                pass  # fall through to keyword fallback

        prior = session.intent_history()
        context_note = f" (following up on {prior[-2]})" if len(
            prior) >= 2 else ""
        base = _KEYWORD_RESPONSES.get(route.intent, route.buddy_line)
        response = base.replace(
            "I will", f"I will{context_note}", 1) if context_note else base

        # Gracefully acknowledge medium confidence — like a human who makes a
        # reasonable guess but keeps the door open to correction.
        if route.confidence < self._MEDIUM_CONFIDENCE_THRESHOLD:
            response = self._hedge_response(response, route)

        # Append SOTA validation signals so the user sees the concrete evidence
        if jit_result and jit_result.signals:
            top = jit_result.signals[:2]
            signals_text = "; ".join(top)
            response = (
                f"{response}\n\n"
                f"SOTA validation ({jit_result.source}): {signals_text}."
            )

        return response, "keyword-fallback"

    def _hedge_response(self, response: str, route: RouteResult) -> str:
        """Prefix response with a human-like confidence acknowledgment."""
        pct = round(route.confidence * 100)
        # Choose the hedge phrasing based on confidence band
        if pct <= 20:
            opener = (
                f"I\'m not certain what you\'re after (only ~{pct}\u202f% match on "
                f"{route.intent}), but here\'s my best attempt — correct me freely."
            )
        elif pct <= 40:
            opener = (
                f"Reading this as {route.intent} (~{pct}\u202f% confident). "
                f"If I\'ve got the intent wrong, just say so and I\'ll re-route."
            )
        else:
            opener = (
                f"Treating this as {route.intent} (about {pct}\u202f% match). "
                f"Let me know if you meant something else."
            )
        return f"{opener} {response}"

    def _build_prompt(
        self,
        route: RouteResult,
        session: ConversationSession,
        jit_result: JITBoostResult | None = None,
    ) -> str:
        """Assemble the full prompt string from session context + JIT signals."""
        context = _build_context_block(session)
        context_section = f"\n\nRecent conversation:\n{context}" if context else ""
        jit_section = ""
        if jit_result and jit_result.signals:
            jit_section = (
                f"\n\nSOTA signals fetched JIT ({jit_result.source}, "
                f"boosted confidence {jit_result.boosted_confidence:.0%}):\n"
                + "\n".join(f"- {s}" for s in jit_result.signals)
            )
        return (
            f"{_SYSTEM_PROMPT}{context_section}{jit_section}\n\n"
            f"Intent: {route.intent} (confidence {route.confidence:.0%})\n"
            f"User: {route.mandate_text}"
        )

    def _call_vertex(
        self,
        route: RouteResult,
        session: ConversationSession,
        jit_result: JITBoostResult | None = None,
        model_id: str = "",
    ) -> str:
        """Call Vertex AI Model Garden with session context + JIT signals."""
        prompt = self._build_prompt(route, session, jit_result)
        resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
            model=model_id or VERTEX_DEFAULT_MODEL, contents=prompt
        )
        return resp.text.strip()

    def _call_gemini(
        self,
        route: RouteResult,
        session: ConversationSession,
        jit_result: JITBoostResult | None = None,
    ) -> str:
        context = _build_context_block(session)
        context_section = f"\n\nRecent conversation:\n{context}" if context else ""
        jit_section = ""
        if jit_result and jit_result.signals:
            jit_section = (
                f"\n\nSOTA signals fetched JIT ({jit_result.source}, "
                f"boosted confidence {jit_result.boosted_confidence:.0%}):\n"
                + "\n".join(f"- {s}" for s in jit_result.signals)
            )
        prompt = (
            f"{_SYSTEM_PROMPT}{context_section}{jit_section}\n\n"
            f"Intent: {route.intent} (confidence {route.confidence:.0%})\n"
            f"User: {route.mandate_text}"
        )
        resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
            model=VERTEX_DEFAULT_MODEL, contents=prompt)
        return resp.text.strip()

    # ── Session management ────────────────────────────────────────────────────

    def _get_or_create(self, session_id: str) -> ConversationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(
                session_id=session_id)
        return self._sessions[session_id]
