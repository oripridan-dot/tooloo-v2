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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from engine.config import CIRCUIT_BREAKER_MAX_FAILS, CIRCUIT_BREAKER_THRESHOLD

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


# ── Router ─────────────────────────────────────────────────────────────────────


class MandateRouter:
    """Standalone keyword-based mandate router with circuit breaker."""

    def __init__(self) -> None:
        self._fail_count: int = 0
        self._tripped: bool = False

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

        scores = _score(text)
        best = max(scores, key=lambda k: scores[k])
        confidence = min(1.0, scores[best] * 8)  # scale to 0–1

        fired = confidence < CIRCUIT_BREAKER_THRESHOLD
        if fired:
            self._record_failure()
        else:
            self._fail_count = 0

        return self._make(best, confidence, mandate_text, fired)

    def reset(self) -> None:
        """Governor-only: clear the circuit breaker state."""
        self._tripped = False
        self._fail_count = 0

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
            buddy_line=_BUDDY_LINES.get(intent, ""),
        )
