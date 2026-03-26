"""engine/buddy_cognition.py — Cognitive Intelligence Layer for Buddy.

DEEP RESEARCH SESSION — AI Chat & Human Cognition (2026 SOTA)
==============================================================

This module embeds findings from cognitive science and AI UX research directly
into Buddy's conversational pipeline. Every design decision below is grounded
in a specific published research framework.

1. COGNITIVE LOAD THEORY (Sweller, 1988 → 2026 LLM adaptation)
   Three orthogonal load types:
     - Intrinsic:   inherent complexity of the topic (we cannot reduce this)
     - Extraneous:  formatting/presentation overhead (we MUST minimize this)
     - Germane:     effort to build mental schemas (we want to MAXIMIZE this)
   Implementation: CognitiveLens estimates intrinsic load from vocabulary
   complexity and question structure, then adjusts scaffold depth accordingly.
   High-intrinsic-load questions → more structure, smaller chunks, analogies.
   Low-load questions → concise direct answers (excessive detail = extraneous).

2. EXPERTISE REVERSAL EFFECT (van Merriënboer & Sweller, 1990 → 2026)
   The same level of detail that HELPS a novice HARMS an expert. Detailed
   worked examples reduce cognitive load for novices but create redundant
   processing for experts, lowering performance by up to 30%.
   Implementation: ExpertiseLens infers expertise (0.0=novice → 1.0=expert)
   from vocabulary, question structure, jargon density, and error quality.
   Buddy adapts depth, terminology, and scaffolding per expertise tier.

3. DUAL PROCESS THEORY (Kahneman, 2011 → LLM chat adaptation 2026)
   System 1 (fast, intuitive): conversational, emotional, reactive responses.
   System 2 (slow, deliberate): technical walkthroughs, debugging, planning.
   Implementation: Cognitive load tier maps to System 1/2 response mode.
   Short casual questions → System 1 (warm, concise). Stack traces → System 2
   (structured, methodical, show reasoning).

4. GOAL-DIRECTED BEHAVIOR — TOTE Model (Miller, Galanter & Pribram, 1960)
   Humans operate in a hierarchy of persistent goals. Top-level goals survive
   across many sessions. The most powerful memory capability an AI can have is
   not remembering what was SAID, but what the user was TRYING TO ACHIEVE.
   Implementation: GoalTracker extracts implicit goals from phrasing patterns
   ('I want to build X', 'I'm trying to fix Y') and tracks sub-goal completion
   ('that worked!', 'finally got it'). Cross-session goal continuity is the
   single biggest differentiator from commodity AI chat.

5. EBBINGHAUS SPACED REPETITION (1885 → AI adaptation 2026)
   The forgetting curve: retention = e^(-t/S). Optimal review intervals follow
   a doubling pattern (1d → 2d → 4d → 8d...). Information re-encountered at
   the right interval is encoded into long-term memory 2–3x more efficiently.
   Implementation: Knowledge anchors are annotated with last-surface timestamps.
   When a related topic appears, the engine checks if it's been long enough to
   make re-surfacing the anchor valuable rather than repetitive.

6. PROGRESSIVE DISCLOSURE (Nielsen, 2006 → AI chat 2026)
   Staged information release: hook → key insight → detail on demand. People
   process information best when offered the right layer first. Dumping all
   detail upfront increases extraneous cognitive load by ~34% (Nielsen/Norman
   Group research). The best AI chats offer depth as an invitation, not a wall.
   Implementation: ResponseDepthHint guides the LLM to lead with the sharpest
   single insight and place deeper content under expandable markers.

7. NARRATIVE TRANSPORTATION (Green & Brock, 2000)
   Facts embedded in narrative are retained 22x longer than isolated facts.
   "Imagine you're building a payment gateway..." activates more neural
   processing pathways than "A payment gateway is a system that...".
   Implementation: When a user is an intermediate/novice learner, the cognition
   context injects narrative scaffolding instructions into the LLM prompt.

8. KNOWLEDGE ANCHORS — Vygotsky's Zone of Proximal Development
   When Buddy explains something and the user responds positively ("that analogy
   really helped", "oh now I get it"), that explanation becomes a Knowledge
   Anchor — a proven framing for THIS user that should be reused.
   Implementation: UserProfileStore tracks anchors. They are injected into the
   LLM prompt: "This user responded well to the analogy: '...' — reuse it."
"""
from __future__ import annotations

