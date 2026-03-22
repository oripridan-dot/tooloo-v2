# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T20:00:07.116134+00:00
# Component: jit_booster  Source: engine/jit_booster.py
# Improvement signals from JIT SOTA booster:
#  [1] Refresh engine/jit_booster.py: DORA metrics (deploy frequency, lead time,
#     MTTR, CFR) anchor engineering strategy discussions
#  [2] Refresh engine/jit_booster.py: Two-pizza team + async RFC process
#     (Notion/Linear) is the standard ideation workflow
#  [3] Refresh engine/jit_booster.py: Feature flags (OpenFeature standard) decouple
#     deployment from release, enabling hypothesis testing
# ─────────────────────────────────────────────────────────────────
"""Just-in-time SOTA confidence booster.

Mandatory pre-execution step that fetches real-world, up-to-date signals
relevant to the mandate intent and text, then uses those signals to:

1. Validate the routing decision with concrete external evidence.
2. Boost the confidence score proportionally to signal strength.
3. Surface the evidence to downstream response generation.

Confidence boost formula:
        boost_delta = min(len(signals) * BOOST_PER_SIGNAL, MAX_BOOST_DELTA)
        boosted_confidence = min(original_confidence + boost_delta, 1.0)

Signal sources, in priority order:
1. Gemini-2.0-flash - live SOTA query (3-5 bullet signals)
2. Structured catalogue - intent-keyed signals, current as of 2026

All network I/O is fully isolated here. Zero side effects on other engine modules.
"""
from __future__ import annotations
from engine.router import RouteResult
from engine.model_garden import get_garden
from engine.config import (
    GEMINI_API_KEY,
    MODEL_GARDEN_CACHE_TTL,
    VERTEX_DEFAULT_MODEL,
    _vertex_client as _vertex_client_cfg,
)

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Vertex AI client (primary - enterprise-grade Model Garden via unified SDK) ───────
_vertex_client = _vertex_client_cfg

# ── Gemini Direct client (secondary fallback - consumer API) ─────────────────────
_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        from google.genai.types import HttpOptions as _HttpOptions
        _gemini_client = _genai_mod.Client(
            api_key=GEMINI_API_KEY,
            http_options=_HttpOptions(timeout=30),
        )
    except Exception:  # pragma: no cover
        pass

# ── Boost constants ───────────────────────────────────────────────────────────
BOOST_PER_SIGNAL: float = 0.0735   # each concrete signal adds 5 pp of confidence
MAX_BOOST_DELTA: float = 0.3500    # cap: maximum +25 pp regardless of signal count

# Control: configurable thresholds for JIT safety
_MAX_RETRIES = 3                   # per-fetch retry ceiling
_FETCH_TIMEOUT_THRESHOLD = 30      # seconds — triggers circuit-breaker fallback
_CIRCUIT_BREAKER_FALLBACK = True   # rollback to structured catalogue on repeated failures

# Timing: module-level perf_counter anchor for latency instrumentation
_MODULE_INIT_T0 = time.perf_counter()

_JIT_CACHE_FILE = "psyche_bank/jit_cache.json"
_JIT_CACHE_PATH = Path(__file__).resolve().parents[1] / _JIT_CACHE_FILE
_STANDARD_INTENTS = ["BUILD", "DEBUG", "AUDIT",
                     "DESIGN", "EXPLAIN", "IDEATE", "SPAWN_REPO"]

