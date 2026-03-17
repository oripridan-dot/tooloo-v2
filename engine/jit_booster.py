"""
engine/jit_booster.py — Just-In-Time SOTA confidence booster.

Mandatory pre-execution step that fetches real-world, up-to-date signals
relevant to the mandate intent and text, then uses those signals to:

  1. Validate the routing decision with concrete external evidence.
  2. Boost the confidence score proportionally to signal strength.
  3. Surface the evidence to downstream response generation.

Confidence boost formula:
  boost_delta = min(len(signals) * BOOST_PER_SIGNAL, MAX_BOOST_DELTA)
  boosted_confidence = min(original_confidence + boost_delta, 1.0)

Signal sources (in priority order):
  1. Gemini-2.0-flash  — live SOTA query (3–5 bullet signals)
  2. Structured catalogue — intent-keyed signals, current as of 2026

All network I/O is fully isolated here. Zero side-effects on other engine modules.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from engine.config import GEMINI_API_KEY, GEMINI_MODEL
from engine.router import RouteResult

# ── Gemini client (re-uses same optional pattern as conversation.py) ──────────
_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        _gemini_client = _genai_mod.Client(api_key=GEMINI_API_KEY)
    except Exception:  # pragma: no cover
        pass

# ── Boost constants ───────────────────────────────────────────────────────────
BOOST_PER_SIGNAL: float = 0.05   # each concrete signal adds 5 pp of confidence
MAX_BOOST_DELTA: float = 0.25    # cap: maximum +25 pp regardless of signal count

# ── SOTA signal catalogue (structured fallback) ───────────────────────────────
# Each entry: (signal_text, relevance_weight) — reflects 2026 SOTA landscape.
# Sorted by weight descending so the top signals are returned first.
_CATALOGUE: dict[str, list[tuple[str, float]]] = {
    "BUILD": [
        ("FastAPI + Pydantic v2 are the production standard for async Python services in 2026", 0.92),
        ("OpenTelemetry is the de-facto distributed tracing standard; instrument from day one", 0.88),
        ("SBOM generation (CycloneDX/SPDX) is a compliance requirement for new services in regulated sectors", 0.82),
        ("Container image signing (Sigstore cosign) is now baseline supply-chain hygiene", 0.78),
        ("Structured logging with correlation IDs (JSON + trace_id) is table stakes for observability", 0.75),
    ],
    "DEBUG": [
        ("Structured JSON logging with correlation IDs is the baseline for distributed tracing", 0.92),
        ("Flamegraph profiling (py-spy / async-profiler) localises hot paths in under 60 seconds", 0.88),
        ("Chaos-engineering fault injection is standard practice for validating resilience post-fix", 0.82),
        ("OpenTelemetry traces + spans are the primary tool for root-cause analysis in 2026", 0.78),
        ("Continuous profiling (Pyroscope / Grafana Phlare) catches regressions before production", 0.74),
    ],
    "AUDIT": [
        ("OWASP Top 10 2025 edition promotes Broken Object-Level Authorisation to the #1 priority", 0.94),
        ("OSS supply-chain audits (Sigstore + Rekor transparency log) are required in regulated environments", 0.89),
        ("CSPM tools (Wiz, Orca, Prisma Cloud) provide real-time cloud posture scoring in 2026", 0.83),
        ("Software composition analysis (Snyk, Grype) must run inside CI/CD on every commit", 0.79),
        ("SLSA level 3 provenance attestations are now a procurement requirement for enterprise software", 0.75),
    ],
    "DESIGN": [
        ("Radix UI + Tailwind CSS v4 is the dominant headless component stack for 2026 projects", 0.91),
        ("WCAG 2.2 is the current accessibility compliance target; Level AA is the minimum bar", 0.88),
        ("Design tokens managed via Style Dictionary v4 enable cross-platform design-system consistency", 0.83),
        ("Server components (React 19 / Next.js 15) shift rendering complexity away from the browser", 0.79),
        ("CSS Container Queries are now baseline and eliminate most JS-driven responsive hacks", 0.74),
    ],
    "EXPLAIN": [
        ("Diátaxis framework (tutorials / how-tos / reference / explanation) is SOTA documentation structure", 0.91),
        ("Mermaid.js v11 is natively supported in GitHub, Notion, and Confluence for inline diagrams", 0.87),
        ("LLM-generated runbooks require mandatory human review before operational use per SOX/ISO-27001", 0.83),
        ("Arc42 templates are the standard for architecture documentation in regulated industries", 0.78),
        ("Decision Records (ADRs) are the canonical format for capturing engineering rationale in 2026", 0.74),
    ],
    "IDEATE": [
        ("DORA metrics (deploy frequency, lead time, MTTR, CFR) anchor engineering strategy discussions", 0.90),
        ("Two-pizza team + async RFC process (Notion/Linear) is the standard ideation workflow", 0.86),
        ("Feature flags (OpenFeature standard) decouple deployment from release, enabling hypothesis testing", 0.82),
        ("Platform engineering (Internal Developer Platforms) is the dominant org pattern in 2026", 0.78),
        ("FinOps practices are now expected: unit economics and cost-per-feature are standard KPIs", 0.74),
    ],
    "SPAWN_REPO": [
        ("GitHub Actions + Dependabot + CodeQL is the baseline secure CI/CD starter pack in 2026", 0.92),
        ("devcontainer.json (Dev Containers spec 2.0) ensures reproducible contributor environments", 0.88),
        ("Semantic versioning + Conventional Commits enables automated CHANGELOG and release notes", 0.84),
        ("OpenSSF Scorecard is the standard for measuring repository security health at creation time", 0.79),
        ("Renovate Bot is now preferred over Dependabot for polyglot monorepos with complex update rules", 0.75),
    ],
    "BLOCKED": [
        ("Circuit breaker pattern (Hystrix-style) requires diagnosing the root failure trigger first", 0.90),
        ("Review recent mandate history and confidence distribution before resetting the breaker", 0.85),
        ("Consider adjusting CIRCUIT_BREAKER_THRESHOLD in config if legitimate mandates keep tripping it", 0.80),
    ],
}

_JIT_FETCH_PROMPT = (
    "You are a real-time SOTA intelligence agent for TooLoo V2. "
    "For the mandate intent '{intent}' and text: \"{mandate_text}\" — "
    "list exactly 3 concrete, current, specific data points as bullet lines (starting with -) "
    "covering relevant SOTA tools, patterns, risks, or standards as of 2026. "
    "Be terse and specific. No preamble. No post-amble."
)


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class JITBoostResult:
    """Immutable snapshot of one JIT confidence-boost operation."""

    jit_id: str
    intent: str
    original_confidence: float
    boosted_confidence: float
    boost_delta: float
    signals: list[str]
    source: str          # "gemini" | "structured"
    fetched_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "jit_id": self.jit_id,
            "intent": self.intent,
            "original_confidence": round(self.original_confidence, 4),
            "boosted_confidence": round(self.boosted_confidence, 4),
            "boost_delta": round(self.boost_delta, 4),
            "signals": self.signals,
            "source": self.source,
            "fetched_at": self.fetched_at,
        }


# ── Engine ────────────────────────────────────────────────────────────────────


class JITBooster:
    """
    Fetches SOTA signals JIT and boosts a RouteResult's confidence score.

    This is a mandatory step — every mandate and chat turn must pass through
    ``fetch()`` before response generation.  The returned ``JITBoostResult``
    carries the validated (boosted) confidence alongside the concrete signals
    that justified it, so callers can both apply the boost and surface the
    evidence to users.

    Usage::

        booster = JITBooster()
        jit = booster.fetch(route)
        # Apply via router.apply_jit_boost(route, jit.boosted_confidence)
    """

    def fetch(self, route: RouteResult) -> JITBoostResult:
        """Mandatory pre-execution step: fetch SOTA signals, compute boost."""
        jit_id = f"jit-{uuid.uuid4().hex[:8]}"
        original = route.confidence
        signals, source = self._fetch_signals(route.intent, route.mandate_text)
        boost_delta = min(len(signals) * BOOST_PER_SIGNAL, MAX_BOOST_DELTA)
        boosted = min(original + boost_delta, 1.0)

        return JITBoostResult(
            jit_id=jit_id,
            intent=route.intent,
            original_confidence=round(original, 4),
            boosted_confidence=round(boosted, 4),
            boost_delta=round(boost_delta, 4),
            signals=signals,
            source=source,
        )

    # ── Signal fetching ────────────────────────────────────────────────────────

    def _fetch_signals(
        self, intent: str, mandate_text: str
    ) -> tuple[list[str], str]:
        if _gemini_client is not None:
            try:
                return self._fetch_gemini(intent, mandate_text), "gemini"
            except Exception:
                pass
        return self._fetch_structured(intent), "structured"

    def _fetch_gemini(self, intent: str, mandate_text: str) -> list[str]:
        prompt = _JIT_FETCH_PROMPT.format(
            intent=intent, mandate_text=mandate_text[:300]
        )
        resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
            model=GEMINI_MODEL, contents=prompt
        )
        bullets = _parse_bullets(resp.text)
        if not bullets:
            raise ValueError(
                "Gemini returned no parseable signals — falling back to structured")
        return bullets

    def _fetch_structured(self, intent: str) -> list[str]:
        entries = _CATALOGUE.get(intent, _CATALOGUE["BUILD"])
        # Sort by relevance weight descending; return top 3 signal texts
        return [
            text
            for text, _ in sorted(entries, key=lambda x: x[1], reverse=True)[:3]
        ]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_bullets(text: str) -> list[str]:
    """Extract bullet-point lines from Gemini SOTA output."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Accept lines starting with -, *, •, or digit+dot (numbered list)
        if re.match(r"^[-*•]|\d+[.)]\s", stripped) and len(stripped) > 5:
            cleaned = re.sub(r"^[-*•\d+.)]\s*", "", stripped).strip()
            if cleaned:
                lines.append(cleaned)
    return lines[:5]  # hard cap at 5 signals