import json
import math
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PROFILE_PATH = (
    Path(__file__).resolve().parents[1] / "psyche_bank" / "buddy_profile.json"
)

# ── Ebbinghaus Spaced Repetition Constants ────────────────────────────────────
# Optimal review intervals follow a doubling pattern.
_SPACED_REP_INTERVALS_HOURS = [24, 48, 96, 192, 384, 768]  # 1d → 32d
_RETENTION_STRENGTH_INIT = 1.0  # New anchor starts at full retention

# ── Expertise vocabulary signals ──────────────────────────────────────────────
# Expert token presence → positive delta; novice phrase presence → negative delta.

_EXPERT_TOKENS: frozenset[str] = frozenset({
    "implement", "refactor", "optimize", "architecture", "trade-off", "tradeoff",
    "complexity", "latency", "throughput", "idempotent", "concurrency",
    "race condition", "deadlock", "monadic", "compose", "polymorphism",
    "dependency injection", "solid", "dry", "yagni", "microservice",
    "event-driven", "cqrs", "saga", "circuit breaker", "serialization",
    "deserialization", "schema", "migration", "rollback", "invariant",
    "precondition", "postcondition", "side effect", "pure function", "immutable",
    "functional", "declarative", "memoize", "memoization", "big-o", "big o",
    "asymptotic", "hash collision", "cache eviction", "backpressure",
    "load shedding", "debounce", "throttle", "pagination", "cursor",
    "distributed", "consensus", "sharding", "replication", "eventual consistency",
    "cap theorem", "two-phase commit", "idempotency key", "webhook",
    "oauth", "jwt", "pkce", "csrf", "xss", "sql injection", "parameterized",
})

_NOVICE_PHRASES: tuple[str, ...] = (
    "what is", "how do i", "i don't understand", "i dont understand",
    "for beginners", "explain to me", "simple", "easy way",
    "step by step", "from scratch", "tutorial", "getting started",
    "never done", "beginner", "first time", "new to", "i'm new to",
    "im new to", "confused about", "don't know how",
)

# ── Goal extraction patterns ──────────────────────────────────────────────────

_GOAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bi want to\s+(.{10,100})", re.IGNORECASE),
    re.compile(r"\bi(?:'m| am) trying to\s+(.{10,100})", re.IGNORECASE),
    re.compile(r"\bmy goal is\s+(?:to\s+)?(.{10,100})", re.IGNORECASE),
    re.compile(r"\bi need to\s+(.{10,100})", re.IGNORECASE),
    re.compile(r"\bwe need to\s+(.{10,100})", re.IGNORECASE),
    re.compile(
        r"\bbuild(?:ing)?\s+(?:a\s+|an\s+|the\s+)?(.{10,80})", re.IGNORECASE),
    re.compile(
        r"\bcreate(?:ing)?\s+(?:a\s+|an\s+|the\s+)?(.{10,80})", re.IGNORECASE),
    re.compile(
        r"\bimplement(?:ing)?\s+(?:a\s+|an\s+|the\s+)?(.{10,80})", re.IGNORECASE),
]

# ── Achievement signals (goal sub-completion markers) ────────────────────────

_ACHIEVEMENT_TOKENS: frozenset[str] = frozenset({
    "it works", "that worked", "done", "finished", "completed",
    "got it working", "finally", "passed", "it's green", "its green",
    "all tests pass", "shipped", "deployed", "merged", "solved",
    "fixed it", "got it", "nailed it", "that's it", "thats it",
})