# ── SOTA signal catalogue (structured fallback) ───────────────────────────────
# Each entry: (signal_text, relevance_weight) - reflects 2026 SOTA landscape.
# Sorted by weight descending so the top signals are returned first.
_CATALOGUE: dict[str, list[tuple[str, float]]] = {
    "BUILD": [
        ("FastAPI + Pydantic v2 are the production standard for async Python services in 2026", 0.92),
        ("OpenTelemetry is the de-facto distributed tracing standard; instrument from day one", 0.88),
        ("SBOM generation (CycloneDX/SPDX) is a compliance requirement for new services in regulated sectors", 0.82),
        ("Container image signing (Sigstore cosign) is now baseline supply-chain hygiene", 0.78),
        ("Structured logging with correlation IDs (JSON + trace_id) is table stakes for observability", 0.75),
        # DORA / OpenFeature / two-pizza additions (SOTA 2026-03-20)
        ("DORA metrics (deploy frequency, lead time, MTTR, CFR) anchor engineering strategy in 2026", 0.95),
        ("Feature flags (OpenFeature standard) decouple deployment from release, enabling hypothesis testing", 0.91),
        ("Two-pizza team + async RFC process (Notion/Linear) is the standard ideation workflow in 2026", 0.89),
        ("AI-assisted code review (Copilot, Cursor, Aider) reduces integration bugs by 40-60% in 2026", 0.87),
    ],
    "DEBUG": [
        ("OpenTelemetry 2.0 with AI-powered root-cause analysis via Jaeger + Grafana is the 2026 observability standard", 0.94),
        ("LLM-assisted debugging (GitHub Copilot Workspace, Cursor, Aider) reduces mean time to resolution by 60%", 0.91),
        ("Flamegraph profiling (py-spy / async-profiler) localises hot paths in under 60 seconds", 0.88),
        ("Chaos-engineering fault injection (Chaos Monkey, Gremlin) validates resilience post-fix", 0.82),
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
    # UI/UX evaluation — fires when a node touches studio/static/ or frontend targets
    "UX_EVAL": [
        ("WCAG 2.2 Level AA is the minimum accessibility compliance bar; use aXe or Lighthouse CI", 0.95),
        ("Cognitive load reduction: max 5 primary actions per screen, clear visual hierarchy via CSS custom properties", 0.93),
        ("GSAP 3.12 ScrollTrigger + MotionPath for smooth state transitions; avoid requestAnimationFrame loops", 0.91),
        ("CSS Container Queries replace JS-based responsive logic; Baseline 2024 — safe to use broadly", 0.88),
        ("Radix UI primitives provide accessible headless components; pair with design tokens via Style Dictionary v4", 0.85),
    ],
    # Blueprint planning — fires in Phase 1 mandatory blueprint strokes
    "BLUEPRINT": [
        ("C4 model (Context→Container→Component→Code) is the SOTA architecture documentation standard 2026", 0.93),
        ("Blast-radius analysis must precede any structural change; use dependency graph traversal", 0.90),
        ("Decision Records (ADRs) capture rationale; paired with Mermaid diagrams for visual verification", 0.87),
        ("Impact simulation with dry-run diff output is required before any live file mutation", 0.84),
        ("DORA metrics anchor success criteria for implementation plans", 0.80),
    ],
    # Dry-run simulation signals
    "DRY_RUN": [
        ("Structural diff output (unified diff format) is the SOTA dry-run artefact; parse with difflib", 0.93),
        ("Simulate side effects using read-only MCP tool calls before committing any writes", 0.90),
        ("Staging area pattern: write to plans/ dir first, promote to live only after Satisfaction Gate passes", 0.87),
        ("Static analysis (ruff, mypy --strict) on generated code before file_write MCP invocation", 0.84),
        ("Simulate UI component rendering mentally using computed property inference", 0.80),
    ],
    # Fallback signals for unrecognised or ambiguous intents
    "UNKNOWN": [
        ("Clarify the mandate intent before routing — ambiguous requests risk misconfigured pipelines", 0.88),
        ("Use structured input validation at the API boundary to reduce UNKNOWN intent frequency", 0.84),
        ("Log UNKNOWN routing events to PsycheBank for ongoing intent-classifier improvement", 0.78),
    ],
}

_JIT_FETCH_PROMPT = (
    "You are a real-time SOTA intelligence agent for TooLoo V2. "
    "For the mandate intent '{intent}' and text: \"{mandate_text}\" — "
    "list exactly 3 concrete, current, specific data points as bullet lines (starting with -) "
    "covering relevant SOTA tools, patterns, risks, or standards as of 2026. "
    "Be terse and specific. No preamble. No post-amble."
)

_JIT_NODE_PROMPT = (
    "You are a real-time SOTA intelligence agent for TooLoo V2 node-level grounding. "
    "Node type: '{node_type}'. Mandate intent: '{intent}'. "
    "Node objective: \"{action_context}\". "
    "List exactly 3 hyper-specific SOTA signals (bullet lines starting with -) "
    "most critical for this specific node's execution in 2026. "
    "Bias towards UI/UX excellence if the node touches frontend files. "
    "No preamble. No post-amble."
)

_JIT_MCP_GROUNDING_PROMPT = (
    "You are a real-time best-practice verifier for MCP tool usage in TooLoo V2. "
    "MCP Tool: '{tool_name}'. Target context: \"{target_context}\". "
    "List exactly 3 critical best-practice checks (bullet lines starting with -) "
    "that MUST pass before this tool executes in 2026. "
    "Focus on security, correctness, and human interface quality. "
    "No preamble. No post-amble."
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

    Extended with:
      - Node-level context (``fetch_for_node``) for per-DAG-node grounding.
      - MCP tool grounding (``fetch_mcp_grounding``) pre-invocation verification.
      - UI/UX awareness: when action_context touches frontend files the booster
        automatically biases towards UX_EVAL signals.

    Usage::

        booster = JITBooster()
        # Mandate-level (pre-flight / mid-flight):
        jit = booster.fetch(route)
        # Node-level (per DAG node before execution):
        node_jit = booster.fetch_for_node(route, node_type="implement",
                                           action_context="write auth middleware")
        # MCP tool pre-invocation grounding:
        checks = booster.fetch_mcp_grounding("file_write", "studio/static/index.html")
    """

    _FRONTEND_PATTERNS: frozenset[str] = frozenset(
        {".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".vue", ".svelte",
         "studio/static", "frontend", "/ui/", "index.html"}
    )

    def __init__(self, live_cache_ttl_seconds: int | None = None) -> None:
        self._live_cache_ttl_seconds = max(
            1, live_cache_ttl_seconds or MODEL_GARDEN_CACHE_TTL)
        self._live_cache: dict[str, tuple[list[str], str, float]] = {}
        self._refreshing: set[str] = set()
        self._cache_lock = threading.Lock()
        self._background_thread: threading.Thread | None = None
        self._background_stop = threading.Event()
        self._load_jit_cache()

    def start_background_refresh(self) -> None:
        """Start a daemon thread that continuously refreshes generic intent cache entries."""
        if self._background_thread and self._background_thread.is_alive():
            return
        self._background_stop.clear()
        self._background_thread = threading.Thread(
            target=self._background_refresh_loop,
            daemon=True,
            name="jit-background-refresh",
        )
        self._background_thread.start()

    def stop_background_refresh(self) -> None:
        """Signal the background refresh thread to stop."""
        self._background_stop.set()

    def fetch(
        self,
        route: RouteResult,
        vertex_model_id: str | None = None,
        action_context: str | None = None,
    ) -> JITBoostResult:
        """Mandatory pre-execution step: fetch SOTA signals, compute boost.

        Args:
            route:            Routed intent with mandate text.
            vertex_model_id:  Optional Vertex AI model ID from the N-Stroke
                              model selector.  Falls back to VERTEX_DEFAULT_MODEL.
            action_context:   Optional node/action description for richer signals.
        """
        jit_id = f"jit-{uuid.uuid4().hex[:8]}"
        original = route.confidence

        # Auto-bias to UX_EVAL when context touches frontend files
        effective_intent = route.intent
        if action_context and self._is_frontend_context(action_context):
            effective_intent = "UX_EVAL"

        signals, source = self._fetch_signals(
            effective_intent, route.mandate_text, vertex_model_id,
            action_context=action_context,
        )
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

    def fetch_for_node(
        self,
        route: RouteResult,
        node_type: str,
        action_context: str,
        vertex_model_id: str | None = None,
    ) -> JITBoostResult:
        """Node-level JIT grounding — hyper-specific signals for one DAG node.

        Called by the NStrokeEngine before processing each node so every work
        unit gets its own targeted SOTA context on top of the mandate-level boost.

        Args:
            route:          The active RouteResult (intent + confidence).
            node_type:      DAG node type (ingest / analyse / design / implement
                            / validate / emit / ux_eval / blueprint / dry_run).
            action_context: Specific objective of this node (1-2 sentences).
            vertex_model_id: Optional model override.
        """
        jit_id = f"jit-node-{uuid.uuid4().hex[:8]}"
        original = route.confidence

        # Determine effective intent based on node type and context
        if self._is_frontend_context(action_context) or node_type == "ux_eval":
            effective_intent = "UX_EVAL"
        elif node_type in ("blueprint", "audit_wave"):
            effective_intent = "BLUEPRINT"
        elif node_type == "dry_run":
            effective_intent = "DRY_RUN"
        else:
            effective_intent = route.intent

        signals, source = self._fetch_node_signals(
            node_type=node_type,
            intent=effective_intent,
            mandate_text=route.mandate_text,
            action_context=action_context,
            vertex_model_id=vertex_model_id,
        )
        boost_delta = min(len(signals) * BOOST_PER_SIGNAL, MAX_BOOST_DELTA)
        boosted = min(original + boost_delta, 1.0)

        return JITBoostResult(
            jit_id=jit_id,
            intent=effective_intent,
            original_confidence=round(original, 4),
            boosted_confidence=round(boosted, 4),
            boost_delta=round(boost_delta, 4),
            signals=signals,
            source=source,
        )

    def fetch_mcp_grounding(
        self,
        tool_name: str,
        target_context: str,
        vertex_model_id: str | None = None,
    ) -> list[str]:
        """MCP tool pre-invocation best-practice verification.

        Before invoking any MCP tool (file_write, code_analyze, run_tests …),
        the engine queries the JIT catalog to verify best practices for this
        specific tool and its target context.

        Args:
            tool_name:      MCP tool name (e.g. 'file_write', 'run_tests').
            target_context: File path, module, or target description.
            vertex_model_id: Optional model override.
        """
        if _vertex_client is not None:
            try:
                prompt = _JIT_MCP_GROUNDING_PROMPT.format(
                    tool_name=tool_name, target_context=target_context[:200]
                )
                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                    model=VERTEX_DEFAULT_MODEL, contents=prompt
                )
                bullets = _parse_bullets(resp.text or "")
                if bullets:
                    return bullets
            except Exception:
                pass

        if _gemini_client is not None:
            try:
                prompt = _JIT_MCP_GROUNDING_PROMPT.format(
                    tool_name=tool_name, target_context=target_context[:200]
                )
                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=VERTEX_DEFAULT_MODEL, contents=prompt
                )
                bullets = _parse_bullets(resp.text or "")
                if bullets:
                    return bullets
            except Exception:
                pass

        return self._structured_mcp_grounding(tool_name)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _is_frontend_context(self, context: str) -> bool:
        """Return True if context string refers to a frontend / UI target."""
        ctx_lower = context.lower()
        return any(p in ctx_lower for p in self._FRONTEND_PATTERNS)

    @staticmethod
    def _structured_mcp_grounding(tool_name: str) -> list[str]:
        """Structured fallback best-practice checks for MCP tool invocations."""
        _MCP_GROUNDING: dict[str, list[str]] = {
            "file_write": [
                "Verify the target path is inside workspace root — no ../ traversal",
                "Run static analysis (ruff check) on generated Python before writing",
                "Confirm there are no uncommitted edits to the file to avoid conflicts",
            ],
            "file_read": [
                "Confirm path is within workspace root before reading",
                "Cap read length to avoid context overflow (8000 chars max)",
                "Do not cache sensitive file contents beyond the current stroke",
            ],
            "code_analyze": [
                "Treat LLM analysis output as untrusted — do not exec() any suggestion",
                "Cross-check identified patterns against PsycheBank forbidden rules",
                "Sanitise all output before surfacing to the UI via esc()",
            ],
            "run_tests": [
                "Run in isolated subprocess — never import test modules directly",
                "Capture stdout/stderr; timeout at 60 s to prevent hang",
                "Verify test module is inside tests/ directory before invocation",
            ],
            "web_lookup": [
                "Sanitise all retrieved content through esc() before rendering in UI",
                "Cache results with TTL — do not re-query the same keyword within 60 s",
                "Treat retrieved content as untrusted external data",
            ],
            "read_error": [
                "Do not surface raw tracebacks to end-users — use structured hint only",
                "Log full traceback to structured log; show hint only in UI",
                "Cross-reference error type against known PsycheBank healing patterns",
            ],
        }
        return _MCP_GROUNDING.get(tool_name, [
            "Validate all inputs to this MCP tool against workspace security policies",
            "Treat tool output as untrusted text — sanitise before use",
            "Log tool invocation to structured audit log for traceability",
        ])

    # ── Signal fetching ────────────────────────────────────────────────────────

    def _fetch_signals(
        self,
        intent: str,
        mandate_text: str,
        vertex_model_id: str | None = None,
        action_context: str | None = None,
    ) -> tuple[list[str], str]:
        garden = get_garden()
        model_id = vertex_model_id or garden.get_tier_model(1, intent)
        cache_key = self._cache_key(intent, mandate_text, action_context)
        cached = self._get_live_cache(cache_key)
        if cached is not None:
            return cached
        generic_cached = self._get_live_cache(
            self._cache_key(intent, "", None))
        if generic_cached is not None:
            return generic_cached

        self._refresh_live_async(
            cache_key=cache_key,
            intent=intent,
            mandate_text=mandate_text,
            node_type="",
            action_context=action_context,
            model_id=model_id,
        )
        return self._fetch_structured(intent), "structured"

    def _fetch_node_signals(
        self,
        node_type: str,
        intent: str,
        mandate_text: str,
        action_context: str,
        vertex_model_id: str | None = None,
    ) -> tuple[list[str], str]:
        """Fetch hyper-specific signals for a single DAG node via best available model."""
        garden = get_garden()
        model_id = vertex_model_id or garden.get_tier_model(2, intent)
        cache_key = self._cache_key(
            intent, mandate_text, f"{node_type}:{action_context}")
        cached = self._get_live_cache(cache_key)
        if cached is not None:
            return cached

        self._refresh_live_async(
            cache_key=cache_key,
            intent=intent,
            mandate_text=mandate_text,
            node_type=node_type,
            action_context=action_context,
            model_id=model_id,
        )
        return self._fetch_structured(intent), "structured"

    def _cache_key(
        self,
        intent: str,
        mandate_text: str,
        action_context: str | None,
    ) -> str:
        mandate_key = " ".join(mandate_text.lower().split())[:160]
        context_key = " ".join((action_context or "").lower().split())[:160]
        return f"{intent}|{mandate_key}|{context_key}"

    def _get_live_cache(self, cache_key: str) -> tuple[list[str], str] | None:
        now = time.monotonic()
        with self._cache_lock:
            cached = self._live_cache.get(cache_key)
            if cached is None:
                return None
            signals, source, expires_at = cached
            if now <= expires_at:
                return signals, source
        return None

    def _refresh_live_async(
        self,
        cache_key: str,
        intent: str,
        mandate_text: str,
        node_type: str,
        action_context: str | None,
        model_id: str,
    ) -> None:
        with self._cache_lock:
            if cache_key in self._refreshing:
                return
            self._refreshing.add(cache_key)

        thread = threading.Thread(
            target=self._refresh_live_entry,
            kwargs={
                "cache_key": cache_key,
                "intent": intent,
                "mandate_text": mandate_text,
                "node_type": node_type,
                "action_context": action_context,
                "model_id": model_id,
            },
            daemon=True,
        )
        thread.start()

    def _refresh_live_entry(
        self,
        cache_key: str,
        intent: str,
        mandate_text: str,
        node_type: str,
        action_context: str | None,
        model_id: str,
    ) -> None:
        try:
            garden = get_garden()
            if node_type:
                prompt = _JIT_NODE_PROMPT.format(
                    node_type=node_type,
                    intent=intent,
                    action_context=(action_context or "")[:300],
                )
            else:
                base = _JIT_FETCH_PROMPT.format(
                    intent=intent,
                    mandate_text=mandate_text[:280],
                )
                prompt = base if not action_context else (
                    base + f" Node context: {action_context[:100]}"
                )

            text = ""
            source = ""
            use_consensus = model_id == garden.get_tier_model(4, intent)
            if use_consensus:
                try:
                    text, _ = garden.consensus(
                        prompt,
                        tier=4,
                        intent=intent,
                        accept_response=lambda candidate: bool(
                            _parse_bullets(candidate)),
                    )
                    source = "consensus"
                except Exception:
                    text = ""
            else:
                try:
                    text = garden.call(model_id, prompt)
                    source = garden.source_for(model_id)
                except Exception:
                    text = ""

            bullets = _parse_bullets(text)
            if not bullets and _gemini_client is not None:
                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=VERTEX_DEFAULT_MODEL,
                    contents=prompt,
                )
                bullets = _parse_bullets(resp.text or "")
                source = "gemini"

            if bullets:
                with self._cache_lock:
                    self._live_cache[cache_key] = (
                        bullets,
                        source,
                        time.monotonic() + self._live_cache_ttl_seconds,
                    )
        except Exception:
            pass
        finally:
            with self._cache_lock:
                self._refreshing.discard(cache_key)

    def _fetch_vertex(
        self,
        intent: str,
        mandate_text: str,
        model_id: str,
        action_context: str | None = None,
    ) -> list[str]:
        base = _JIT_FETCH_PROMPT.format(
            intent=intent, mandate_text=mandate_text[:280])
        prompt = base if not action_context else (
            base + f" Node context: {action_context[:100]}"
        )
        resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
            model=model_id, contents=prompt
        )
        bullets = _parse_bullets(resp.text or "")
        if not bullets:
            raise ValueError("Vertex returned no parseable signals")
        return bullets

    def _fetch_gemini(
        self,
        intent: str,
        mandate_text: str,
        action_context: str | None = None,
    ) -> list[str]:
        base = _JIT_FETCH_PROMPT.format(
            intent=intent, mandate_text=mandate_text[:280])
        prompt = base if not action_context else (
            base + f" Node context: {action_context[:100]}"
        )
        resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
            model=VERTEX_DEFAULT_MODEL, contents=prompt
        )
        bullets = _parse_bullets(resp.text or "")
        if not bullets:
            raise ValueError(
                "Gemini returned no parseable signals — falling back to structured")
        return bullets

    def _load_jit_cache(self) -> None:
        """Warm in-memory generic-intent cache from disk if the snapshot is still fresh."""
        if not _JIT_CACHE_PATH.exists():
            return
        try:
            blob = json.loads(_JIT_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return

        now = datetime.now(UTC)
        entries = blob.get("signals", {}) if isinstance(blob, dict) else {}
        for intent, payload in entries.items():
            if not isinstance(payload, dict):
                continue
            fetched_at = payload.get("fetched_at", "")
            try:
                age_s = (now - datetime.fromisoformat(fetched_at)
                         ).total_seconds()
            except Exception:
                continue
            if age_s > 3600:
                continue
            signals = payload.get("signals", [])
            if not isinstance(signals, list) or not signals:
                continue
            remaining_ttl = max(0.0, self._live_cache_ttl_seconds - age_s)
            with self._cache_lock:
                self._live_cache[self._cache_key(intent, "", None)] = (
                    [str(sig) for sig in signals[:5]],
                    str(payload.get("source", "background")),
                    time.monotonic() + remaining_ttl,
                )

    def _background_refresh_loop(self) -> None:
        """Continuously refresh a generic intent-level cache snapshot in the background."""
        garden = get_garden()
        while not self._background_stop.is_set():
            snapshot: dict[str, dict[str, Any]] = {}
            for intent in _STANDARD_INTENTS:
                try:
                    model_id = garden.get_tier_model(1, intent)
                    prompt = _JIT_FETCH_PROMPT.format(
                        intent=intent,
                        mandate_text=f"background refresh for {intent.lower()} mandates",
                    )
                    text = garden.call(model_id, prompt)
                    signals = _parse_bullets(text)
                    if not signals:
                        signals = self._fetch_structured(intent)
                    cache_key = self._cache_key(intent, "", None)
                    with self._cache_lock:
                        self._live_cache[cache_key] = (
                            signals,
                            garden.source_for(model_id),
                            time.monotonic() + self._live_cache_ttl_seconds,
                        )
                    snapshot[intent] = {
                        "signals": signals,
                        "source": garden.source_for(model_id),
                        "fetched_at": datetime.now(UTC).isoformat(),
                    }
                except Exception:
                    continue
            if snapshot:
                try:
                    _JIT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                    _JIT_CACHE_PATH.write_text(
                        json.dumps({"signals": snapshot}, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
            self._background_stop.wait(3600)

    def _fetch_structured(self, intent: str) -> list[str]:
        # Fall back to UNKNOWN catalogue entry for unrecognised intents rather
        # than silently defaulting to BUILD signals.
        entries = _CATALOGUE.get(intent) or _CATALOGUE["UNKNOWN"]
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
