"""
engine/tribunal.py — OWASP poison detection → heal → VastLearn capture.

Standalone — zero imports outside engine/. No LLM, no network.

OWASP-aligned poison patterns:
  - Hardcoded secrets (SECRET=, API_KEY=, PASSWORD=, TOKEN= with inline values)
  - String-concatenation SQL injection
  - eval() / exec() / __import__() in generated logic

On poison detection:
  1. Redact logic_body with a tombstone comment.
  2. Write a new .cog.json rule to psyche_bank/ via PsycheBank.
  3. Return TribunalResult(poison_detected=True, heal_applied=True).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.psyche_bank import CogRule, PsycheBank

_HEAL_TOMBSTONE = (
    "# [TRIBUNAL HEALED] Poisoned logic redacted. "
    "Rule captured in psyche_bank/."
)

# OWASP-aligned patterns — ranked by severity
_POISON: list[tuple[str, re.Pattern[str]]] = [
    (
        "hardcoded-secret",
        re.compile(
            r'(?:SECRET|PASSWORD|API_KEY|TOKEN|PRIVATE_KEY)\s*=\s*["\'][^"\']{3,}["\']',
            re.IGNORECASE,
        ),
    ),
    (
        "sql-injection",
        re.compile(r'SELECT\b.*\+\s*\w+', re.IGNORECASE),
    ),
    (
        "dynamic-eval",
        re.compile(r'\beval\s*\(', re.IGNORECASE),
    ),
    (
        "dynamic-exec",
        re.compile(r'\bexec\s*\(', re.IGNORECASE),
    ),
    (
        "dynamic-import",
        re.compile(r'__import__\s*\(', re.IGNORECASE),
    ),
]


@dataclass
class Engram:
    """Minimal engram representation — no external schema dependency."""

    slug: str
    intent: str
    logic_body: str
    domain: str = "backend"
    mandate_level: str = "L2"


@dataclass
class TribunalResult:
    slug: str
    passed: bool
    poison_detected: bool
    heal_applied: bool
    vast_learn_triggered: bool
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "passed": self.passed,
            "poison_detected": self.poison_detected,
            "heal_applied": self.heal_applied,
            "vast_learn_triggered": self.vast_learn_triggered,
            "violations": self.violations,
        }


class Tribunal:
    """Evaluate an engram for OWASP violations, heal, and capture rules."""

    def __init__(self, bank: PsycheBank | None = None) -> None:
        self._bank = bank or PsycheBank()

    def evaluate(self, engram: Engram) -> TribunalResult:
        violations = [name for name, pat in _POISON if pat.search(engram.logic_body)]

        if not violations:
            return TribunalResult(
                slug=engram.slug,
                passed=True,
                poison_detected=False,
                heal_applied=False,
                vast_learn_triggered=False,
            )

        # Heal: redact the logic body
        engram.logic_body = _HEAL_TOMBSTONE

        # Capture new rules into PsycheBank for each novel violation
        for v in violations:
            rule_id = f"tribunal-auto-{v}-001"
            self._bank.capture(
                CogRule(
                    id=rule_id,
                    description=f"Auto-captured by Tribunal during heal: {v}",
                    pattern=v,
                    enforcement="block",
                    category="security",
                    source="tribunal",
                )
            )

        return TribunalResult(
            slug=engram.slug,
            passed=False,
            poison_detected=True,
            heal_applied=True,
            vast_learn_triggered=True,
            violations=violations,
        )