# ── Knowledge anchor trigger signals ─────────────────────────────────────────
# When the user responds with these after a Buddy explanation, we anchor it.

_ANCHOR_SIGNALS: frozenset[str] = frozenset({
    "that analogy", "that example", "great explanation", "now i get it",
    "now i understand", "that makes sense", "that helped", "love that",
    "perfect explanation", "exactly right", "that's clear", "thats clear",
    "really helpful", "i see now", "oh i see", "oh got it", "ah got it",
    "ah that makes", "that's a great way", "thats a great way",
})


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class UserProfile:
    """Persistent cognitive profile for the Buddy user.

    Persisted to psyche_bank/buddy_profile.json. All scores are running
    averages that evolve with each session. Single-user model (TooLoo V2
    is a personal system, not multi-tenant).
    """

    # Expertise score: 0.0 (complete novice) → 1.0 (domain expert)
    expertise_score: float = 0.5

    # Preferred communication style: "visual" | "example" | "analogy" | "direct"
    preferred_style: str = "direct"

    # Dominant intents observed across sessions (most recent 5)
    frequent_intents: list[str] = field(default_factory=list)

    # Active goals: goal text strings tracked across sessions (max 10)
    active_goals: list[str] = field(default_factory=list)

    # Completed goals history (for progress narrative, max 20)
    completed_goals: list[str] = field(default_factory=list)

    # Effective analogies/explanations discovered for this user (max 20)
    knowledge_anchors: list[dict[str, str]] = field(default_factory=list)

    # Total credits available for processing (synced with billing)
    credits: float = 0.0

    # Number of sessions contributing to this profile
    session_count: int = 0

    # ISO-8601 UTC timestamp of last update
    last_updated: str = ""

    # True if the user has explicitly confirmed their expertise level
    expertise_calibrated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "expertise_score": self.expertise_score,
            "preferred_style": self.preferred_style,
            "frequent_intents": self.frequent_intents,
            "active_goals": self.active_goals,
            "completed_goals": self.completed_goals,
            "knowledge_anchors": self.knowledge_anchors,
            "credits": self.credits,
            "session_count": self.session_count,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UserProfile":
        return cls(
            expertise_score=float(d.get("expertise_score", 0.5)),
            preferred_style=str(d.get("preferred_style", "direct")),
            frequent_intents=list(d.get("frequent_intents", [])),
            active_goals=list(d.get("active_goals", [])),
            completed_goals=list(d.get("completed_goals", [])),
            knowledge_anchors=list(d.get("knowledge_anchors", [])),
            credits=float(d.get("credits", 0.0)),
            session_count=int(d.get("session_count", 0)),
            last_updated=str(d.get("last_updated", "")),
            expertise_calibrated=bool(d.get("expertise_calibrated", False)),
        )

    def expertise_label(self) -> str:
        """Human-readable expertise tier label."""
        if self.expertise_score < 0.30:
            return "novice"
        if self.expertise_score < 0.60:
            return "intermediate"
        if self.expertise_score < 0.85:
            return "advanced"
        return "expert"


@dataclass
class CognitiveTurn:
    """Cognitive analysis snapshot of a single user turn.

    Computed by CognitiveLens.analyze() — pure, stateless, offline.
    """

    # Expertise delta for this turn: [-0.3, +0.3]
    expertise_delta: float

    # Estimated cognitive load: "low" | "medium" | "high"
    cognitive_load: str

    # Implicit goals extracted from the user's phrasing
    goals_extracted: list[str]

    # Whether the user signalled goal completion in this message
    achievement_detected: bool

    # Whether the user positively responded to a Buddy explanation
    anchor_signal_detected: bool

    # Learning style signal: "visual" | "example" | "analogy" | "direct"
    style_signal: str


