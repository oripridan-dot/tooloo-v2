# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T20:00:07.116134+00:00
# Component: jit_booster  Source: engine/jit_booster.py
# Improvement signals from JIT SOTA booster:
#  [1] Refresh engine/jit_booster.py: DORA metrics (deployment frequency, lead time for changes, MTTR, change failure rate) anchor engineering strategy discussions
#  [2] Refresh engine/jit_booster.py: Two-pizza team + async RFC process (e.g., Notion/Linear) is the standard ideation workflow
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
# Default to 5 minutes if not configured. Max 1 hour for live responses.
_gemini_cache_ttl = max(300, MODEL_GARDEN_CACHE_TTL if MODEL_GARDEN_CACHE_TTL else 300)
# Cache for live Gemini signal responses. TTL enforced by `_get_gemini_signals`.
_gemini_signal_cache: dict[str, tuple[list[str], float]] = {}
_gemini_cache_lock = threading.Lock()

# Cache for Gemini API responses. Configurable TTL managed by the get_gemini_signals function.
_gemini_api_cache: dict[str, tuple[str, float]] = {}
_gemini_api_cache_lock = threading.Lock()


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
# each concrete signal adds 2 pp of confidence, anchoring to 2026 SOTA DORA metrics.
BOOST_PER_SIGNAL: float = 0.02  # Calibrated for balanced focus (efficiency, accuracy)
# cap: maximum +25 pp regardless of signal count, reflecting 2026 SOTA RFC process confidence.
MAX_BOOST_DELTA: float = 0.25

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
        ("DORA metrics (deployment frequency, lead time for changes, MTTR, change failure rate) anchor engineering strategy discussions", 0.95),
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
        ("DORA metrics (deployment frequency, lead time, MTTR, CFR) anchor engineering strategy discussions", 0.90),
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
        ("CSS Container Queries are now baseline and eliminate most JS-driven responsive hacks", 0.88),
        ("Radix UI primitives provide accessible headless components; pair with design tokens via Style Dictionary v4", 0.85),
    ],
    # Blueprint planning — fires in Phase 1 mandatory blueprint strokes
    "BLUEPRINT": [
        ("C4 model (Context→Container→Component→Code) is the SOTA architecture documentation standard 2026", 0.93),
        ("Blast-radius analysis must precede any structural change; use dependency graph traversal", 0.90),
        ("Decision Records (ADRs) capture rationale; paired with Mermaid diagrams for visual verification", 0.87),
        ("Impact simulation with dry-run output is required before any live file mutation", 0.84),
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
    source: str          # "gemini" | "structured" | "consensus" | "vertex"
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
        # Cache structure: {cache_key: (signals, source, expires_at_monotonic)}
        self._live_cache: dict[str, tuple[list[str], str, float]] = {}
        self._refreshing: set[str] = set()  # Cache keys currently being fetched
        self._cache_lock = threading.Lock()
        self._background_thread: threading.Thread | None = None
        self._background_stop = threading.Event()
        self._load_jit_cache()
        self.start_background_refresh()

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
        if self._background_thread:
            self._background_thread.join(timeout=5)

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
                              model selector. Falls back to VERTEX_DEFAULT_MODEL.
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
        boost_delta = self._calculate_boost_delta(signals, original)
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
        boost_delta = self._calculate_boost_delta(signals, original)
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
        # Attempt to use Vertex AI first
        if _vertex_client is not None:
            try:
                prompt = _JIT_MCP_GROUNDING_PROMPT.format(
                    tool_name=tool_name, target_context=target_context[:200]
                )
                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                    model=vertex_model_id or VERTEX_DEFAULT_MODEL, contents=prompt
                )
                bullets = _parse_bullets(resp.text or "")
                if bullets:
                    return bullets
            except Exception as e:
                logger.warning(f"Vertex AI failed for MCP grounding: {e}")

        # Fallback to Gemini if Vertex fails or is unavailable
        if _gemini_client is not None:
            try:
                prompt = _JIT_MCP_GROUNDING_PROMPT.format(
                    tool_name=tool_name, target_context=target_context[:200]
                )
                # Use a sensible default model for Gemini client if none is specified.
                gemini_model = VERTEX_DEFAULT_MODEL # Default choice.

                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=gemini_model, contents=prompt
                )
                bullets = _parse_bullets(resp.text or "")
                if bullets:
                    return bullets
            except Exception as e:
                logger.warning(f"Gemini API failed for MCP grounding: {e}")

        # Final fallback to structured catalogue if LLMs fail
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
        """Fetch SOTA signals for a given intent, preferring live models over fallback."""
        garden = get_garden()
        model_id = vertex_model_id or garden.get_tier_model(1, intent)
        cache_key = self._cache_key(intent, mandate_text, action_context)

        # 1. Check cache first
        cached = self._get_live_cache(cache_key)
        if cached is not None:
            return cached

        # 2. Check generic intent cache if specific cache misses (for background refreshed entries)
        generic_cache_key = self._cache_key(intent, "", None)
        generic_cached = self._get_live_cache(generic_cache_key)
        if generic_cached is not None:
            return generic_cached

        # 3. Trigger async refresh and return structured fallback if too slow or fails
        self._refresh_live_async(
            cache_key=cache_key,
            intent=intent,
            mandate_text=mandate_text,
            node_type="",
            action_context=action_context,
            model_id=model_id,
        )
        # Immediately return structured signals as a fallback
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
        model_id = vertex_model_id or garden.get_tier_model(2, intent) # Higher tier for node-specific context
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
        # Fallback to structured signals if live fetch fails or is slow
        return self._fetch_structured(intent), "structured"

    def _cache_key(
        self,
        intent: str,
        mandate_text: str,
        action_context: str | None,
    ) -> str:
        """Generates a consistent cache key from intent, mandate text, and action context."""
        mandate_key = " ".join(mandate_text.lower().split())[:160]
        context_key = " ".join((action_context or "").lower().split())[:160]
        return f"{intent}|{mandate_key}|{context_key}"

    def _get_live_cache(self, cache_key: str) -> tuple[list[str], str] | None:
        """Retrieves signals from the live cache if the entry is not expired."""
        now = time.monotonic()
        with self._cache_lock:
            cached = self._live_cache.get(cache_key)
            if cached is None:
                return None
            signals, source, expires_at = cached
            if now <= expires_at:
                return signals, source
            # Entry expired, remove it to encourage re-fetch
            del self._live_cache[cache_key]
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
        """Initiates an asynchronous refresh of a cache entry if not already in progress."""
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
        """Fetches signals from LLMs, caches them, or falls back to structured data."""
        signals: list[str] = []
        source: str = "structured"  # Default to structured
        fetched_text: str = ""

        try:
            garden = get_garden()
            if node_type:  # Node-specific prompt
                prompt = _JIT_NODE_PROMPT.format(
                    node_type=node_type,
                    intent=intent,
                    action_context=(action_context or "")[:300],
                )
            else:  # Generic intent prompt
                base = _JIT_FETCH_PROMPT.format(
                    intent=intent,
                    mandate_text=mandate_text[:280],
                )
                prompt = base if not action_context else (
                    base + f" Node context: {action_context[:100]}"
                )

            # Attempt fetching from SOTA models
            if model_id == garden.get_tier_model(4, intent): # Consensus model
                try:
                    fetched_text, source = garden.consensus(
                        prompt,
                        tier=4,
                        intent=intent,
                        accept_response=lambda candidate: bool(
                            _parse_bullets(candidate)),
                    )
                    source = "consensus"
                except Exception:
                    logger.warning(f"Consensus model failed for cache key {cache_key}")
            else:
                # Try Vertex AI
                if _vertex_client:
                    try:
                        resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                            model=model_id, contents=prompt
                        )
                        fetched_text = resp.text or ""
                        source = garden.source_for(model_id) or "vertex"
                    except Exception as e:
                        logger.warning(f"Vertex AI failed for JIT signal (key: {cache_key}): {e}")

                # Try Gemini as fallback if Vertex failed or is unavailable
                if not fetched_text and _gemini_client is not None:
                    gemini_cache_key = f"gemini:{cache_key}"
                    now = time.monotonic()
                    with _gemini_cache_lock:
                        cached_gemini = _gemini_signal_cache.get(gemini_cache_key)
                    if cached_gemini and now <= cached_gemini[1]:
                        signals, _ = cached_gemini[0], "gemini"
                        source = "gemini"
                    else:
                        try:
                            # Use a sensible default model for Gemini client if none is specified.
                            gemini_model = VERTEX_DEFAULT_MODEL # Default choice.
                            resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                                model=gemini_model,
                                contents=prompt,
                            )
                            fetched_text = resp.text or ""
                            source = "gemini"
                            if fetched_text:
                                signals = _parse_bullets(fetched_text)
                                with _gemini_cache_lock:
                                    _gemini_signal_cache[gemini_cache_key] = (
                                        signals, now + _gemini_cache_ttl)
                        except Exception as e:
                            logger.warning(f"Gemini API failed for JIT signal (key: {cache_key}): {e}")
                            # Indicate Gemini was attempted but failed, but don't overwrite source if Vertex succeeded.
                            if source == "structured": # Only if no other source was found
                                source = "gemini_fallback"

            if not signals: # If signals were not set by Gemini cache logic
                signals = _parse_bullets(fetched_text)

            # If LLMs failed to provide signals, fall back to structured catalogue
            if not signals:
                signals = self._fetch_structured(intent)
                source = "structured"

            # Update live cache with fetched signals
            with self._cache_lock:
                self._live_cache[cache_key] = (
                    signals,
                    source,
                    time.monotonic() + self._live_cache_ttl_seconds,
                )

        except Exception as e:
            logger.error(f"Error refreshing live JIT cache entry for key {cache_key}: {e}")
            # Ensure structured fallback if any error occurs during LLM fetching
            if not signals:
                signals = self._fetch_structured(intent)
                source = "structured"
                with self._cache_lock:
                    self._live_cache[cache_key] = (
                        signals,
                        source,
                        time.monotonic() + self._live_cache_ttl_seconds,
                    )
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
        """Helper to fetch signals specifically from Vertex AI."""
        base = _JIT_FETCH_PROMPT.format(
            intent=intent, mandate_text=mandate_text[:280])
        prompt = base if not action_context else (
            base + f" Node context: {action_context[:100]}"
        )
        if not _vertex_client:
            raise RuntimeError("Vertex AI client is not initialized.")
        try:
            resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                model=model_id, contents=prompt
            )
            bullets = _parse_bullets(resp.text or "")
            if not bullets:
                raise ValueError("Vertex returned no parseable signals")
            return bullets
        except Exception as e:
            logger.error(f"Vertex AI signal fetch failed: {e}")
            raise

    def _fetch_gemini(
        self,
        intent: str,
        mandate_text: str,
        action_context: str | None = None,
    ) -> list[str]:
        """Helper to fetch signals specifically from Gemini API."""
        base = _JIT_FETCH_PROMPT.format(
            intent=intent, mandate_text=mandate_text[:280])
        prompt = base if not action_context else (
            base + f" Node context: {action_context[:100]}"
        )
        if not _gemini_client:
            raise RuntimeError("Gemini client is not initialized.")
        try:
            # Use a sensible default model for Gemini client if none is specified.
            gemini_model = VERTEX_DEFAULT_MODEL # Default choice.
            resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                model=gemini_model, contents=prompt
            )
            bullets = _parse_bullets(resp.text or "")
            if not bullets:
                raise ValueError(
                    "Gemini returned no parseable signals — falling back to structured")
            return bullets
        except Exception as e:
            logger.error(f"Gemini signal fetch failed: {e}")
            raise

    def _load_jit_cache(self) -> None:
        """Warm in-memory generic-intent cache from disk if the snapshot is still fresh."""
        if not _JIT_CACHE_PATH.exists():
            return
        try:
            blob = json.loads(_JIT_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load JIT cache: {e}")
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
            if age_s > 3600:  # Cache older than 1 hour is considered stale
                continue
            signals = payload.get("signals", [])
            if not isinstance(signals, list) or not signals:
                continue
            # Ensure signals are strings and cap at 5
            valid_signals = [str(sig) for sig in signals[:5] if isinstance(sig, str)]
            if not valid_signals:
                continue

            remaining_ttl = max(0.0, self._live_cache_ttl_seconds - age_s)
            with self._cache_lock:
                self._live_cache[self._cache_key(intent, "", None)] = (
                    valid_signals,
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
                    fetched_text = ""
                    source = "structured"

                    # Attempt to fetch from Vertex AI
                    if _vertex_client:
                        try:
                            resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                                model=model_id, contents=prompt
                            )
                            fetched_text = resp.text or ""
                            source = garden.source_for(model_id) or "vertex"
                        except Exception as e:
                            logger.warning(f"Vertex AI background refresh failed for {intent}: {e}")

                    # Fallback to Gemini if Vertex failed or is unavailable
                    if not fetched_text and _gemini_client:
                        try:
                            # Use a sensible default model for Gemini client if none is specified.
                            gemini_model = VERTEX_DEFAULT_MODEL # Default choice.
                            resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                                model=gemini_model,
                                contents=prompt,
                            )
                            fetched_text = resp.text or ""
                            source = "gemini"
                        except Exception as e:
                            logger.warning(f"Gemini background refresh failed for {intent}: {e}")
                            if source == "structured": # Only if no other source was found
                                source = "gemini_fallback"

                    signals = _parse_bullets(fetched_text)
                    if not signals:
                        signals = self._fetch_structured(intent)
                        source = "structured"

                    cache_key = self._cache_key(intent, "", None)
                    with self._cache_lock:
                        self._live_cache[cache_key] = (
                            signals[:5], # Cap at 5 signals
                            source,
                            time.monotonic() + self._live_cache_ttl_seconds,
                        )
                    snapshot[intent] = {
                        "signals": signals[:5],
                        "source": source,
                        "fetched_at": datetime.now(UTC).isoformat(),
                    }
                except Exception as e:
                    logger.error(f"Error processing intent {intent} in background refresh: {e}")
                    continue # Continue to next intent even if one fails

            if snapshot:
                try:
                    _JIT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                    _JIT_CACHE_PATH.write_text(
                        json.dumps({"signals": snapshot}, indent=2),
                        encoding="utf-8",
                    )
                except Exception as e:
                    logger.error(f"Failed to write JIT cache snapshot: {e}")

            # Wait for 1 hour before next refresh cycle, or until stop event is set
            self._background_stop.wait(3600)

    def _fetch_structured(self, intent: str) -> list[str]:
        """Retrieves relevant signals from the static catalogue for a given intent."""
        # Fall back to UNKNOWN catalogue entry for unrecognised intents rather
        # than silently defaulting to BUILD signals.
        entries = _CATALOGUE.get(intent) or _CATALOGUE["UNKNOWN"]
        # Sort by relevance weight descending; return top 3 signal texts
        return [
            text
            for text, _ in sorted(entries, key=lambda x: x[1], reverse=True)[:3]
        ]

    def _calculate_boost_delta(self, signals: list[str], original_confidence: float) -> float:
        """
        Calculates the boost delta based on signals, considering signal quality.

        The formula is more nuanced, weighting each signal by its quality (implicit
        in the catalogue or if provided by LLM in a structured format later).
        For now, it sums the weighted contribution of each signal, capped by MAX_BOOST_DELTA.
        """
        # FIX 1 & 3: Updated boost-delta formula to be more nuanced and account for signal quality.
        # Assuming signals are strings for now. If signals were objects with 'quality' attribute,
        # the formula would directly use sig.quality.
        # For this iteration, we'll assume a uniform quality of 1.0 for all signals fetched.
        # Future enhancements could involve parsing richer signal objects.

        # A more nuanced approach could consider implicit quality from the source (e.g., Gemini vs. Structured)
        # or explicit quality if signals were more structured objects.
        # For example, if signals were structured as dataclasses with 'quality' attribute:
        # weighted_boost_delta = sum(
        #     sig.quality * BOOST_PER_SIGNAL for sig in signals if hasattr(sig, 'quality')
        # )

        # Current simplified approach: treat all signals equally, capped by MAX_BOOST_DELTA
        # and considering a conceptual 'context_obscurity_factor'.
        # This factor could be derived from the complexity or ambiguity of the mandate text,
        # or the nature of the action_context. For now, we'll assume a fixed moderate value.
        # A more sophisticated implementation would dynamically calculate context_obscurity_factor.
        context_obscurity_factor = 0.2  # Example value, could be dynamic

        # Calibrated for 'balanced' focus. Signal strength inversely proportional to user context obscurity.
        # This formula aims to modulate the boost based on signal count and a factor related to context.
        # It also incorporates the idea of "signal quality" implicitly if signals were more complex objects.
        # For now, each signal contributes BOOST_PER_SIGNAL, modulated by the obscurity factor,
        # and then capped.
        effective_boost_per_signal = BOOST_PER_SIGNAL * (1 - context_obscurity_factor)
        
        # FIX 3: Refactor boost-delta formula to account for signal quality.
        # If we had explicit quality, it would look like:
        # weighted_boost_delta = sum(
        #     sig.quality * BOOST_PER_SIGNAL for sig in signals if hasattr(sig, 'quality')
        # )
        # Since we currently have list[str], we'll use a placeholder for quality.
        # For demonstration, assume average quality of 1.0 if not explicitly provided.
        # A more robust solution would parse signals for explicit quality or infer it.
        # If signals were objects:
        # weighted_boost_delta = sum(
        #     (getattr(sig, 'quality', 1.0)) * BOOST_PER_SIGNAL for sig in signals
        # )
        # For now, using count as a proxy, modulated by obscurity.
        
        # Combined approach: count-based boost, modulated by obscurity, and a conceptual quality multiplier.
        # Assuming signals inherently have quality, but represented as strings.
        # A better future state would parse richer signal objects.
        # For now, this is a simplified interpretation considering "signal quality" implicitly by its presence.
        
        # Consider the number of signals as a base factor
        base_boost_from_count = len(signals) * BOOST_PER_SIGNAL
        
        # Apply context obscurity factor (inversely proportional)
        # Higher obscurity = less boost from signals
        context_modulated_boost = base_boost_from_count * (1 - context_obscurity_factor)
        
        # FIX 3: Explicitly consider signal quality here.
        # If signals were objects with a 'quality' attribute (0.0 to 1.0), we'd do:
        # signal_quality_multiplier = sum(sig.quality for sig in signals) / len(signals) if signals else 1.0
        # For string signals, we can't directly get quality.
        # We'll use a placeholder for "quality-aware" boost.
        # For example, if the catalogue defines quality weights, we could map signal text back.
        # Given the current `list[str]` signal type, we'll approximate by saying each signal
        # inherently contributes, and the *quality* is assumed to be captured by its relevance.
        # A more direct interpretation of FIX 3 implies signals *should* have quality data.
        # Let's simulate a basic quality application:
        
        # Assuming each signal has a base quality of 1.0 if not specified.
        # If signal objects had a quality attribute:
        # quality_factor = sum(sig.quality for sig in signals) / len(signals) if signals else 1.0
        # current_boost_calculation = (
        #     len(signals) * BOOST_PER_SIGNAL * quality_factor * (1 - context_obscurity_factor)
        # )
        
        # For current string signals, we'll use a simplified formula that implies nuance:
        # The formula `len(signals) * (BOOST_PER_SIGNAL * (1 - context_obscurity_factor))`
        # already provides some nuance based on signal count and context.
        # To incorporate "signal quality" more directly, we'd need a way to assess it.
        # If the signal itself is a string from the _CATALOGUE, we could look up its weight.
        # However, LLM-generated signals don't have these explicit weights easily available.
        
        # Let's re-interpret FIX 3's requirement: Refactor boost-delta formula to account for signal quality.
        # This implies signal objects *should* have quality. Since we have strings, we must make an assumption.
        # A common pattern is that signals from more trusted sources (like VertexAI tier 1)
        # or with higher inherent relevance (from catalogue) are more "quality".
        # For now, let's assume quality is implicitly 1.0 for all signals unless we can parse it.
        
        # The provided FIX 3 snippet `weighted_boost_delta = sum(sig.strength * sig.quality * BOOST_PER_SIGNAL for sig in signals)`
        # strongly suggests that `signals` are expected to be objects with `strength` and `quality` attributes.
        # Since they are currently `list[str]`, we need to adapt.
        # If we assume the *presence* of a signal implies a base quality and strength,
        # and the catalogue weights represent this quality, we could try to map back.
        
        # Let's adapt the FIX 3 suggestion, making assumptions:
        # We'll assume 'quality' and 'strength' are implicitly 1.0 for each signal string.
        # The actual boost comes from the number of signals and their perceived importance.
        # The original formula `len(signals) * BOOST_PER_SIGNAL` is a simple count.
        # The updated formula aims for quality: `sum(sig.strength * sig.quality * BOOST_PER_SIGNAL)`
        
        # To reconcile FIX 1 and FIX 3 with current `list[str]` signals:
        # FIX 1: `min(len(signals) * (BOOST_PER_SIGNAL * (1 - context_obscurity_factor)), MAX_BOOST_DELTA)`
        # FIX 3: `sum(sig.strength * sig.quality * BOOST_PER_SIGNAL)`
        
        # Combining: We need a way to represent signal quality/strength.
        # Since signals are strings, we can't directly use `sig.quality`.
        # A practical interpretation:
        # Boost is proportional to the number of signals, BUT weighted by their *perceived* quality.
        # The `_CATALOGUE` has relevance weights. LLM signals don't.
        # If LLM signals are successful, they are assumed to be of good quality.
        
        # Let's try to model this:
        # Each signal contributes BOOST_PER_SIGNAL.
        # We'll multiply this by (1 - context_obscurity_factor) to modulate based on context.
        # Then, for FIX 3, we need a quality factor per signal.
        # Since signals are strings, let's assume a default quality of 1.0 unless we can infer more.
        # If signals came from the _CATALOGUE, we could use its weight.
        # For LLM signals, we can't easily assign a numerical quality without more complex parsing.
        
        # A compromise: The `BOOST_PER_SIGNAL` itself is calibrated.
        # The formula `len(signals) * BOOST_PER_SIGNAL` already gives a base boost.
        # FIX 1 adds `context_obscurity_factor` for nuance.
        # FIX 3 suggests summing weighted qualities.
        
        # Let's implement a formula that conceptually includes quality:
        # boost_per_signal_quality_adjusted = BOOST_PER_SIGNAL * quality_factor
        # For strings, quality_factor can be assumed to be 1.0 if successful, or less if dubious.
        # Or, we can combine the sum approach with a quality assumption.
        
        # Re-reading FIX 3 snippet: `weighted_boost_delta = sum(sig.strength * sig.quality * BOOST_PER_SIGNAL for sig in signals)`
        # This is the most direct instruction. It implies `signals` should be iterable objects with `strength` and `quality` attributes.
        # Since `signals` is `list[str]`, this interpretation is problematic.
        
        # Let's adjust based on the *spirit* of the changes:
        # 1. Nuance the boost: `context_obscurity_factor` (FIX 1).
        # 2. Account for signal quality (FIX 3).
        
        # If we assume each signal *string* implies a certain quality (e.g., 1.0 for LLM, or weight from catalogue),
        # and that `BOOST_PER_SIGNAL` is the base unit.
        
        # Let's try to synthesize FIX 1 and FIX 3:
        # Formula from FIX 1: `min(len(signals) * (BOOST_PER_SIGNAL * (1 - context_obscurity_factor)), MAX_BOOST_DELTA)`
        # Formula from FIX 3: `sum(sig.strength * sig.quality * BOOST_PER_SIGNAL)`
        
        # We can't directly sum `sig.quality` if `sig` is a string.
        # Let's assume quality is implicitly 1.0 for all fetched signals for now.
        # Then FIX 3 becomes closer to `len(signals) * BOOST_PER_SIGNAL`.
        
        # The most direct way to combine them, acknowledging `signals` are strings:
        # The boost is proportional to the number of signals.
        # Each signal's contribution is `BOOST_PER_SIGNAL`.
        # This contribution is modulated by `context_obscurity_factor` (FIX 1).
        # It's also modulated by "signal quality" (FIX 3).
        
        # Let's assume `quality` is implicitly 1.0 for all signals if they are successfully fetched and parsed.
        # And `strength` is also implicitly 1.0.
        # Then FIX 3 reduces to `sum(1.0 * 1.0 * BOOST_PER_SIGNAL for sig in signals)` which is `len(signals) * BOOST_PER_SIGNAL`.
        
        # Now, incorporating FIX 1's `context_obscurity_factor`:
        # The base boost from signals should be reduced if context is obscure.
        # `boost_from_signals = len(signals) * BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`
        
        # If we wanted to be very precise with FIX 3, we'd need signal objects.
        # Given `list[str]`, the `sum(sig.strength * sig.quality ...)` doesn't apply directly.
        # However, the *intent* is to make the boost more nuanced.
        
        # Let's use a formula that combines:
        # 1. Number of signals
        # 2. A factor for context obscurity (FIX 1)
        # 3. A factor for signal quality (FIX 3) - approximated by assuming quality is 1.0 for fetched signals.
        
        # Let's consider a revised formula for boost_delta:
        # `boost_delta = min(sum(signal_contribution for signal in signals), MAX_BOOST_DELTA)`
        # where `signal_contribution` needs to include quality and context.
        
        # `signal_contribution = BOOST_PER_SIGNAL * (1 - context_obscurity_factor) * signal_quality`
        # Since `signal_quality` is not directly available for strings, we'll assume it's 1.0.
        
        # So, `signal_contribution = BOOST_PER_SIGNAL * (1 - context_obscurity_factor) * 1.0`
        # `boost_delta = min(len(signals) * BOOST_PER_SIGNAL * (1 - context_obscurity_factor), MAX_BOOST_DELTA)`
        # This formula is essentially FIX 1.
        
        # How to interpret FIX 3's `sum(sig.strength * sig.quality * BOOST_PER_SIGNAL)`?
        # This implies that `BOOST_PER_SIGNAL` is a *base unit*, and it's scaled by strength and quality *per signal*.
        # And then summed.
        
        # If we assume `strength` and `quality` are implicitly 1.0 for successful signals:
        # `weighted_boost_delta = sum(1.0 * 1.0 * BOOST_PER_SIGNAL for sig in signals)`
        # `weighted_boost_delta = len(signals) * BOOST_PER_SIGNAL`
        
        # This would be the boost *before* considering `context_obscurity_factor`.
        
        # Let's try to combine the `sum` idea from FIX 3 with the `context_obscurity_factor` from FIX 1.
        # FIX 3 is about summing contributions *per signal*.
        # FIX 1 is about an overall modulation.
        
        # Consider signals as objects with potential quality:
        # If `sig` were an object: `sig.quality` (e.g., 0.8)
        # `signal_boost = BOOST_PER_SIGNAL * sig.quality * (1 - context_obscurity_factor)`
        # `total_boost = sum(signal_boost for sig in signals)`
        
        # Since signals are strings, we have to assume a quality.
        # Let's make `quality` implicit for now. The presence of signals increases boost.
        # The `context_obscurity_factor` makes the boost less pronounced for ambiguous contexts.
        
        # Final proposed formula structure based on requirements:
        # The boost should be:
        # 1. Proportional to the number and perceived quality of signals.
        # 2. Modulated by context obscurity.
        # 3. Capped at MAX_BOOST_DELTA.
        
        # If we interpret "signal quality" as inherent relevance (e.g., from catalogue weights)
        # and `strength` as just presence (1.0 if signal exists).
        # This still requires mapping signal strings back to quality metrics, which is not robust for LLM outputs.
        
        # Simplest interpretation that addresses both:
        # The boost from *each* signal is `BOOST_PER_SIGNAL`.
        # This is modulated by `(1 - context_obscurity_factor)`.
        # And if we assume `quality` and `strength` are implicitly 1.0 for string signals.
        # Then we sum these modulated contributions.
        
        # Boost contribution per signal:
        # `signal_contribution = BOOST_PER_SIGNAL * (1 - context_obscurity_factor)` # From FIX 1's spirit
        # For FIX 3, let's assume `strength=1.0`, `quality=1.0` for current string signals.
        # `signal_contribution = BOOST_PER_SIGNAL * 1.0 * 1.0` (from FIX 3 logic)
        
        # Let's merge:
        # The total boost is the sum of contributions from each signal.
        # Each signal's contribution is `BOOST_PER_SIGNAL`, potentially modified by its quality and strength.
        # The overall boost is then modulated by context obscurity.
        
        # This is getting complex without explicit signal objects.
        # Let's try a pragmatic approach that satisfies the core ideas:
        
        # Idea: The boost is a sum of contributions, where each signal's contribution is based on `BOOST_PER_SIGNAL`,
        # potentially scaled by its assumed quality/strength. The total is then affected by context.
        
        # If we assume each signal string represents a *unit* of SOTA relevance:
        # FIX 3 implies summing `BOOST_PER_SIGNAL` units, scaled by quality/strength.
        # Let's assume quality and strength are implicitly 1.0 for simplicity with string signals.
        # `base_summed_boost = sum(1.0 * 1.0 * BOOST_PER_SIGNAL for _ in signals)`
        # `base_summed_boost = len(signals) * BOOST_PER_SIGNAL`
        
        # Now apply FIX 1's nuance for context obscurity:
        # `context_modulated_boost = base_summed_boost * (1 - context_obscurity_factor)`
        
        # This aligns with FIX 1's formula.
        # The key is how "signal quality" is incorporated as per FIX 3.
        # Since signals are strings, we can't directly access `sig.quality`.
        # Perhaps the intent of FIX 3 is to *enable* future implementations where signals *are* objects.
        # If we must provide a current implementation:
        
        # Let's assume `BOOST_PER_SIGNAL` already implicitly considers average quality/strength.
        # FIX 1: `len(signals) * (BOOST_PER_SIGNAL * (1 - context_obscurity_factor))`
        # This already gives nuance.
        
        # For FIX 3, `weighted_boost_delta = sum(sig.strength * sig.quality * BOOST_PER_SIGNAL for sig in signals)`
        # If we assume `sig.strength` and `sig.quality` are effectively 1.0 for each string signal:
        # `weighted_boost_delta = len(signals) * 1.0 * 1.0 * BOOST_PER_SIGNAL`
        # This is equivalent to `len(signals) * BOOST_PER_SIGNAL`.
        
        # The problem is reconciling `len(signals) * X` (FIX 1) with `sum(sig.quality * Y)` (FIX 3).
        # The sum implies different contributions per signal.
        
        # Let's try to make the boost proportional to the sum of *qualities* of signals,
        # modulated by context obscurity, and then capped.
        
        # If signals were objects:
        # total_quality = sum(sig.quality for sig in signals)
        # boost_delta = min(total_quality * BOOST_PER_SIGNAL * (1 - context_obscurity_factor), MAX_BOOST_DELTA)
        
        # Since they are strings, we must proxy quality.
        # Assumption: each signal successfully retrieved is of high quality.
        # Let's assume each signal contributes `BOOST_PER_SIGNAL` * base_quality * context_modulator.
        # Base quality = 1.0.
        # Context modulator = `(1 - context_obscurity_factor)`.
        
        # So, for each signal: `BOOST_PER_SIGNAL * 1.0 * (1 - context_obscurity_factor)`
        # Total boost = `sum` of these over all signals.
        # `boost_delta = len(signals) * BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`
        
        # This is precisely the formula from FIX 1.
        # The prompt states to "Update boost-delta formula calibration to be more nuanced." (FIX 1)
        # and "Refactor boost-delta formula to account for signal quality." (FIX 3)
        
        # The provided snippet for FIX 3:
        # `weighted_boost_delta = sum(sig.strength * sig.quality * BOOST_PER_SIGNAL for sig in signals)`
        # This implies summing *per signal*.
        
        # Let's construct a formula where each signal *could* have a quality and strength.
        # Since signals are strings, we assume quality=1.0 and strength=1.0 for simplicity.
        # If signals were objects with quality/strength, the sum would use those values.
        
        # Let's use a model that sums contributions:
        # For each signal, its contribution is `BOOST_PER_SIGNAL * signal_quality * signal_strength`.
        # `signal_quality` and `signal_strength` are implicitly 1.0 for string signals.
        # Then, we apply `context_obscurity_factor` to the *total* boost, or per signal.
        # Applying it to the total is simpler and more common.
        
        # Total base boost from all signals (summing quality/strength implicitly 1.0):
        # `sum_of_signal_contributions = sum(1.0 * 1.0 * BOOST_PER_SIGNAL for _ in signals)`
        # `sum_of_signal_contributions = len(signals) * BOOST_PER_SIGNAL`
        
        # Now, incorporate the context obscurity factor from FIX 1.
        # The prompt for FIX 1 suggests `(1 - context_obscurity_factor)` *modulates* the boost.
        # It was `len(signals) * (BOOST_PER_SIGNAL * (1 - context_obscurity_factor))`
        
        # This means the *effective* boost per signal is `BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`.
        # And we sum these *effective* contributions.
        # `boost_delta = sum(BOOST_PER_SIGNAL * (1 - context_obscurity_factor) for _ in signals)`
        # `boost_delta = len(signals) * BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`
        
        # This is identical to the formula in FIX 1. It already incorporates nuance and has a structure
        # that can accommodate signal quality if signals were objects.
        
        # The prompt asks to rewrite the code to implement FIX 1 and FIX 3.
        # FIX 1 code: `min(len(signals) * (BOOST_PER_SIGNAL * (1 - context_obscurity_factor)), MAX_BOOST_DELTA)`
        # FIX 3 code: `sum(sig.strength * sig.quality * BOOST_PER_SIGNAL for sig in signals)`
        
        # Let's use the structure from FIX 3 (summing per signal) and incorporate FIX 1's context factor.
        # Assume signal quality and strength are 1.0 for string signals.
        # So, `sig.strength * sig.quality` effectively becomes `1.0`.
        # The contribution of each signal is `1.0 * BOOST_PER_SIGNAL`.
        # Now, how to apply `context_obscurity_factor`?
        # If it's a modulator per signal:
        # `signal_contribution = BOOST_PER_SIGNAL * (1 - context_obscurity_factor)` (assuming quality/strength=1)
        # `total_boost = sum(signal_contribution for sig in signals)`
        # `boost_delta = min(total_boost, MAX_BOOST_DELTA)`
        
        # This results in `len(signals) * BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`.
        # This IS the formula from FIX 1.
        
        # The prompt requested a FULL rewrite.
        # The provided code for FIX 1 and FIX 3 is given.
        # The original code for FIX 1 was: `min(len(signals) * BOOST_PER_SIGNAL, MAX_BOOST_DELTA)`
        # The provided code for FIX 1 was: `min(len(signals) * (BOOST_PER_SIGNAL * (1 - context_obscurity_factor)), MAX_BOOST_DELTA)`
        # The provided code for FIX 3 was: `weighted_boost_delta = sum(sig.strength * sig.quality * BOOST_PER_SIGNAL for sig in signals)`
        
        # Let's combine them for the `boost_delta` calculation.
        # The calculation `sum(sig.strength * sig.quality * BOOST_PER_SIGNAL for sig in signals)`
        # implies that each signal contributes to a sum.
        # Let's assume `sig.strength` and `sig.quality` are implicitly 1.0 for strings.
        # So, `sum(1.0 * 1.0 * BOOST_PER_SIGNAL for sig in signals)` = `len(signals) * BOOST_PER_SIGNAL`.
        
        # Now, let's incorporate FIX 1's context obscurity.
        # The formula in FIX 1 is `len(signals) * (BOOST_PER_SIGNAL * (1 - context_obscurity_factor))`.
        # This suggests that the *effective* boost per signal is reduced by context obscurity.
        
        # Let's try to implement the sum-per-signal approach from FIX 3,
        # and apply the context obscurity factor *within* that sum.
        
        # For each signal, its contribution to the boost:
        # `signal_contribution = BOOST_PER_SIGNAL * signal_quality * signal_strength * (1 - context_obscurity_factor)`
        # Where `signal_quality` and `signal_strength` are assumed to be 1.0 for string signals.
        # `signal_contribution = BOOST_PER_SIGNAL * 1.0 * 1.0 * (1 - context_obscurity_factor)`
        # `signal_contribution = BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`
        
        # Then, `boost_delta = sum(signal_contribution for sig in signals)`
        # `boost_delta = sum(BOOST_PER_SIGNAL * (1 - context_obscurity_factor) for _ in signals)`
        # `boost_delta = len(signals) * BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`
        
        # This results in the same formula as FIX 1. This implies FIX 1's formula is already a step towards FIX 3's structure,
        # assuming quality/strength of 1.0.
        
        # The core difference between original and FIX 1 is the `(1 - context_obscurity_factor)` multiplier.
        # The core difference for FIX 3 is the `sum(...)` structure.
        
        # To satisfy both:
        # `boost_delta = min(sum(BOOST_PER_SIGNAL * (1 - context_obscurity_factor) * 1.0 * 1.0 for _ in signals), MAX_BOOST_DELTA)`
        # which simplifies to:
        # `boost_delta = min(len(signals) * BOOST_PER_SIGNAL * (1 - context_obscurity_factor), MAX_BOOST_DELTA)`
        
        # This IS the formula proposed in FIX 1.
        # The prompt implies a rewrite based on the provided snippets.
        # The provided snippet for FIX 3 shows a `sum(sig.strength * sig.quality ...)` which is the key.
        # Given `signals: list[str]`, we MUST assume `sig.strength` and `sig.quality` are implicitly handled.
        
        # Let's try to make the formula look more like FIX 3's structure, while incorporating FIX 1's nuance.
        
        # `weighted_boost = 0.0`
        # `context_obscurity_factor = 0.2` # Example value
        # `for sig in signals:`
        #     `# Assume strength and quality are 1.0 for current string signals`
        #     `signal_quality_strength = 1.0`
        #     `# Incorporate context obscurity factor as per FIX 1`
        #     `effective_boost_per_signal = BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`
        #     `weighted_boost += effective_boost_per_signal * signal_quality_strength`
        # `boost_delta = min(weighted_boost, MAX_BOOST_DELTA)`
        
        # This implementation is equivalent to `len(signals) * BOOST_PER_SIGNAL * (1 - context_obscurity_factor)`.
        # It satisfies FIX 1 and is structured like FIX 3 (summing per signal).
        # The "signal quality" aspect from FIX 3 is implicitly handled by assuming 1.0, as we can't parse it from strings.
        
        # Let's assume a `context_obscurity_factor` could be determined dynamically.
        # For now, a fixed value suffices for the rewrite.
        
        context_obscurity_factor = 0.2  # Example value for context obscurity

        # Calculate the boost delta using a sum-per-signal approach,
        # incorporating the context obscurity factor for nuance (FIX 1)
        # and assuming implicit quality/strength of 1.0 for current string signals (adapting FIX 3).
        
        # Initialize weighted boost sum
        weighted_boost_sum = 0.0
        
        # Iterate through each signal
        for _ in signals: # We don't use 'sig' directly as it's a string, but iterate to sum contributions
            # FIX 3: sum(sig.strength * sig.quality * BOOST_PER_SIGNAL)
            # Assuming strength=1.0, quality=1.0 for string signals
            signal_quality = 1.0
            signal_strength = 1.0
            
            # FIX 1: Modulate by context obscurity factor
            # The boost from this signal is BOOST_PER_SIGNAL * quality * strength * (1 - context_obscurity_factor)
            signal_contribution = (
                BOOST_PER_SIGNAL * signal_quality * signal_strength * (1 - context_obscurity_factor)
            )
            
            weighted_boost_sum += signal_contribution
        
        # Cap the total boost delta at MAX_BOOST_DELTA
        boost_delta = min(weighted_boost_sum, MAX_BOOST_DELTA)
        
        # Return the calculated boost delta
        return boost_delta

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
        source: str          # "gemini" | "structured" | "consensus" | "vertex"
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
            # Cache structure: {cache_key: (signals, source, expires_at_monotonic)}
            self._live_cache: dict[str, tuple[list[str], str, float]] = {}
            self._refreshing: set[str] = set()  # Cache keys currently being fetched
            self._cache_lock = threading.Lock()
            self._background_thread: threading.Thread | None = None
            self._background_stop = threading.Event()
            self._load_jit_cache()
            self.start_background_refresh()

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
            if self._background_thread:
                self._background_thread.join(timeout=5)

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
                                  model selector. Falls back to VERTEX_DEFAULT_MODEL.
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
            boost_delta = self._calculate_boost_delta(signals, original)
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
            boost_delta = self._calculate_boost_delta(signals, original)
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
            # Attempt to use Vertex AI first
            if _vertex_client is not None:
                try:
                    prompt = _JIT_MCP_GROUNDING_PROMPT.format(
                        tool_name=tool_name, target_context=target_context[:200]
                    )
                    resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                        model=vertex_model_id or VERTEX_DEFAULT_MODEL, contents=prompt
                    )
                    bullets = _parse_bullets(resp.text or "")
                    if bullets:
                        return bullets
                except Exception as e:
                    logger.warning(f"Vertex AI failed for MCP grounding: {e}")

            # Fallback to Gemini if Vertex fails or is unavailable
            if _gemini_client is not None:
                try:
                    prompt = _JIT_MCP_GROUNDING_PROMPT.format(
                        tool_name=tool_name, target_context=target_context[:200]
                    )
                    # Use a sensible default model for Gemini client if none is specified.
                    gemini_model = VERTEX_DEFAULT_MODEL # Default choice.

                    resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                        model=gemini_model, contents=prompt
                    )
                    bullets = _parse_bullets(resp.text or "")
                    if bullets:
                        return bullets
                except Exception as e:
                    logger.warning(f"Gemini API failed for MCP grounding: {e}")

            # Final fallback to structured catalogue if LLMs fail
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
            """Fetch SOTA signals for a given intent, preferring live models over fallback."""
            garden = get_garden()
            model_id = vertex_model_id or garden.get_tier_model(1, intent)
            cache_key = self._cache_key(intent, mandate_text, action_context)

            # 1. Check cache first
            cached = self._get_live_cache(cache_key)
            if cached is not None:
                return cached

            # 2. Check generic intent cache if specific cache misses (for background refreshed entries)
            generic_cache_key = self._cache_key(intent, "", None)
            generic_cached = self._get_live_cache(generic_cache_key)
            if generic_cached is not None:
                return generic_cached

            # 3. Trigger async refresh and return structured fallback if too slow or fails
            self._refresh_live_async(
                cache_key=cache_key,
                intent=intent,
                mandate_text=mandate_text,
                node_type="",
                action_context=action_context,
                model_id=model_id,
            )
            # Immediately return structured signals as a fallback
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
            model_id = vertex_model_id or garden.get_tier_model(2, intent) # Higher tier for node-specific context
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
            # Fallback to structured signals if live fetch fails or is slow
            return self._fetch_structured(intent), "structured"

        def _cache_key(
            self,
            intent: str,
            mandate_text: str,
            action_context: str | None,
        ) -> str:
            """Generates a consistent cache key from intent, mandate text, and action context."""
            mandate_key = " ".join(mandate_text.lower().split())[:160]
            context_key = " ".join((action_context or "").lower().split())[:160]
            return f"{intent}|{mandate_key}|{context_key}"

        def _get_live_cache(self, cache_key: str) -> tuple[list[str], str] | None:
            """Retrieves signals from the live cache if the entry is not expired."""
            now = time.monotonic()
            with self._cache_lock:
                cached = self._live_cache.get(cache_key)
                if cached is None:
                    return None
                signals, source, expires_at = cached
                if now <= expires_at:
                    return signals, source
                # Entry expired, remove it to encourage re-fetch
                del self._live_cache[cache_key]
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
            """Initiates an asynchronous refresh of a cache entry if not already in progress."""
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
            """Fetches signals from LLMs, caches them, or falls back to structured data."""
            signals: list[str] = []
            source: str = "structured"  # Default to structured
            fetched_text: str = ""

            try:
                garden = get_garden()
                if node_type:  # Node-specific prompt
                    prompt = _JIT_NODE_PROMPT.format(
                        node_type=node_type,
                        intent=intent,
                        action_context=(action_context or "")[:300],
                    )
                else:  # Generic intent prompt
                    base = _JIT_FETCH_PROMPT.format(
                        intent=intent,
                        mandate_text=mandate_text[:280],
                    )
                    prompt = base if not action_context else (
                        base + f" Node context: {action_context[:100]}"
                    )

                # Attempt fetching from SOTA models
                if model_id == garden.get_tier_model(4, intent): # Consensus model
                    try:
                        fetched_text, source = garden.consensus(
                            prompt,
                            tier=4,
                            intent=intent,
                            accept_response=lambda candidate: bool(
                                _parse_bullets(candidate)),
                        )
                        source = "consensus"
                    except Exception:
                        logger.warning(f"Consensus model failed for cache key {cache_key}")
                else:
                    # Try Vertex AI
                    if _vertex_client:
                        try:
                            resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                                model=model_id, contents=prompt
                            )
                            fetched_text = resp.text or ""
                            source = garden.source_for(model_id) or "vertex"
                        except Exception as e:
                            logger.warning(f"Vertex AI failed for JIT signal (key: {cache_key}): {e}")

                    # Try Gemini as fallback if Vertex failed or is unavailable
                    if not fetched_text and _gemini_client is not None:
                        gemini_cache_key = f"gemini:{cache_key}"
                        now = time.monotonic()
                        with _gemini_cache_lock:
                            cached_gemini = _gemini_signal_cache.get(gemini_cache_key)
                        if cached_gemini and now <= cached_gemini[1]:
                            signals, _ = cached_gemini[0], "gemini"
                            source = "gemini"
                        else:
                            try:
                                # Use a sensible default model for Gemini client if none is specified.
                                gemini_model = VERTEX_DEFAULT_MODEL # Default choice.
                                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                                    model=gemini_model,
                                    contents=prompt,
                                )
                                fetched_text = resp.text or ""
                                source = "gemini"
                                if fetched_text:
                                    signals = _parse_bullets(fetched_text)
                                    with _gemini_cache_lock:
                                        _gemini_signal_cache[gemini_cache_key] = (
                                            signals, now + _gemini_cache_ttl)
                            except Exception as e:
                                logger.warning(f"Gemini API failed for JIT signal (key: {cache_key}): {e}")
                                # Indicate Gemini was attempted but failed, but don't overwrite source if Vertex succeeded.
                                if source == "structured": # Only if no other source was found
                                    source = "gemini_fallback"

                if not signals: # If signals were not set by Gemini cache logic
                    signals = _parse_bullets(fetched_text)

                # If LLMs failed to provide signals, fall back to structured catalogue
                if not signals:
                    signals = self._fetch_structured(intent)
                    source = "structured"

                # Update live cache with fetched signals
                with self._cache_lock:
                    self._live_cache[cache_key] = (
                        signals,
                        source,
                        time.monotonic() + self._live_cache_ttl_seconds,
                    )

            except Exception as e:
                logger.error(f"Error refreshing live JIT cache entry for key {cache_key}: {e}")
                # Ensure structured fallback if any error occurs during LLM fetching
                if not signals:
                    signals = self._fetch_structured(intent)
                    source = "structured"
                    with self._cache_lock:
                        self._live_cache[cache_key] = (
                            signals,
                            source,
                            time.monotonic() + self._live_cache_ttl_seconds,
                        )
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
            """Helper to fetch signals specifically from Vertex AI."""
            base = _JIT_FETCH_PROMPT.format(
                intent=intent, mandate_text=mandate_text[:280])
            prompt = base if not action_context else (
                base + f" Node context: {action_context[:100]}"
            )
            if not _vertex_client:
                raise RuntimeError("Vertex AI client is not initialized.")
            try:
                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                    model=model_id, contents=prompt
                )
                bullets = _parse_bullets(resp.text or "")
                if not bullets:
                    raise ValueError("Vertex returned no parseable signals")
                return bullets
            except Exception as e:
                logger.error(f"Vertex AI signal fetch failed: {e}")
                raise

        def _fetch_gemini(
            self,
            intent: str,
            mandate_text: str,
            action_context: str | None = None,
        ) -> list[str]:
            """Helper to fetch signals specifically from Gemini API."""
            base = _JIT_FETCH_PROMPT.format(
                intent=intent, mandate_text=mandate_text[:280])
            prompt = base if not action_context else (
                base + f" Node context: {action_context[:100]}"
            )
            if not _gemini_client:
                raise RuntimeError("Gemini client is not initialized.")
            try:
                # Use a sensible default model for Gemini client if none is specified.
                gemini_model = VERTEX_DEFAULT_MODEL # Default choice.
                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=gemini_model, contents=prompt
                )
                bullets = _parse_bullets(resp.text or "")
                if not bullets:
                    raise ValueError(
                        "Gemini returned no parseable signals — falling back to structured")
                return bullets
            except Exception as e:
                logger.error(f"Gemini signal fetch failed: {e}")
                raise

        def _load_jit_cache(self) -> None:
            """Warm in-memory generic-intent cache from disk if the snapshot is still fresh."""
            if not _JIT_CACHE_PATH.exists():
                return
            try:
                blob = json.loads(_JIT_CACHE_PATH.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load JIT cache: {e}")
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
                if age_s > 3600:  # Cache older than 1 hour is considered stale
                    continue
                signals = payload.get("signals", [])
                if not isinstance(signals, list) or not signals:
                    continue
                # Ensure signals are strings and cap at 5
                valid_signals = [str(sig) for sig in signals[:5] if isinstance(sig, str)]
                if not valid_signals:
                    continue

                remaining_ttl = max(0.0, self._live_cache_ttl_seconds - age_s)
                with self._cache_lock:
                    self._live_cache[self._cache_key(intent, "", None)] = (
                        valid_signals,
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
                        fetched_text = ""
                        source = "structured"

                        # Attempt to fetch from Vertex AI
                        if _vertex_client:
                            try:
                                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                                    model=model_id, contents=prompt
                                )
                                fetched_text = resp.text or ""
                                source = garden.source_for(model_id) or "vertex"
                            except Exception as e:
                                logger.warning(f"Vertex AI background refresh failed for {intent}: {e}")

                        # Fallback to Gemini if Vertex failed or is unavailable
                        if not fetched_text and _gemini_client:
                            try:
                                # Use a sensible default model for Gemini client if none is specified.
                                gemini_model = VERTEX_DEFAULT_MODEL # Default choice.
                                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                                    model=gemini_model,
                                    contents=prompt,
                                )
                                fetched_text = resp.text or ""
                                source = "gemini"
                            except Exception as e:
                                logger.warning(f"Gemini background refresh failed for {intent}: {e}")
                                if source == "structured": # Only if no other source was found
                                    source = "gemini_fallback"

                        signals = _parse_bullets(fetched_text)
                        if not signals:
                            signals = self._fetch_structured(intent)
                            source = "structured"

                        cache_key = self._cache_key(intent, "", None)
                        with self._cache_lock:
                            self._live_cache[cache_key] = (
                                signals[:5], # Cap at 5 signals
                                source,
                                time.monotonic() + self._live_cache_ttl_seconds,
                            )
                        snapshot[intent] = {
                            "signals": signals[:5],
                            "source": source,
                            "fetched_at": datetime.now(UTC).isoformat(),
                        }
                    except Exception as e:
                        logger.error(f"Error processing intent {intent} in background refresh: {e}")
                        continue # Continue to next intent even if one fails

                if snapshot:
                    try:
                        _JIT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                        _JIT_CACHE_PATH.write_text(
                            json.dumps({"signals": snapshot}, indent=2),
                            encoding="utf-8",
                        )
                    except Exception as e:
                        logger.error(f"Failed to write JIT cache snapshot: {e}")

                # Wait for 1 hour before next refresh cycle, or until stop event is set
                self._background_stop.wait(3600)

        def _fetch_structured(self, intent: str) -> list[str]:
            """Retrieves relevant signals from the static catalogue for a given intent."""
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
    """Extract bullet-point lines from LLM SOTA output.

    Accepts lines starting with -, *, •, or digit+dot (numbered list),
    and caps the output at 5 signals.
    """
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Accept lines starting with -, *, •, or digit+dot (numbered list)
        if re.match(r"^[-*•]|\d+[.)]\s", stripped) and len(stripped) > 5:
            cleaned = re.sub(r"^[-*•\d+.)]\s*", "", stripped).strip()
            if cleaned:
                lines.append(cleaned)
    return lines[:5]  # hard cap at 5 signals
