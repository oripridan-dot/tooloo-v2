# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-19T16:01:25.381037+00:00
# Component: router  Source: engine/router.py
# Improvement signals from JIT SOTA booster:
#  [1] FIX 1: engine/router.py:30 — Expand _KEYWORDS with synonyms and more specific
#     terms based on SOTA signals. CODE:     "BUILD": [         "build",
#     "implement", "create", "add", "write", "generate", "scaffold",
#     "initialise", "initialize", "setup", "set up", "wire", "integrate",
#     "sync",         "synchronise", "synchronize", "deploy", "ship",
#     "release", "update the", "provision", "configure",     ],     "DEBUG": [
#     "fix", "bug", "error", "broken", "fail", "crash", "traceback",
#     "exception",         "diagnose", "root cause", "investigate", "patch",
#     "regression", "500", "404",         "not working", "issue", "problem",
#     "debug", "troubleshoot", "monitor",     ],
#  [2] FIX 2: engine/router.py:62 — Implement confidence-band boundaries for BUILD,
#     DEBUG, AUDIT, DESIGN, EXPLAIN, IDEATE based on observed distribution of
#     scores. CODE: def _score(text: str) -> dict[str, float]:     lowered =
#     text.lower()     scores: dict[str, float] = {}     for intent, patterns
#     in _KEYWORDS.items():         hits = sum(1 for p in patterns if
#     re.search(p, lowered))         # Normalize score by the number of
#     patterns for that intent         normalized_score = hits / len(patterns)
#     if patterns else 0         scores[intent] = normalized_score      #
#     Apply fixed confidence band boundaries (e.g., adjust these based on
#     actual data)     for intent in ["BUILD", "DEBUG", "AUDIT", "DESIGN",
#     "EXPLAIN", "IDEATE"]:         if scores.get(intent, 0) <
#     CIRCUIT_BREAKER_THRESHOLD:             scores[intent] = 0.0  # Force low
#     confidence if below threshold     return scores
#  [3] FIX 3: engine/router.py:27 — Introduce active learning sampling strategy for
#     misclassified examples to improve intent coverage. CODE: """
#     engine/router.py — Mandate intent classification + circuit breaker.
#     Standalone keyword scorer — no external dependencies beyond stdlib.
#     Classifies free-text into: BUILD | DEBUG | AUDIT | DESIGN | EXPLAIN |
#     IDEATE | SPAWN_REPO  Circuit breaker (Law 19):   - confidence
#     <CIRCUIT_BREAKER_THRESHOLD  → fires breaker flag on that result   -
#     CIRCUIT_BREAKER_MAX_FAILS consecutive failures → router trips (returns
#     BLOCKED)   - Governor calls reset() to restore  Active Learning: Collect
#     low-confidence or misclassified examples for targeted retraining. """
#     from __future__ import annotations
# ─────────────────────────────────────────────────────────────────
#     terms based on SOTA signals. CODE:     "BUILD": [         "build",
#     "implement", "create", "add", "write", "generate", "scaffold",
#     "initialise", "initialize", "setup", "set up", "wire", "integrate",
#     "sync",         "synchronise", "synchronize", "deploy", "ship",
#     "release", "update the", "provision", "configure",     ],     "DEBUG": [
#     "fix", "bug", "error", "broken", "fail", "crash", "traceback",
#     "exception",         "diagnose", "root cause", "investigate", "patch",
#     "regression", "500", "404",         "not working", "issue", "problem",
#     "debug", "troubleshoot", "monitor",     ],
#     DEBUG, AUDIT, DESIGN, EXPLAIN, IDEATE based on observed distribution of
#     scores. CODE: def _score(text: str) -> dict[str, float]:     lowered =
#     text.lower()     scores: dict[str, float] = {}     for intent, patterns
#     in _KEYWORDS.items():         hits = sum(1 for p in patterns if
#     re.search(p, lowered))         # Normalize score by the number of
#     patterns for that intent         normalized_score = hits / len(patterns)
#     if patterns else 0         scores[intent] = normalized_score      #
#     Apply fixed confidence band boundaries (e.g., adjust these based on
#     actual data)     for intent in ["BUILD", "DEBUG", "AUDIT", "DESIGN",
#     "EXPLAIN", "IDEATE"]:         if scores.get(intent, 0) <
#     CIRCUIT_BREAKER_THRESHOLD:             scores[intent] = 0.0  # Force low
#     confidence if below threshold     return scores
#     misclassified examples to improve intent coverage. CODE: """
#     engine/router.py — Mandate intent classification + circuit breaker.
#     Standalone keyword scorer — no external dependencies beyond stdlib.
#     Classifies free-text into: BUILD | DEBUG | AUDIT | DESIGN | EXPLAIN |
#     IDEATE | SPAWN_REPO  Circuit breaker (Law 19):   - confidence
#     <CIRCUIT_BREAKER_THRESHOLD  → fires breaker flag on that result   -
#     CIRCUIT_BREAKER_MAX_FAILS consecutive failures → router trips (returns
#     BLOCKED)   - Governor calls reset() to restore  Active Learning: Collect
#     low-confidence or misclassified examples for targeted retraining. """
#     from __future__ import annotations
#     terms based on SOTA signals. CODE:     "BUILD": [         "build",
#     "implement", "create", "add", "write", "generate", "scaffold",
#     "initialise", "initialize", "setup", "set up", "wire", "integrate",
#     "sync",         "synchronise", "synchronize", "deploy", "ship",
#     "release", "update the", "provision", "configure",     ],     "DEBUG": [
#     "fix", "bug", "error", "broken", "fail", "crash", "traceback",
#     "exception",         "diagnose", "root cause", "investigate", "patch",
#     "regression", "500", "404",         "not working", "issue", "problem",
#     "debug", "troubleshoot", "monitor",     ],
#     DEBUG, AUDIT, DESIGN, EXPLAIN, IDEATE based on observed distribution of
#     scores. CODE: def _score(text: str) -> dict[str, float]:     lowered =
#     text.lower()     scores: dict[str, float] = {}     for intent, patterns
#     in _KEYWORDS.items():         hits = sum(1 for p in patterns if
#     re.search(p, lowered))         # Normalize score by the number of
#     patterns for that intent         normalized_score = hits / len(patterns)
#     if patterns else 0         scores[intent] = normalized_score      #
#     Apply fixed confidence band boundaries (e.g., adjust these based on
#     actual data)     for intent in ["BUILD", "DEBUG", "AUDIT", "DESIGN",
#     "EXPLAIN", "IDEATE"]:         if scores.get(intent, 0) <
#     CIRCUIT_BREAKER_THRESHOLD:             scores[intent] = 0.0  # Force low
#     confidence if below threshold     return scores
#     misclassified examples to improve intent coverage. CODE: """
#     engine/router.py — Mandate intent classification + circuit breaker.
#     Standalone keyword scorer — no external dependencies beyond stdlib.
#     Classifies free-text into: BUILD | DEBUG | AUDIT | DESIGN | EXPLAIN |
#     IDEATE | SPAWN_REPO  Circuit breaker (Law 19):   - confidence
#     <CIRCUIT_BREAKER_THRESHOLD  → fires breaker flag on that result   -
#     CIRCUIT_BREAKER_MAX_FAILS consecutive failures → router trips (returns
#     BLOCKED)   - Governor calls reset() to restore  Active Learning: Collect
#     low-confidence or misclassified examples for targeted retraining. """
#     from __future__ import annotations
#     terms based on SOTA signals. CODE:     "BUILD": [         "build",
#     "implement", "create", "add", "write", "generate", "scaffold",
#     "initialise", "initialize", "setup", "set up", "wire", "integrate",
#     "sync",         "synchronise", "synchronize", "deploy", "ship",
#     "release", "update the", "provision", "configure",     ],     "DEBUG": [
#     "fix", "bug", "error", "broken", "fail", "crash", "traceback",
#     "exception",         "diagnose", "root cause", "investigate", "patch",
#     "regression", "500", "404",         "not working", "issue", "problem",
#     "debug", "troubleshoot", "monitor",     ],
#     DEBUG, AUDIT, DESIGN, EXPLAIN, IDEATE based on observed distribution of
#     scores. CODE: def _score(text: str) -> dict[str, float]:     lowered =
#     text.lower()     scores: dict[str, float] = {}     for intent, patterns
#     in _KEYWORDS.items():         hits = sum(1 for p in patterns if
#     re.search(p, lowered))         # Normalize score by the number of
#     patterns for that intent         normalized_score = hits / len(patterns)
#     if patterns else 0         scores[intent] = normalized_score      #
#     Apply fixed confidence band boundaries (e.g., adjust these based on
#     actual data)     for intent in ["BUILD", "DEBUG", "AUDIT", "DESIGN",
#     "EXPLAIN", "IDEATE"]:         if scores.get(intent, 0) <
#     CIRCUIT_BREAKER_THRESHOLD:             scores[intent] = 0.0  # Force low
#     confidence if below threshold     return scores
#     misclassified examples to improve intent coverage. CODE: """
#     engine/router.py — Mandate intent classification + circuit breaker.
#     Standalone keyword scorer — no external dependencies beyond stdlib.
#     Classifies free-text into: BUILD | DEBUG | AUDIT | DESIGN | EXPLAIN |
#     IDEATE | SPAWN_REPO  Circuit breaker (Law 19):   - confidence
#     <CIRCUIT_BREAKER_THRESHOLD  → fires breaker flag on that result   -
#     CIRCUIT_BREAKER_MAX_FAILS consecutive failures → router trips (returns
#     BLOCKED)   - Governor calls reset() to restore  Active Learning: Collect
#     low-confidence or misclassified examples for targeted retraining. """
#     from __future__ import annotations
#     terms based on SOTA signals. CODE:     "BUILD": [         "build",
#     "implement", "create", "add", "write", "generate", "scaffold",
#     "initialise", "initialize", "setup", "set up", "wire", "integrate",
#     "sync",         "synchronise", "synchronize", "deploy", "ship",
#     "release", "update the", "provision", "configure",     ],     "DEBUG": [
#     "fix", "bug", "error", "broken", "fail", "crash", "traceback",
#     "exception",         "diagnose", "root cause", "investigate", "patch",
#     "regression", "500", "404",         "not working", "issue", "problem",
#     "debug", "troubleshoot", "monitor",     ],
#     DEBUG, AUDIT, DESIGN, EXPLAIN, IDEATE based on observed distribution of
#     scores. CODE: def _score(text: str) -> dict[str, float]:     lowered =
#     text.lower()     scores: dict[str, float] = {}     for intent, patterns
#     in _KEYWORDS.items():         hits = sum(1 for p in patterns if
#     re.search(p, lowered))         # Normalize score by the number of
#     patterns for that intent         normalized_score = hits / len(patterns)
#     if patterns else 0         scores[intent] = normalized_score      #
#     Apply fixed confidence band boundaries (e.g., adjust these based on
#     actual data)     for intent in ["BUILD", "DEBUG", "AUDIT", "DESIGN",
#     "EXPLAIN", "IDEATE"]:         if scores.get(intent, 0) <
#     CIRCUIT_BREAKER_THRESHOLD:             scores[intent] = 0.0  # Force low
#     confidence if below threshold     return scores
#     misclassified examples to improve intent coverage. CODE: """
#     engine/router.py — Mandate intent classification + circuit breaker.
#     Standalone keyword scorer — no external dependencies beyond stdlib.
#     Classifies free-text into: BUILD | DEBUG | AUDIT | DESIGN | EXPLAIN |
#     IDEATE | SPAWN_REPO  Circuit breaker (Law 19):   - confidence
#     <CIRCUIT_BREAKER_THRESHOLD  → fires breaker flag on that result   -
#     CIRCUIT_BREAKER_MAX_FAILS consecutive failures → router trips (returns
#     BLOCKED)   - Governor calls reset() to restore  Active Learning: Collect
#     low-confidence or misclassified examples for targeted retraining. """
#     from __future__ import annotations
"""
engine/router.py — Mandate intent classification + circuit breaker.

Standalone keyword scorer — no external dependencies beyond stdlib.
Classifies free-text into: BUILD | DEBUG | AUDIT | DESIGN | EXPLAIN | IDEATE | SPAWN_REPO

Circuit breaker (Law 19):
  - confidence < CIRCUIT_BREAKER_THRESHOLD  → fires breaker flag on that result
  - CIRCUIT_BREAKER_MAX_FAILS consecutive failures → router trips (returns BLOCKED)
  - Governor calls reset() to restore
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from engine.config import CIRCUIT_BREAKER_MAX_FAILS, CIRCUIT_BREAKER_THRESHOLD

# Maximum number of low-confidence examples retained for active-learning reuse.
_ACTIVE_LEARNING_MAXLEN: int = 200

# ── Semantic Embedding Classifier ─────────────────────────────────────────────
# Uses Gemini text-embedding-004 to classify intent via cosine similarity against
# pre-defined prototype phrases per intent.  Hybrid formula:
#   final_confidence = 0.60 * embedding_score + 0.40 * keyword_score
# Falls back to keyword-only when the API is unavailable.

_INTENT_PROTOTYPES: dict[str, list[str]] = {
    "BUILD": [
        "build and implement a new feature",
        "create a new service or module",
        "write code to add functionality",
        "generate and scaffold a new component",
        "integrate and wire up systems",
    ],
    "DEBUG": [
        "fix a bug or error",
        "diagnose a crash or exception",
        "investigate why something is broken",
        "patch a regression or failing test",
        "traceback analysis and root cause investigation",
    ],
    "AUDIT": [
        "audit security and dependencies",
        "review code quality and health",
        "validate and verify the system",
        "scan for outdated libraries or licenses",
        "generate a status or health report",
    ],
    "DESIGN": [
        "design a user interface layout",
        "create a UI mockup or wireframe",
        "redesign the visual theme or style",
        "component and interface design",
        "ux and experience prototype",
    ],
    "EXPLAIN": [
        "explain how this works",
        "describe and clarify a concept",
        "walk me through this code",
        "what does this function do",
        "break down the architecture",
    ],
    "IDEATE": [
        "brainstorm ideas and strategies",
        "what approach should I take",
        "recommend a solution or direction",
        "advise on best practices",
        "explore options and alternatives",
    ],
    "SPAWN_REPO": [
        "create a new git repository",
        "initialise and bootstrap a new project",
        "spawn a new service repository",
        "new repo scaffold with boilerplate",
        "set up a new codebase from scratch",
    ],
}


def _cosine_dense_router(a: list[float], b: list[float]) -> float:
    """Cosine similarity for dense float vectors (router use only)."""
    import math
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0.0 and nb > 0.0 else 0.0


class SemanticEmbeddingClassifier:
    """Intent classifier using Gemini text-embedding-004 prototype matching.

    At first use, pre-computes one mean prototype embedding per intent from
    ``_INTENT_PROTOTYPES``.  Subsequent calls classify via cosine similarity.
    Thread-safe: prototype computation happens once under a lock.
    """

    _EMBED_MODEL = "models/text-embedding-004"

    def __init__(self) -> None:
        import threading
        self._lock = threading.Lock()
        self._prototypes: dict[str, list[float]] | None = None
        self._client = None
        try:
            # type: ignore[attr-defined]
            from engine.config import GEMINI_API_KEY as _K
            if _K:
                from google import genai as _g  # type: ignore[import]
                self._client = _g.Client(api_key=_K)
        except Exception:
            pass

    def _embed(self, text: str) -> list[float] | None:
        if self._client is None:
            return None
        try:
            resp = self._client.models.embed_content(
                model=self._EMBED_MODEL,
                contents=text[:2000],
            )
            return list(resp.embeddings[0].values)
        except Exception:
            return None

    def _mean_embed(self, phrases: list[str]) -> list[float] | None:
        vecs = [v for p in phrases if (v := self._embed(p))]
        if not vecs:
            return None
        dim = len(vecs[0])
        mean = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
        mag = sum(x * x for x in mean) ** 0.5
        return [x / mag for x in mean] if mag > 0.0 else mean

    def _ensure_prototypes(self) -> bool:
        """Lazy-init: compute prototype embeddings once. Returns True if ready."""
        if self._prototypes is not None:
            return True
        with self._lock:
            if self._prototypes is not None:
                return True
            protos: dict[str, list[float]] = {}
            for intent, phrases in _INTENT_PROTOTYPES.items():
                emb = self._mean_embed(phrases)
                if emb is None:
                    return False  # API unavailable — abort, use keyword fallback
                protos[intent] = emb
            self._prototypes = protos
        return True

    def classify(self, text: str) -> dict[str, float] | None:
        """Return cosine similarity scores per intent, or None if API unavailable."""
        if not self._ensure_prototypes():
            return None
        emb = self._embed(text)
        if emb is None:
            return None
        assert self._prototypes is not None
        return {
            intent: max(0.0, _cosine_dense_router(emb, proto))
            for intent, proto in self._prototypes.items()
        }


# Module-level singleton — initialised once, shared across all router instances.
_semantic_clf = SemanticEmbeddingClassifier()

# ── Keyword catalogue ──────────────────────────────────────────────────────────

_KEYWORDS: dict[str, list[str]] = {
    "BUILD": [
        "build", "implement", "create", "add", "write", "generate", "scaffold",
        "initialise", "initialize", "setup", "set up", "wire", "integrate", "sync",
        "synchronise", "synchronize", "deploy", "ship", "release", "update the",
    ],
    "DEBUG": [
        "fix", "bug", "error", "broken", "fail", "crash", "traceback", "exception",
        "diagnose", "root cause", "investigate", "patch", "regression", "500",
        "not working", "issue", "problem",
    ],
    "AUDIT": [
        "audit", "scan", "review", "check", "validate", "verify", "report",
        "status", "health", "stale", "outdated", "licence", "license", "security",
        "dependency", "cost", "telemetry",
    ],
    "DESIGN": [
        "design", "redesign", "layout", "mockup", r"\bui\b", r"\bux\b", "wireframe",
        "visual", "canvas", "component", "interface", "theme", "style", "prototype",
    ],
    "EXPLAIN": [
        "explain", "why", "how does", "what is", "describe", "walk me through",
        "clarify", "what does", "breakdown", "break down",
    ],
    "IDEATE": [
        "brainstorm", "ideate", "ideas", "strategy", "approach", "recommend",
        "advise", "should i", "what would", "how should",
    ],
    "SPAWN_REPO": [
        "new repo", "new repository", "create repo", "spawn repo", "bootstrap repo",
        "initialise repo", "initialize repo", "new project", "new service",
    ],
}


def _score(text: str) -> dict[str, float]:
    lowered = text.lower()
    scores: dict[str, float] = {}
    for intent, patterns in _KEYWORDS.items():
        hits = sum(1 for p in patterns if re.search(p, lowered))
        scores[intent] = hits / len(patterns)
    return scores


def _scaled_confidence(scores: dict[str, float], intent: str) -> float:
    pattern_count = max(1, len(_KEYWORDS.get(intent, [])))
    return min(1.0, scores[intent] * (8 * 20 / pattern_count))


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class RouteResult:
    intent: str
    confidence: float
    circuit_open: bool
    mandate_text: str
    buddy_line: str = ""
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "circuit_open": self.circuit_open,
            "mandate_text": self.mandate_text,
            "buddy_line": self.buddy_line,
            "ts": self.ts,
        }


_BUDDY_LINES: dict[str, str] = {
    "BUILD": "Switching to BUILD mode — ready to implement.",
    "DEBUG": "Entering DEBUG mode — let's trace and squash that issue.",
    "AUDIT": "Running AUDIT mode — scanning systems and reporting.",
    "DESIGN": "Opening DESIGN mode — let's shape the experience.",
    "EXPLAIN": "EXPLAIN mode activated — walking you through it.",
    "IDEATE": "Entering IDEATE mode — let's explore ideas together.",
    "SPAWN_REPO": "Activating SPAWN_REPO mode — architecting a new repo factory.",
    "BLOCKED": "Circuit breaker is tripped. Governor reset required before proceeding.",
}

_HEDGE_THRESHOLD: float = 0.65  # below this confidence, buddy_line includes a hedge


def compute_buddy_line(intent: str, confidence: float) -> str:
    """Derive the Buddy status line from intent + confidence.

    Exported so JIT boost can recompute the line after updating confidence.
    """
    base = _BUDDY_LINES.get(intent, "")
    if intent != "BLOCKED" and confidence < _HEDGE_THRESHOLD:
        pct = round(confidence * 100)
        return (
            f"Best match looks like {intent} (~{pct}\u202f% confident) — "
            f"redirect me if I've misread. {base}"
        )
    return base


# ── Router ─────────────────────────────────────────────────────────────────────


class MandateRouter:
    """Standalone keyword-based mandate router with circuit breaker.

    Active-Learning Sampler
    -----------------------
    Every routing result whose confidence falls below ``_HEDGE_THRESHOLD``
    (or that fires the circuit breaker) is automatically appended to an
    in-memory deque (``_low_conf_samples``, capped at
    ``_ACTIVE_LEARNING_MAXLEN``).  Call ``get_low_confidence_samples()`` to
    retrieve these examples for offline classifier retraining.
    """

    def __init__(self) -> None:
        self._fail_count: int = 0
        self._tripped: bool = False
        # Active-learning sample buffer: (mandate_text, routed_intent, confidence)
        self._low_conf_samples: deque[tuple[str, str, float]] = deque(
            maxlen=_ACTIVE_LEARNING_MAXLEN
        )

    @property
    def is_tripped(self) -> bool:
        return self._tripped

    def status(self) -> dict[str, Any]:
        return {
            "circuit_open": self._tripped,
            "consecutive_failures": self._fail_count,
            "max_fails": CIRCUIT_BREAKER_MAX_FAILS,
            "threshold": CIRCUIT_BREAKER_THRESHOLD,
        }

    def _record_failure(self) -> None:
        """Manually record a failure — used by tests and external callers."""
        self._fail_count += 1
        if self._fail_count >= CIRCUIT_BREAKER_MAX_FAILS:
            self._tripped = True

    def get_low_confidence_samples(self) -> list[tuple[str, str, float]]:
        """Return buffered low-confidence routing examples for active-learning.

        Each element is ``(mandate_text, routed_intent, confidence)``.
        The buffer is a rolling window of the most recent
        ``_ACTIVE_LEARNING_MAXLEN`` samples.
        """
        return list(self._low_conf_samples)

    def route(self, mandate_text: str) -> RouteResult:
        if self._tripped:
            return RouteResult(
                intent="BLOCKED",
                confidence=0.0,
                circuit_open=True,
                mandate_text=mandate_text,
                buddy_line=_BUDDY_LINES["BLOCKED"],
            )

        text = mandate_text.strip()
        if not text:
            return self._make("BUILD", 0.2, mandate_text)

        # Keyword score (always computed as the reliable fallback)
        kw_scores = _score(text)
        kw_best = max(kw_scores, key=lambda k: kw_scores[k])
        kw_conf = _scaled_confidence(kw_scores, kw_best)

        # Semantic embedding score (Gemini text-embedding-004, may be None)
        sem_scores = _semantic_clf.classify(text)
        if sem_scores is not None:
            sem_best = max(sem_scores, key=lambda k: sem_scores[k])
            sem_conf = sem_scores[sem_best]
            # Hybrid: prefer the intent with best combined score
            hybrid: dict[str, float] = {}
            all_intents = set(kw_scores) | set(sem_scores)
            for intent in all_intents:
                k = _scaled_confidence(
                    kw_scores, intent) if intent in kw_scores else 0.0
                s = sem_scores.get(intent, 0.0)
                hybrid[intent] = 0.60 * s + 0.40 * k
            best = max(hybrid, key=lambda k: hybrid[k])
            confidence = min(1.0, hybrid[best])
        else:
            # API unavailable — fall back to pure keyword
            best = kw_best
            confidence = kw_conf

        fired = confidence < CIRCUIT_BREAKER_THRESHOLD
        if fired:
            self._record_failure()
        else:
            self._fail_count = 0

        # Active-learning: buffer low-confidence and CB-firing examples.
        if fired or confidence < _HEDGE_THRESHOLD:
            self._low_conf_samples.append((text, best, confidence))

        return self._make(best, confidence, mandate_text, fired)

    def route_chat(self, mandate_text: str) -> RouteResult:
        """Route a conversational message without touching the circuit-breaker state.

        Chat exchanges (short greetings, follow-ups, clarifications) routinely
        score below CIRCUIT_BREAKER_THRESHOLD.  Counting them as CB failures
        would trip the breaker on normal conversation — this method routes the
        text but never increments fail_count or trips the breaker.
        """
        if self._tripped:
            return RouteResult(
                intent="BLOCKED",
                confidence=0.0,
                circuit_open=True,
                mandate_text=mandate_text,
                buddy_line=_BUDDY_LINES["BLOCKED"],
            )

        text = mandate_text.strip()
        if not text:
            return self._make("BUILD", 0.2, mandate_text)

        kw_scores = _score(text)
        kw_best = max(kw_scores, key=lambda k: kw_scores[k])
        kw_conf = _scaled_confidence(kw_scores, kw_best)

        sem_scores = _semantic_clf.classify(text)
        if sem_scores is not None:
            hybrid: dict[str, float] = {}
            all_intents = set(kw_scores) | set(sem_scores)
            for intent in all_intents:
                k = _scaled_confidence(
                    kw_scores, intent) if intent in kw_scores else 0.0
                s = sem_scores.get(intent, 0.0)
                hybrid[intent] = 0.60 * s + 0.40 * k
            best = max(hybrid, key=lambda k: hybrid[k])
            confidence = min(1.0, hybrid[best])
        else:
            best = kw_best
            confidence = kw_conf

        # Never set circuit_open=True for chat — low confidence in conversation is
        # normal (greetings, short follow-ups).  The breaker counter is also untouched.
        return self._make(best, confidence, mandate_text, fired=False)

    def reset(self) -> None:
        """Governor-only: clear the circuit breaker state."""
        self._tripped = False
        self._fail_count = 0

    def apply_jit_boost(self, route: RouteResult, boosted_confidence: float) -> None:
        """Apply a post-routing JIT confidence boost in-place.

        Called after JITBooster.fetch() validates the route with SOTA signals.
        Updates confidence, recomputes buddy_line, and undoes the circuit-breaker
        failure increment if the boosted confidence now meets the threshold.
        """
        route.confidence = round(boosted_confidence, 4)
        route.buddy_line = compute_buddy_line(route.intent, route.confidence)
        if route.circuit_open and route.confidence >= CIRCUIT_BREAKER_THRESHOLD:
            # JIT evidence validates this route — undo the premature CB failure
            route.circuit_open = False
            if self._fail_count > 0:
                self._fail_count -= 1

    def _make(
        self,
        intent: str,
        confidence: float,
        text: str,
        fired: bool = False,
    ) -> RouteResult:
        return RouteResult(
            intent=intent,
            confidence=round(confidence, 4),
            circuit_open=fired,
            mandate_text=text,
            buddy_line=compute_buddy_line(intent, round(confidence, 4)),
        )


# ── Conversational Intent Discovery ──────────────────────────────────────────

_INTENT_LOCK_THRESHOLD: float = 0.90   # confidence gate to lock intent

_GENERIC_INTENT_QUESTION = (
    "What are you trying to accomplish — what should exist or work that doesn't right now?"
)

_INTENT_QUESTIONS: dict[str, str] = {
    "BUILD": "What exactly should be built — which system, layer, or feature do you have in mind?",
    "DEBUG": "Can you share the error message, when this occurs, or the symptoms you're seeing?",
    "AUDIT": "Which aspect should be audited — security, dependencies, performance, or cost?",
    "DESIGN": "What should the experience look like, and who will use it?",
    "EXPLAIN": "What should I explain — can you point me to a concept, file, or behaviour?",
    "IDEATE": "What space are we exploring — product ideas, architecture choices, or strategies?",
    "SPAWN_REPO": "What is the repo for — new service, library, or app? What is its primary role?",
}

_VALUE_QUESTIONS: dict[str, str] = {
    "BUILD": "What problem does this solve, and what does a successful outcome look like for you?",
    "DEBUG": "What is the business or user impact of this bug? What does 'fixed' look like?",
    "AUDIT": "What risk are you trying to surface or reduce with this audit?",
    "DESIGN": "Who experiences this UI, and what should they feel when they use it?",
    "EXPLAIN": "What will you do differently once you understand this?",
    "IDEATE": "What goal or constraint is driving this exploration?",
    "SPAWN_REPO": "What is the primary use case of this new repo, and who will contribute to it?",
}

_CONSTRAINTS_QUESTIONS: dict[str, str] = {
    "BUILD": "Any tech-stack requirements, performance targets, or integration constraints?",
    "DEBUG": "Any environment constraints — production vs dev, language version, time pressure?",
    "AUDIT": "Any compliance standard, scope boundary, or deadline I should know about?",
    "DESIGN": "Platform, accessibility requirements, or existing design-system constraints?",
    "EXPLAIN": "Any depth preference — executive summary, detailed walkthrough, or diagram?",
    "IDEATE": "Any budget, timeline, or technology constraints to factor in?",
    "SPAWN_REPO": "Preferred language, licence, CI/CD target, or internal template?",
}

_VALUE_INDICATORS: list[str] = [
    r"\bbecause\b", r"\bneed\b", r"\bwant\b", r"\bgoal\b", r"\btrying to\b",
    r"\bso that\b", r"\bin order to\b", r"\bmust\b", r"\bimportant\b",
    r"\bcrucial\b", r"\bcritical\b", r"\bhelp\b", r"\benable\b",
    r"\ballow\b", r"\bpurpose\b", r"\bvalue\b", r"\bsolve\b",
    r"\bproblem\b", r"\bobjective\b", r"\boutcome\b",
    r"\bimpact\b", r"\bfix\b", r"\bimprove\b",
]


def _has_value_indicator(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(p, lowered) for p in _VALUE_INDICATORS)


@dataclass
class LockedIntent:
    """A confirmed, fully-understood user intent ready for the Two-Stroke Engine.

    Created by ConversationalIntentDiscovery once confidence >= _INTENT_LOCK_THRESHOLD
    and the user's value statement has been captured.
    """

    intent: str
    confidence: float
    value_statement: str        # why this matters to the user
    constraint_summary: str     # any constraints mentioned
    mandate_text: str           # full aggregated context that triggered the lock
    context_turns: list[dict[str, Any]]
    locked_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": round(self.confidence, 4),
            "value_statement": self.value_statement,
            "constraint_summary": self.constraint_summary,
            "mandate_text": self.mandate_text,
            "context_turns": self.context_turns,
            "locked_at": self.locked_at,
        }


@dataclass
class IntentLockResult:
    """Result of one conversational intent-discovery turn.

    If ``locked`` is True, ``locked_intent`` is populated and the Two-Stroke
    Engine may be invoked.  Otherwise ``clarification_question`` must be shown
    to the user and the next turn passed back to ``discover()``.
    """

    locked: bool
    clarification_question: str         # empty string when locked
    clarification_type: str             # "intent" | "value" | "constraints" | ""
    locked_intent: LockedIntent | None
    turn_count: int
    intent_hint: str                    # best-guess intent even when not locked
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "locked": self.locked,
            "clarification_question": self.clarification_question,
            "clarification_type": self.clarification_type,
            "locked_intent": self.locked_intent.to_dict() if self.locked_intent else None,
            "turn_count": self.turn_count,
            "intent_hint": self.intent_hint,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class _IntentSession:
    """Internal per-session accumulator used by ConversationalIntentDiscovery."""

    session_id: str
    texts: list[str] = field(default_factory=list)
    locked_intent: LockedIntent | None = None

    def add_text(self, text: str) -> None:
        stripped = text.strip()
        if stripped:
            self.texts.append(stripped)

    @property
    def combined_text(self) -> str:
        return " ".join(self.texts)

    @property
    def has_value(self) -> bool:
        return any(_has_value_indicator(t) for t in self.texts)

    @property
    def turn_count(self) -> int:
        return len(self.texts)


class ConversationalIntentDiscovery:
    """Multi-turn conversational engine that locks intent before execution.

    Instead of one-shot classification, this engine holds a dialogue until
    confidence >= _INTENT_LOCK_THRESHOLD AND the user's value statement has
    been captured.  Only then is a LockedIntent returned for use by the
    Two-Stroke Engine.

    Example usage::

        discovery = ConversationalIntentDiscovery()
        while True:
            result = discovery.discover(user_text, session_id)
            if result.locked:
                engine.run(result.locked_intent)
                break
            else:
                ask_user(result.clarification_question)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, _IntentSession] = {}

    def discover(self, text: str, session_id: str) -> IntentLockResult:
        """Process one user turn and return a lock result or the next question."""
        session = self._sessions.setdefault(
            session_id, _IntentSession(session_id))

        # If already locked in this session, return the existing lock immediately.
        if session.locked_intent is not None:
            return IntentLockResult(
                locked=True,
                clarification_question="",
                clarification_type="",
                locked_intent=session.locked_intent,
                turn_count=session.turn_count,
                intent_hint=session.locked_intent.intent,
                confidence=session.locked_intent.confidence,
            )

        session.add_text(text)

        # Score against accumulated context for richer signal.
        scores = _score(session.combined_text)
        best = max(scores, key=lambda k: scores[k])
        raw_confidence = _scaled_confidence(scores, best)

        # Each additional turn adds alignment evidence (capped at +0.24).
        turn_boost = min((session.turn_count - 1) * 0.08, 0.24)
        confidence = min(1.0, raw_confidence + turn_boost)

        # Lock when confidence is high enough AND value is understood.
        can_lock = confidence >= _INTENT_LOCK_THRESHOLD and (
            session.has_value or session.turn_count >= 3
        )

        if can_lock:
            locked = LockedIntent(
                intent=best,
                confidence=confidence,
                value_statement=self._extract_value_statement(session),
                constraint_summary=self._extract_constraint_statement(session),
                mandate_text=session.combined_text,
                context_turns=[
                    {"turn": i + 1, "text": t} for i, t in enumerate(session.texts)
                ],
            )
            session.locked_intent = locked
            return IntentLockResult(
                locked=True,
                clarification_question="",
                clarification_type="",
                locked_intent=locked,
                turn_count=session.turn_count,
                intent_hint=best,
                confidence=confidence,
            )

        # Determine which clarification question to ask next.
        if confidence < 0.50:
            q_type = "intent"
            question = _INTENT_QUESTIONS.get(best, _GENERIC_INTENT_QUESTION)
        elif not session.has_value:
            q_type = "value"
            question = _VALUE_QUESTIONS.get(
                best,
                f"What outcome should this {best.lower()} achieve — what does success look like?",
            )
        else:
            q_type = "constraints"
            question = _CONSTRAINTS_QUESTIONS.get(
                best,
                "Are there specific constraints, deadlines, or integration requirements I should know?",
            )

        return IntentLockResult(
            locked=False,
            clarification_question=question,
            clarification_type=q_type,
            locked_intent=None,
            turn_count=session.turn_count,
            intent_hint=best,
            confidence=confidence,
        )

    def clear_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_lock(self, session_id: str) -> LockedIntent | None:
        """Return the currently locked intent for a session, or None."""
        session = self._sessions.get(session_id)
        return session.locked_intent if session else None

    @staticmethod
    def _extract_value_statement(session: _IntentSession) -> str:
        for text in reversed(session.texts):
            if _has_value_indicator(text):
                return text[:200]
        return session.texts[-1][:200] if session.texts else ""

    @staticmethod
    def _extract_constraint_statement(session: _IntentSession) -> str:
        constraint_words = [
            "must", "requirement", "constraint", "deadline", "limit",
            "cannot", "no more than", "at least", "only", "specific",
        ]
        for text in session.texts:
            if any(w in text.lower() for w in constraint_words):
                return text[:200]
        return ""