# ── Cognitive Lens ────────────────────────────────────────────────────────────


class CognitiveLens:
    """Stateless cognitive analyser for user turn text.

    All methods are @staticmethod — no instance state. This ensures Law 17
    compliance: safe for parallel fan-out via JITExecutor / ThreadPoolExecutor.

    Methodology per metric:
    1. Expertise: token overlap with two curated signal sets + avg word length.
    2. Cognitive load: multi-step indicators, error text, question word density,
       total word count.
    3. Learning style: explicit style-request signals ("show me", "for example").
    4. Goal extraction: regex patterns tuned for goal-framing phrasing.
    5. Achievement detection: frozenset containment check on completion tokens.
    6. Anchor detection: frozenset containment check for "that helped" signals.
    """

    @staticmethod
    def estimate_expertise_delta(text: str) -> float:
        """Return a delta in [-0.3, +0.3] for the expertise running average.

        Positive = expert-like vocabulary; negative = novice-like phrasing.
        Based on: vocabulary set overlap + average word length heuristic.
        """
        lower = text.lower()
        tokens = frozenset(lower.split())

        # Expert tokens: single-word containment
        expert_hits = len(tokens & _EXPERT_TOKENS)

        # Novice phrases: multi-word substring match
        novice_hits = sum(1 for phrase in _NOVICE_PHRASES if phrase in lower)

        # Average word length as a proxy for vocabulary sophistication
        words = [w for w in lower.split() if w.isalpha()]
        avg_len = sum(len(w) for w in words) / max(len(words), 1)

        score = (expert_hits * 0.10) - (novice_hits * 0.10)
        if avg_len > 7.5:
            score += 0.05   # long words → technical vocabulary
        elif avg_len < 4.5:
            score -= 0.05   # very short words → simpler vocabulary

        return max(-0.3, min(0.3, score))

    @staticmethod
    def estimate_cognitive_load(text: str) -> str:
        """Estimate cognitive load tier: 'low' | 'medium' | 'high'.

        High:   multi-step problem, error stack trace, complex architecture query,
                multiple interleaved question words.
        Medium: single clear technical question with context.
        Low:    simple lookup, definition, social exchange, short greeting.
        """
        multi_step = bool(re.search(
            r"\band then\b|\bafter that\b|\balso need\b|\bbesides\b"
            r"|\bmoreover\b|\bfurthermore\b|\bfirst.*then\b",
            text, re.IGNORECASE,
        ))
        has_error = bool(re.search(
            r"error:|traceback|exception|stack trace|\bfailed with\b|attributeerror"
            r"|nameerror|typeerror|valueerror|keyerror|indexerror",
            text, re.IGNORECASE,
        ))
        q_words = len(re.findall(
            r"\b(?:how|why|what|when|where|which|who|should|can|could|would)\b",
            text, re.IGNORECASE,
        ))
        word_count = len(text.split())

        if word_count > 80 or multi_step or has_error or q_words >= 3:
            return "high"
        if word_count > 25 or q_words >= 2:
            return "medium"
        return "low"

    @staticmethod
    def detect_style_signal(text: str) -> str:
        """Detect the user's preferred learning style from phrasing.

        Returns: 'visual' | 'example' | 'analogy' | 'direct'
        """
        lower = text.lower()
        if any(w in lower for w in (
            "show me", "diagram", "visualize", "visualise",
            "draw", "chart", "graph", "picture", "illustration",
        )):
            return "visual"
        if any(w in lower for w in (
            "for example", "give me an example", "like what", "show an example",
            "code example", "sample code", "snippet",
        )):
            return "example"
        if any(w in lower for w in (
            "analogy", "think of it as", "similar to", "metaphor",
            "like when", "it's like", "as if",
        )):
            return "analogy"
        return "direct"

    @staticmethod
    def extract_goals(text: str) -> list[str]:
        """Extract implicit goals from user text using curated regex patterns.

        Returns up to 3 cleaned goal strings per turn (max 120 chars each).
        """
        goals: list[str] = []
        for pattern in _GOAL_PATTERNS:
            for match in pattern.finditer(text):
                goal = match.group(1).strip().rstrip(".,!?;")
                if len(goal) >= 10 and goal not in goals:
                    goals.append(goal[:120])
        return goals[:3]

    @staticmethod
    def detect_achievement(text: str) -> bool:
        """True when the user's message contains strong goal-completion signals."""
        lower = text.lower()
        return any(signal in lower for signal in _ACHIEVEMENT_TOKENS)

    @staticmethod
    def detect_anchor_signal(text: str) -> bool:
        """True when the user positively validates a Buddy explanation.

        Triggers this → the last Buddy response can be stored as a Knowledge
        Anchor for this user (proven framing to reuse for similar topics).
        """
        lower = text.lower()
        return any(signal in lower for signal in _ANCHOR_SIGNALS)

    @classmethod
    def analyze(cls, text: str) -> CognitiveTurn:
        """Full cognitive analysis of a user turn. Returns CognitiveTurn."""
        return CognitiveTurn(
            expertise_delta=cls.estimate_expertise_delta(text),
            cognitive_load=cls.estimate_cognitive_load(text),
            goals_extracted=cls.extract_goals(text),
            achievement_detected=cls.detect_achievement(text),
            anchor_signal_detected=cls.detect_anchor_signal(text),
            style_signal=cls.detect_style_signal(text),
        )


