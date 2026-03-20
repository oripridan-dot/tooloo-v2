# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T19:59:29.189756+00:00
# Component: tribunal  Source: engine/tribunal.py
# Improvement signals from JIT SOTA booster:
#  [1] Extend engine/tribunal.py: OWASP Top 10 2025 edition promotes Broken Object-
#     Level Authorisation to the #1 priority
#  [2] Extend engine/tribunal.py: OSS supply-chain audits (Sigstore + Rekor
#     transparency log) are required in regulated environments
#  [3] Extend engine/tribunal.py: CSPM tools (Wiz, Orca, Prisma Cloud) provide real-
#     time cloud posture scoring in 2026
# ─────────────────────────────────────────────────────────────────
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
# Aligned with OWASP Top 10 2025: A01 Broken Object-Level Authorisation (BOLA)
# is the #1 priority as of 2025.  Patterns are ordered by 2025 severity rank.
_POISON: list[tuple[str, re.Pattern[str]]] = [
    (
        # OWASP A01:2025 — BOLA / IDOR (elevated to #1 in 2025 edition)
        # Detects direct DB/ORM queries using a raw user-supplied identifier
        # without an ownership filter — the canonical BOLA/IDOR pattern.
        # e.g.  Model.objects.get(id=request.data['id'])  without owner check.
        "bola-idor",
        re.compile(
            r'\.(?:filter|get|find|fetch|load|delete|update)\s*\('
            r'[^)]*\b(?:id|pk|user_id|object_id|resource_id|item_id|record_id)\s*='
            r'\s*(?:request|req|params|args|data|form|kwargs)\b',
            re.IGNORECASE,
        ),
    ),
    (
        # OWASP A01:2025 — BOLA / IDOR (second pattern)
        # Detects unfiltered SQLAlchemy / Django ORM lookups by a bare variable
        # that likely originates from a route parameter — no owner check present.
        # e.g.  db.get(Model, item_id)  or  Model.objects.get(pk=item_id)
        "bola-unfiltered-query",
        re.compile(
            r'\bdb\.(?:get|query|execute)\s*\([^)]*,\s*\w*_?id\w*\b'
            r'|\bModel\.objects\.get\s*\(\s*pk\s*=\s*\w+\s*\)'
            r'|\bget_object_or_404\s*\([^,)]+,\s*(?:pk|id)\s*=\s*(?!.*owner|.*user)',
            re.IGNORECASE,
        ),
    ),
    (
        "hardcoded-secret",
        re.compile(
            r'(?:SECRET|PASSWORD|API_KEY|TOKEN|PRIVATE_KEY|AUTH|CREDENTIAL|ACCESS_KEY|KEY)'
            r'\s*=\s*["\'][^"\']{3,}["\']',
            re.IGNORECASE,
        ),
    ),
    (
        "aws-key-leak",
        re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    ),
    (
        "bearer-token-leak",
        re.compile(r'\bBearer\s+[A-Za-z0-9\-_+/]{20,}\.', re.IGNORECASE),
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
    (
        # OWASP A01:2025 — Broken Access Control: path-traversal escape sequences
        "path-traversal",
        re.compile(r'\.\.[/\\]'),
    ),
    (
        # OWASP A03:2021 — Injection: Server-Side Template Injection (SSTI)
        # Detects {{ ... }} template syntax in logic bodies (Jinja2, Mako, etc.)
        "ssti-template-injection",
        re.compile(r'\{\{.*?\}\}'),
    ),
    (
        # OWASP A03:2021 — Injection: Command Injection via os.system / subprocess shell
        "command-injection",
        re.compile(
            r'\bos\.system\s*\(|subprocess\.(run|call|Popen)\s*\([^)]*shell\s*=\s*True',
            re.IGNORECASE,
        ),
    ),

    (
        # OWASP A10:2021 — Server-Side Request Forgery (SSRF)
        # Detects HTTP client calls where the URL is constructed from user-controlled
        # request attributes (requests.get(req.data['url']), httpx.get(params['uri']), …)
        "ssrf",
        re.compile(
            r'(?:requests|httpx|aiohttp|urllib\.request)\s*\.\s*(?:get|post|put|delete|request)\s*\('
            r'\s*(?:request|req|params|args|data|form|kwargs)\b',
            re.IGNORECASE,
        ),
    ),
    (
        # OWASP A08:2021 — Software Integrity Failures: Insecure Deserialization
        # pickle/marshal.load(s) on untrusted data enables arbitrary code execution
        "insecure-deserialization",
        re.compile(r'\b(pickle|marshal)\.(load|loads)\s*\(', re.IGNORECASE),
    ),
    (
        # OWASP A08:2021 — Software / Data Integrity Failures: Supply-Chain
        # Detects TLS verification bypass: requests.get(url, verify=False) or
        # ssl.CERT_NONE — both allow MITM attacks on package/artifact fetches.
        "supply-chain-tls-bypass",
        re.compile(
            r'verify\s*=\s*False|ssl\.CERT_NONE|ssl\.create_default_context.*check_hostname\s*=\s*False',
            re.IGNORECASE,
        ),
    ),
    (
        # OWASP A08:2021 — Software Integrity Failures: unsigned pip install
        # subprocess pip install without --require-hashes or --hash= allows
        # supply-chain substitution attacks (JIT signal: Sigstore/SLSA gate).
        "supply-chain-unpinned-install",
        re.compile(
            r'subprocess.*pip.*install(?!.*--require-hashes)(?!.*--hash=)',
            re.IGNORECASE,
        ),
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
        violations = [name for name,
                      pat in _POISON if pat.search(engram.logic_body)]

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