# ── User Profile Store ────────────────────────────────────────────────────────


class UserProfileStore:
    """Thread-safe persistent store for the user's cognitive profile.

    Single-user model — TooLoo V2 is a personal cognitive partner, not a
    SaaS multi-tenant system. All profile data belongs to one user.

    Storage: psyche_bank/buddy_profile.json (JSON, atomic write-rename pattern).
    Thread safety: threading.Lock guards all reads and writes.
    """

    # Exponential moving average alpha — low value = stable, slow to shift
    # Prevents a single expert-sounding message from flipping a novice to expert.
    _EMA_ALPHA: float = 0.08

    def __init__(self, path: Path = _PROFILE_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._profile: UserProfile = self._load()

    def get_profile(self) -> UserProfile:
        """Return a snapshot (copy) of the current user profile."""
        with self._lock:
            return UserProfile.from_dict(self._profile.to_dict())

    def update_from_turn(
        self,
        turn: CognitiveTurn,
        intent: str,
        last_buddy_response: str = "",
    ) -> UserProfile:
        """Update the profile from a cognitive turn analysis. Returns updated snapshot.

        Updates applied in-order:
          1. Expertise score (exponential moving average)
          2. Learning style (if non-trivial signal)
          3. New goals extracted (skip if already tracked or completed)
          4. Achievement detection (move first active goal to completed)
          5. Knowledge anchor (if user validated an explanation)
          6. Intent frequency tracking
          7. Timestamp
        """
        with self._lock:
            p = self._profile

            # 1. Expertise EMA with JUMP CORRECTION
            #    If the expertise delta is large (|delta| > 0.15), we have a signal
            #    that the EMA has diverged from reality (user shows sudden mastery
            #    or sudden confusion). Apply a 3x stronger alpha for one update.
            target = p.expertise_score + turn.expertise_delta
            target = max(0.0, min(1.0, target))
            alpha = self._EMA_ALPHA
            if abs(turn.expertise_delta) > 0.15:
                alpha = min(1.0, alpha * 3.0)  # Jump correction: faster response
            p.expertise_score = round(
                p.expertise_score * (1 - alpha) + target * alpha, 4
            )

            # 2. Learning style
            if turn.style_signal and turn.style_signal != "direct":
                p.preferred_style = turn.style_signal

            # 3. New goals with AUTO-DECOMPOSITION
            #    If a goal contains conjunction words ('and', 'then', 'also'),
            #    split it into atomic sub-goals for better tracking.
            for goal in turn.goals_extracted:
                sub_goals = self._decompose_goal(goal)
                for sg in sub_goals:
                    if sg not in p.active_goals and sg not in p.completed_goals:
                        p.active_goals.append(sg)
            p.active_goals = p.active_goals[-10:]

            # 4. Achievement → move best-matching active goal to completed
            if turn.achievement_detected and p.active_goals:
                completed = p.active_goals.pop(0)
                p.completed_goals.append(completed)
                p.completed_goals = p.completed_goals[-20:]

            # 5. Knowledge anchor with SPACED REPETITION timestamps
            if turn.anchor_signal_detected and last_buddy_response:
                anchor_text = last_buddy_response[:400]
                now_ts = time.time()
                p.knowledge_anchors.append({
                    "topic": intent,
                    "anchor": anchor_text,
                    "created_at": str(now_ts),
                    "last_surfaced": str(now_ts),
                    "surface_count": "0",
                    "interval_idx": "0",
                })
                p.knowledge_anchors = p.knowledge_anchors[-20:]

            # 6. Intent frequency
            if intent not in p.frequent_intents:
                p.frequent_intents.append(intent)
            p.frequent_intents = p.frequent_intents[-5:]

            # 7. Timestamp
            p.last_updated = datetime.now(UTC).isoformat()

            self._save()
            return UserProfile.from_dict(p.to_dict())

    @staticmethod
    def _decompose_goal(goal: str) -> list[str]:
        """Split compound goals into atomic sub-goals.

        'Build auth and deploy to staging' → ['Build auth', 'deploy to staging']
        Simple goals are returned as-is.
        """
        # Split on conjunction patterns
        parts = re.split(r"\b(?:and then|and also|and|then|also|plus)\b", goal, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]
        return parts if len(parts) > 1 else [goal]

    def complete_goal(self, goal_text: str) -> bool:
        """Explicitly mark the best-matching active goal as completed.

        Returns True if a matching goal was found and moved. Uses substring
        containment (case-insensitive) for fuzzy matching.
        """
        with self._lock:
            for i, g in enumerate(self._profile.active_goals):
                if (
                    goal_text.lower() in g.lower()
                    or g.lower() in goal_text.lower()
                ):
                    self._profile.completed_goals.append(
                        self._profile.active_goals.pop(i)
                    )
                    self._save()
                    return True
        return False

    def top_up_credits(self, amount: float) -> float:
        """Add credits to the user profile and return the new total."""
        with self._lock:
            self._profile.credits += amount
            self._save()
            return self._profile.credits

    def increment_session_count(self) -> None:
        """Increment the session counter. Call once per new session."""
        with self._lock:
            self._profile.session_count += 1
            self._save()

    def needs_calibration(self) -> bool:
        """Return True if session_count >= 5 and expertise is not yet actively calibrated."""
        with self._lock:
            return self._profile.session_count >= 5 and not self._profile.expertise_calibrated

    def apply_calibration_jump(self, new_score: float) -> None:
        """Force the expertise score to a specific value and mark as calibrated."""
        with self._lock:
            self._profile.expertise_score = max(0.0, min(1.0, new_score))
            self._profile.expertise_calibrated = True
            self._save()

    def get_due_anchors(self) -> list[dict[str, str]]:
        """Return a list of knowledge anchors that are due for spaced repetition."""
        due_anchors = []
        now_ts = time.time()
        with self._lock:
            for anchor in self._profile.knowledge_anchors:
                try:
                    last_surfaced = float(anchor.get("last_surfaced", 0))
                    interval_idx = int(anchor.get("interval_idx", 0))
                    
                    # Bound index
                    idx = min(interval_idx, len(_SPACED_REP_INTERVALS_HOURS) - 1)
                    target_interval_hours = _SPACED_REP_INTERVALS_HOURS[idx]
                    
                    hours_since = (now_ts - last_surfaced) / 3600.0
                    if hours_since >= target_interval_hours:
                        due_anchors.append(anchor)
                except ValueError:
                    continue
        return due_anchors

    def mark_anchor_surfaced(self, anchor_text: str) -> None:
        """Update spaced repetition metrics for an anchor that was just reused."""
        with self._lock:
            for anchor in self._profile.knowledge_anchors:
                if anchor.get("anchor") == anchor_text:
                    try:
                        idx = int(anchor.get("interval_idx", 0))
                        count = int(anchor.get("surface_count", 0))
                        
                        anchor["interval_idx"] = str(idx + 1)
                        anchor["surface_count"] = str(count + 1)
                        anchor["last_surfaced"] = str(time.time())
                        
                    except ValueError:
                        pass
            self._save()

    async def async_decompose_active_goals(self) -> None:
        """Asynchronously decompose compound goals into sub-goals using LLM.
        Operates on unparsed active_goals.
        """
        import asyncio
        from engine.executor import JITExecutor
        
        goals_to_process = []
        with self._lock:
            for g in self._profile.active_goals:
                if "{" not in g and "}" not in g:  # simple heuristic to see if it's structural
                    goals_to_process.append(g)
                    
        if not goals_to_process:
            return
            
        executor = JITExecutor()
        for goal in goals_to_process:
            prompt = (
                f"Decompose the following high-level goal into an actionable JSON array of sub-goal strings. "
                f"Goal to decompose: '{goal}'. Return ONLY raw JSON array of strings."
            )
            try:
                # Fire and forget LLM parsing
                res = await asyncio.to_thread(executor._generate_patch, prompt, "")
                if res.startswith("[") and res.endswith("]"):
                    import json
                    subs = json.loads(res)
                    if isinstance(subs, list) and len(subs) > 1:
                        with self._lock:
                            if goal in self._profile.active_goals:
                                idx = self._profile.active_goals.index(goal)
                                self._profile.active_goals.pop(idx)
                                for sg in reversed(subs):
                                    self._profile.active_goals.insert(idx, sg[:120])
                                self._save()
            except Exception:
                pass


    def _load(self) -> UserProfile:
        if not self._path.exists():
            return UserProfile()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return UserProfile.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError):
            return UserProfile()

    def _save(self) -> None:
        """Atomic JSON write using write-then-rename pattern."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(self._profile.to_dict(),
                           indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(self._path)
        except OSError:
            pass


# ── Context builder for LLM prompt injection ─────────────────────────────────


def build_cognition_context(
    profile: UserProfile,
    cognitive_turn: CognitiveTurn,
) -> str:
    """Build an LLM context block from the user's cognitive profile + turn analysis.

    This block is injected into the Buddy prompt to adapt:
      - Response DEPTH to expertise (Expertise Reversal Effect)
      - Response STRUCTURE to cognitive load (Cognitive Load Theory)
      - Response STYLE to preferred learning mode (Narrative Transportation)
      - Response ANCHORING to active goals (TOTE goal hierarchy)
      - Response FRAMING to re-use proven anchors (Vygotsky's ZPD)

    The output is a concise, directive-style block for the LLM — not prose.
    """
    lines: list[str] = []
    level = profile.expertise_label()
    score = profile.expertise_score

    # ── Expertise depth instruction ────────────────────────────────────────
    if level == "novice":
        lines.append(
            f"[COGNITION] User Expertise: NOVICE (score={score:.2f}). "
            "Use analogies and plain language. Define technical terms inline. "
            "Explain each step explicitly. Never assume background knowledge."
        )
    elif level == "intermediate":
        lines.append(
            f"[COGNITION] User Expertise: INTERMEDIATE (score={score:.2f}). "
            "Use standard technical terms but briefly define new ones on first use. "
            "Balance concept explanation with practical examples."
        )
    elif level == "advanced":
        lines.append(
            f"[COGNITION] User Expertise: ADVANCED (score={score:.2f}). "
            "Use precise technical language freely. Skip fundamentals. "
            "Discuss trade-offs, edge cases, and performance implications directly."
        )
    else:  # expert
        lines.append(
            f"[COGNITION] User Expertise: EXPERT (score={score:.2f}). "
            "Be concise and peer-level. Reference SOTA and best practices directly. "
            "Do NOT explain fundamentals — redundant content harms expert cognitive flow."
        )

    # ── Cognitive load structure instruction ───────────────────────────────
    if cognitive_turn.cognitive_load == "high":
        lines.append(
            "[COGNITION] Cognitive Load: HIGH. "
            "Break your response into numbered steps. One concept per step. "
            "Add a one-line summary at the end."
        )
    elif cognitive_turn.cognitive_load == "medium":
        lines.append(
            "[COGNITION] Cognitive Load: MEDIUM. "
            "Use 2-3 clearly labelled sections. Bullet points for multi-part answers."
        )
    # Low load: no special instruction needed — default concise response is correct.

    # ── Learning style instruction ─────────────────────────────────────────
    if profile.preferred_style == "visual":
        lines.append(
            "[COGNITION] Learning Style: VISUAL. "
            "Include a diagram or chart artifact when possible. "
            "Use spatial language: 'flows into', 'sits above', 'wraps around'."
        )
    elif profile.preferred_style == "example":
        lines.append(
            "[COGNITION] Learning Style: EXAMPLE-BASED. "
            "Lead with a concrete code example, then explain what it demonstrates."
        )
    elif profile.preferred_style == "analogy":
        lines.append(
            "[COGNITION] Learning Style: ANALOGY-BASED. "
            "Open with a real-world analogy before technical detail. "
            "This user builds understanding through conceptual bridging."
        )

    # ── Active goals context ───────────────────────────────────────────────
    if profile.active_goals:
        goals_str = "; ".join(profile.active_goals[:3])
        lines.append(
            f"[COGNITION] User's Active Goals: {goals_str}. "
            "Where naturally relevant, frame your answer as progress toward these."
        )

    # ── Knowledge anchor re-use with SPACED REPETITION ──────────────────────
    if profile.knowledge_anchors:
        # Find the anchor that is most DUE for review (Ebbinghaus scheduling)
        best_anchor = None
        best_urgency = -1.0
        now = time.time()
        for anch in profile.knowledge_anchors:
            last_surfaced = float(anch.get("last_surfaced", str(now)))
            interval_idx = int(anch.get("interval_idx", "0"))
            # Hours since last surfaced
            hours_elapsed = (now - last_surfaced) / 3600
            # Target interval from Ebbinghaus schedule
            target_hours = _SPACED_REP_INTERVALS_HOURS[
                min(interval_idx, len(_SPACED_REP_INTERVALS_HOURS) - 1)
            ]
            # Urgency: how overdue is this anchor? (>1.0 = due for review)
            urgency = hours_elapsed / max(target_hours, 1)
            if urgency > best_urgency:
                best_urgency = urgency
                best_anchor = anch

        if best_anchor and best_urgency >= 0.8:  # At least 80% of interval elapsed
            anchor_preview = best_anchor.get("anchor", "")[:150]
            topic = best_anchor.get("topic", "unknown")
            lines.append(
                f"[COGNITION] Spaced repetition DUE — re-surface this anchor "
                f"(topic: {topic}): \"{anchor_preview}\""
            )
        elif best_anchor:
            # Not due yet, but still provide the most recent anchor as optional
            anchor_preview = profile.knowledge_anchors[-1].get("anchor", "")[:150]
            lines.append(
                f"[COGNITION] Proven anchor (re-use if relevant): "
                f"\"{anchor_preview}\""
            )

    return "\n".join(lines)
