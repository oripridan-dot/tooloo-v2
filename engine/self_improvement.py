"""
engine/self_improvement.py — TooLoo V2 self-improvement loop.

The system applies its own pipeline capabilities to itself:

  1. Enumerate engine micro-components as DAG nodes
  2. For each component, generate a domain-appropriate improvement mandate
  3. Route each mandate → JIT SOTA boost → Tribunal scan → Scope evaluate
     → Fan-out execute → Refinement report
  4. Harvest JIT SOTA signals as concrete improvement directives per component
  5. Produce a SelfImprovementReport with verdicts and top recommendations

Wave plan (3 waves, varying parallelism):
    Wave 1 [core-security]  : router · tribunal · psyche_bank           (x3 parallel)
    Wave 2 [performance]    : jit_booster · executor · graph            (x3 parallel)
    Wave 3 [meta-analysis]  : scope_evaluator · refinement              (x2 parallel)

Scope: 8 nodes · 3 waves · max x3 parallel · strategy: deep-parallel
Risk:  router (circuit-breaker state), tribunal (OWASP patterns must not trigger
       on self-audit mandates — uses benign audit-only text)
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from engine.config import GEMINI_API_KEY, GEMINI_MODEL, VERTEX_DEFAULT_MODEL
from engine.config import _vertex_client as _vertex_client_cfg
from engine.executor import Envelope, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBooster
from engine.mcp_manager import MCPManager
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.router import MandateRouter
from engine.scope_evaluator import ScopeEvaluator
from engine.tribunal import Engram, Tribunal

if TYPE_CHECKING:
    from engine.jit_booster import JITBoostResult
    from engine.router import RouteResult

# ── LLM clients (initialised once — same pattern as jit_booster / conversation) ──
_vertex_client = _vertex_client_cfg

_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        _gemini_client = _genai_mod.Client(api_key=GEMINI_API_KEY)
    except Exception:  # pragma: no cover
        pass

# ── Workspace root ────────────────────────────────────────────────────────────
_REPO_ROOT: Path = Path(__file__).resolve().parents[1]

# ── Map component name → source file relative to repo root ────────────────────
_COMPONENT_SOURCE: dict[str, str] = {
    "router":           "engine/router.py",
    "tribunal":         "engine/tribunal.py",
    "psyche_bank":      "engine/psyche_bank.py",
    "jit_booster":      "engine/jit_booster.py",
    "executor":         "engine/executor.py",
    "graph":            "engine/graph.py",
    "scope_evaluator":  "engine/scope_evaluator.py",
    "refinement":       "engine/refinement.py",
    "n_stroke":         "engine/n_stroke.py",
    "supervisor":       "engine/supervisor.py",
    "conversation":     "engine/conversation.py",
    "config":           "engine/config.py",
    # Wave 6 — advanced execution layer
    "branch_executor":  "engine/branch_executor.py",
    "mandate_executor": "engine/mandate_executor.py",
    "model_garden":     "engine/model_garden.py",
    "vector_store":     "engine/vector_store.py",
    "daemon":           "engine/daemon.py",
}

_FOCUS_ALIASES: dict[str, str] = {
    "balanced": "balanced",
    "efficiency": "efficiency",
    "quality": "quality",
    "accuracy": "accuracy",
    "speed": "speed",
    "latency": "speed",
    "performance": "speed",
    "robustness": "quality",
    "determinism": "accuracy",
}

_ANALYSIS_PROMPT = (
    "You are TooLoo V2's self-improvement analyst.  Your job is to audit a specific "
    "engine component and produce CONCRETE, ACTIONABLE code-level improvements.\n\n"
    "Component: {component}\n"
    "Role: {description}\n"
    "Improvement mandate: {mandate}\n\n"
    "SOTA signals (current 2026 best practices):\n{signals}\n\n"
    "Source code (first {max_lines} lines):\n```python\n{source}\n```\n\n"
    "Produce exactly 3 concrete improvements. For each, output:\n"
    "  FIX <N>: <file_path>:<line_hint> — <what to change> (1 line)\n"
    "  CODE: <the exact replacement code snippet (≤8 lines)>\n\n"
    "Be terse, specific, and production-ready. Follow TooLoo V2 laws: "
    "stateless processors, no hardcoded secrets, all config from engine/config.py."
)

# ── Component manifest ────────────────────────────────────────────────────────
#
# Each entry describes one engine micro-component:
#   component   — module/class name
#   description — one-line role
#   mandate     — the improvement mandate text routed through the full pipeline
#   wave        — 1-indexed wave assignment for the 3-wave DAG
#   deps        — component names that must complete before this one starts
#
_COMPONENTS: list[dict[str, Any]] = [
    # ── Wave 1: core security ─────────────────────────────────────────────────
    {
        "component": "router",
        "description": "Intent classification + circuit breaker",
        "mandate": (
            "audit and improve the MandateRouter keyword classifier: review intent "
            "coverage, check circuit-breaker threshold calibration, validate "
            "confidence-band boundaries for BUILD DEBUG AUDIT DESIGN EXPLAIN IDEATE"
        ),
        "wave": 1,
        "deps": [],
    },
    {
        "component": "tribunal",
        "description": "OWASP poison detection + healer",
        "mandate": (
            "audit and improve the Tribunal OWASP poison-detection patterns: review "
            "coverage of injection, secrets, and dynamic-eval vectors, recommend "
            "additional security rules aligned with OWASP Top 10 2025"
        ),
        "wave": 1,
        "deps": [],
    },
    {
        "component": "psyche_bank",
        "description": "Cognitive .cog.json rule store",
        "mandate": (
            "audit and improve the PsycheBank rule store: review deduplication "
            "strategy, recommend TTL expiry for auto-captured rules, validate that "
            "rule IDs and categories conform to security governance standards"
        ),
        "wave": 1,
        "deps": [],
    },
    # ── Wave 2: performance ───────────────────────────────────────────────────
    {
        "component": "jit_booster",
        "description": "SOTA confidence booster",
        "mandate": (
            "audit and improve the JITBooster SOTA signal catalogue: update signal "
            "entries with 2026 patterns, review boost-delta formula calibration, "
            "recommend caching strategy for live Gemini signal responses"
        ),
        "wave": 2,
        "deps": ["router"],
    },
    {
        "component": "executor",
        "description": "JIT parallel fan-out executor",
        "mandate": (
            "implement and improve execution observability in JITExecutor: add "
            "latency histogram collection, review ThreadPoolExecutor sizing strategy, "
            "recommend adaptive worker-count tuning based on wave width"
        ),
        "wave": 2,
        "deps": ["router"],
    },
    {
        "component": "graph",
        "description": "CognitiveGraph + TopologicalSorter + DAG",
        "mandate": (
            "build and improve the CognitiveGraph DAG engine: validate acyclicity "
            "enforcement under concurrent writes, review provenance chain depth "
            "limits, recommend cycle-recovery strategies for IDEATE mandates"
        ),
        "wave": 2,
        "deps": ["router"],
    },
    # ── Wave 3: meta-analysis ─────────────────────────────────────────────────
    {
        "component": "scope_evaluator",
        "description": "Pre-execution wave-plan analyser",
        "mandate": (
            "implement advanced risk-surface scoring in ScopeEvaluator: review "
            "parallelism ratio thresholds, improve strategy classification for "
            "single-node plans, recommend dynamic thread allocation models"
        ),
        "wave": 3,
        "deps": ["executor", "graph"],
    },
    {
        "component": "refinement",
        "description": "Post-execution evaluate-and-refine loop",
        "mandate": (
            "build and improve adaptive threshold tuning in RefinementLoop: review "
            "WARN and FAIL success-rate boundaries, recommend histogram-based p90 "
            "slow-node detection, improve rerun recommendation criteria"
        ),
        "wave": 3,
        "deps": ["executor", "graph"],
    },
    # ── Wave 4: orchestration ─────────────────────────────────────────────────
    {
        "component": "n_stroke",
        "description": "N-Stroke Autonomous Cognitive Loop engine",
        "mandate": (
            "build and improve the NStrokeEngine loop: review satisfaction-gate "
            "thresholds, validate SimulationGate completeness and security checks, "
            "recommend adaptive MAX_STROKES tuning based on mandate complexity, "
            "improve SSE broadcast payload richness for observability"
        ),
        "wave": 4,
        "deps": ["scope_evaluator", "refinement"],
    },
    {
        "component": "supervisor",
        "description": "TwoStrokeEngine sub-pipeline",
        "mandate": (
            "audit and improve the TwoStrokeEngine supervisor: review preflight and "
            "midflight supervisor sequencing, validate Tribunal integration between "
            "strokes, recommend pipeline shortcut conditions for low-complexity "
            "mandates to reduce unnecessary strokes"
        ),
        "wave": 4,
        "deps": ["scope_evaluator", "refinement"],
    },
    # ── Wave 5: intelligence layer ────────────────────────────────────────────
    {
        "component": "conversation",
        "description": "Multi-turn ConversationEngine with confidence tiers",
        "mandate": (
            "build and improve the ConversationEngine: review three-tier confidence "
            "handling boundaries (clarification / hedge / confident), improve JIT "
            "signal surfacing in responses, recommend context-window management "
            "strategies for long multi-turn sessions, validate OWASP input checks"
        ),
        "wave": 5,
        "deps": ["n_stroke", "supervisor"],
    },
    {
        "component": "config",
        "description": "Single source of truth config loader",
        "mandate": (
            "audit and improve engine/config.py: validate all env-var fallbacks "
            "are safe defaults, review CIRCUIT_BREAKER_THRESHOLD and MAX_STROKES "
            "constants for 2026 SOTA calibration, recommend typed-config dataclass "
            "pattern to eliminate ad-hoc os.getenv() calls across engine modules"
        ),
        "wave": 5,
        "deps": ["n_stroke", "supervisor"],
    },
    # ── Wave 6: advanced execution layer ─────────────────────────────────────
    {
        "component": "branch_executor",
        "description": "FORK/CLONE/SHARE async branch pipeline engine",
        "mandate": (
            "audit and improve BranchExecutor: review FORK/SHARE branch isolation "
            "guarantees, validate SharedBlackboard read-only contract under concurrent "
            "writes, recommend mitosis depth limits to prevent runaway branching, "
            "improve asyncio.TaskGroup migration from gather() pattern"
        ),
        "wave": 6,
        "deps": ["n_stroke", "conversation"],
    },
    {
        "component": "mandate_executor",
        "description": "LLM-powered DAG node executor (live work function factory)",
        "mandate": (
            "build and improve MandateExecutor: review make_live_work_fn closure "
            "safety for ThreadPoolExecutor fan-out, validate node-type prompt "
            "templates cover all 8 node types, recommend streaming output support "
            "for long-running implement nodes, audit spawn_process tool output handling"
        ),
        "wave": 6,
        "deps": ["n_stroke", "conversation"],
    },
    {
        "component": "model_garden",
        "description": "Multi-provider Model Garden — tier-based model selector",
        "mandate": (
            "audit and improve ModelGarden: review 4-tier capability scoring matrix "
            "for 2026 model landscape accuracy, validate consensus() parallel "
            "execution under ThreadPoolExecutor, recommend dynamic tier re-scoring "
            "based on observed latency histograms, audit cross-provider error handling"
        ),
        "wave": 6,
        "deps": ["config", "jit_booster"],
    },
    {
        "component": "vector_store",
        "description": "In-process TF-IDF vector store with cosine similarity",
        "mandate": (
            "implement and improve VectorStore: review TF-IDF incremental IDF "
            "recomputation correctness, recommend approximate nearest-neighbour "
            "upgrade path (HNSW/Annoy) for corpora >10k docs, validate thread-safety "
            "of add/search under concurrent access, audit near-duplicate threshold calibration"
        ),
        "wave": 6,
        "deps": ["config", "psyche_bank"],
    },
    {
        "component": "daemon",
        "description": "Background ROI scoring + autonomous proposal daemon",
        "mandate": (
            "audit and improve BackgroundDaemon: review asyncio event-loop isolation "
            "from FastAPI lifespan, validate proposal scorer fallback when Gemini is "
            "unavailable, recommend structured healthcheck endpoint for daemon status, "
            "audit high-risk component approval gating (Law 20 invariants)"
        ),
        "wave": 6,
        "deps": ["config", "psyche_bank"],
    },
]


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class ComponentAssessment:
    """Pipeline assessment for one engine micro-component."""

    component: str
    description: str
    intent: str
    original_confidence: float
    boosted_confidence: float
    jit_signals: list[str]
    jit_source: str
    tribunal_passed: bool
    scope_summary: str
    execution_success: bool
    execution_latency_ms: float
    suggestions: list[str]
    # Value scoring — quantifies the expected business/engineering impact of applying
    # the suggestions in this assessment.  Range 0.0-1.0.  Computed by
    # SelfImprovementEngine._score_improvement_value().
    value_score: float = 0.0
    value_rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "description": self.description,
            "intent": self.intent,
            "original_confidence": round(self.original_confidence, 3),
            "boosted_confidence": round(self.boosted_confidence, 3),
            "jit_signals": self.jit_signals,
            "jit_source": self.jit_source,
            "tribunal_passed": self.tribunal_passed,
            "scope_summary": self.scope_summary,
            "execution_success": self.execution_success,
            "execution_latency_ms": round(self.execution_latency_ms, 2),
            "suggestions": self.suggestions,
            "value_score": round(self.value_score, 3),
            "value_rationale": self.value_rationale,
        }


@dataclass
class SelfImprovementReport:
    """Immutable snapshot of one self-improvement cycle."""

    improvement_id: str
    ts: str
    components_assessed: int
    waves_executed: int
    total_signals: int
    assessments: list[ComponentAssessment]
    top_recommendations: list[str]
    refinement_verdict: str        # "pass" | "warn" | "fail"
    refinement_success_rate: float
    latency_ms: float
    # Ouroboros God Mode additions
    arch_diagram: str = ""         # Mermaid diagram of engine component graph
    regression_passed: bool = True  # True if run_tests MCP passed post-cycle
    regression_details: str = ""   # test summary from MCPManager.run_tests

    def to_dict(self) -> dict[str, Any]:
        return {
            "improvement_id": self.improvement_id,
            "ts": self.ts,
            "components_assessed": self.components_assessed,
            "waves_executed": self.waves_executed,
            "total_signals": self.total_signals,
            "assessments": [a.to_dict() for a in self.assessments],
            "top_recommendations": self.top_recommendations,
            "refinement_verdict": self.refinement_verdict,
            "refinement_success_rate": round(self.refinement_success_rate, 3),
            "latency_ms": round(self.latency_ms, 2),
            "arch_diagram": self.arch_diagram,
            "regression_passed": self.regression_passed,
            "regression_details": self.regression_details,
        }


# ── Engine ────────────────────────────────────────────────────────────────────


class SelfImprovementEngine:
    """Run the full pipeline against each engine component to surface improvement
    opportunities.

    Ouroboros God Mode:
      Before any self-assessment, the engine generates an architectural diagram
      (Mermaid) of the component dependency graph.  After the assessment cycle,
      it runs the full test suite via MCPManager.run_tests and gates the final
      verdict on the regression result.  This ensures self-modifications never
      silently break the existing pipeline.

    Uses a *dedicated* MandateRouter in ``route_chat`` mode so the self-improvement
    cycle never trips the shared circuit-breaker used by the Governor API.

    Usage::

        engine = SelfImprovementEngine()
        report = engine.run()
    """

    # Suggestions derived from verdicts — extracted from refinement recommendations
    _WAVE_LABELS: MappingProxyType = MappingProxyType(
        {1: "core-security", 2: "performance", 3: "meta-analysis",
         4: "orchestration", 5: "intelligence-layer",
         6: "advanced-execution"})

    def __init__(
        self,
        booster: JITBooster | None = None,
        bank: PsycheBank | None = None,
        optimization_focus: str = "balanced",
    ) -> None:
        # Isolated router — never touches the shared circuit-breaker
        self._router = MandateRouter()
        self._booster = booster or JITBooster()
        self._bank = bank or PsycheBank()
        self._tribunal = Tribunal(bank=self._bank)
        self._executor = JITExecutor(max_workers=6)
        self._sorter = TopologicalSorter()
        self._scope_evaluator = ScopeEvaluator()
        self._refinement_loop = RefinementLoop()
        self._mcp = MCPManager()
        # LLM model — re-uses same default as config
        self._vertex_model: str = VERTEX_DEFAULT_MODEL
        self._optimization_focus = self._normalise_focus(optimization_focus)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        optimization_focus: str | None = None,
        run_regression_gate: bool = True,
    ) -> SelfImprovementReport:
        """Execute the Ouroboros self-improvement cycle.

        Phases:
          Phase 0 — Architectural Diagram generation (Mermaid component graph)
          Phase 1 — Component assessment waves (existing 3-wave structure)
          Phase 2 — Regression Gate via MCPManager.run_tests (sandbox)
        """
        t0 = time.monotonic()
        improvement_id = f"si-{uuid.uuid4().hex[:8]}"
        if optimization_focus is not None:
            self._optimization_focus = self._normalise_focus(optimization_focus)

        # ── Phase 0: Generate architectural diagram ───────────────────────────
        arch_diagram = self._generate_arch_diagram()

        # ── Phase 1: Component assessment waves ──────────────────────────────
        wave_spec = self._build_wave_spec()
        waves = self._sorter.sort(wave_spec)

        assessments: list[ComponentAssessment] = []
        component_id_map = {
            c["component"]: f"{improvement_id}-{c['component']}"
            for c in _COMPONENTS
        }
        envelopes = [
            Envelope(
                mandate_id=component_id_map[c["component"]],
                intent="AUDIT",
                domain="self-improvement",
                metadata={"component": c},
            )
            for c in _COMPONENTS
        ]
        dependency_map = {
            component_id_map[c["component"]]: [
                component_id_map[d] for d in c["deps"]]
            for c in _COMPONENTS
        }

        all_results = self._executor.fan_out_dag(
            self._assess_component,
            envelopes,
            dependency_map,
            max_workers=max(3, len(waves)),
        )

        for result in all_results:
            if result.success and isinstance(result.output, ComponentAssessment):
                result.output.execution_latency_ms = result.latency_ms
                assessments.append(result.output)
            else:
                comp = next(
                    c for c in _COMPONENTS
                    if component_id_map[c["component"]] == result.mandate_id
                )
                assessments.append(ComponentAssessment(
                    component=comp["component"],
                    description=comp["description"],
                    intent="AUDIT",
                    original_confidence=0.0,
                    boosted_confidence=0.0,
                    jit_signals=[],
                    jit_source="none",
                    tribunal_passed=False,
                    scope_summary="assessment failed",
                    execution_success=False,
                    execution_latency_ms=result.latency_ms,
                    suggestions=[
                        "Re-run self-improvement cycle to retry this component."],
                    value_rationale=f"focus={self._optimization_focus}; assessment failed",
                ))

        # ── Phase 2: Regression Gate ─────────────────────────────────────────
        if run_regression_gate:
            regression_passed, regression_details = self._run_regression_gate(
                improvement_id
            )
        else:
            regression_passed, regression_details = True, "skipped by caller"

        # Build refinement envelopes representing the component assessments
        from engine.executor import ExecutionResult
        refinement_inputs = [
            ExecutionResult(
                mandate_id=f"{improvement_id}-{a.component}",
                success=a.execution_success,
                output=a.component,
                latency_ms=a.execution_latency_ms,
            )
            for a in assessments
        ]
        refinement = self._refinement_loop.evaluate(refinement_inputs)

        top_recs = self._top_recommendations(
            assessments, refinement.recommendations)
        total_signals = sum(len(a.jit_signals) for a in assessments)

        return SelfImprovementReport(
            improvement_id=improvement_id,
            ts=datetime.now(UTC).isoformat(),
            components_assessed=len(assessments),
            waves_executed=len(waves),
            total_signals=total_signals,
            assessments=assessments,
            top_recommendations=top_recs,
            refinement_verdict=refinement.verdict,
            refinement_success_rate=refinement.success_rate,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            arch_diagram=arch_diagram,
            regression_passed=regression_passed,
            regression_details=regression_details,
        )

    # ── Ouroboros God Mode helpers ────────────────────────────────────────────

    def _generate_arch_diagram(self) -> str:
        """Generate a Mermaid graph diagram of the engine component dependencies.

        Attempts Vertex AI first; falls back to a static structural diagram.
        The diagram is written to plans/arch_diagram.md in the workspace.
        """
        prompt = (
            "Generate a Mermaid graph LR diagram showing the TooLoo V2 engine "
            "component dependencies for these components and their deps:\n"
            + "\n".join(
                f"  {c['component']} --> deps: {c['deps']}"
                for c in _COMPONENTS
            )
            + "\n\nOutput ONLY the Mermaid code block. No prose. Start with ```mermaid"
        )
        diagram = ""
        if _vertex_client is not None:
            try:
                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                    model=self._vertex_model, contents=prompt
                )
                diagram = (resp.text or "").strip()
            except Exception:
                pass
        if not diagram and _gemini_client is not None:
            try:
                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=GEMINI_MODEL, contents=prompt
                )
                diagram = (resp.text or "").strip()
            except Exception:
                pass
        if not diagram:
            # Static fallback diagram
            diagram = self._static_arch_diagram()

        # Write to plans/ directory (non-live, planning-phase write)
        self._write_plan("arch_diagram.md",
                         f"# TooLoo V2 Architecture\n\n{diagram}\n")
        return diagram

    def _run_regression_gate(
        self, improvement_id: str
    ) -> tuple[bool, str]:
        """Run the test suite via MCPManager.run_tests after the assessment cycle.

        Returns (passed: bool, details: str).  Runs in sandbox mode — does not
        block the report if tests fail, but surfaces the failure prominently.

        Skipped when executing inside an existing pytest session (PYTEST_CURRENT_TEST
        is set) to avoid spawning a recursive subprocess that will time-out.
        """
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return True, "skipped (running inside pytest)"
        result = self._mcp.call_uri("mcp://tooloo/run_tests",
                                    test_path="tests", timeout=45)
        details = str(result.output or "")[:500]
        passed = result.success
        return passed, details

    def _write_plan(self, filename: str, content: str) -> None:
        """Write a planning-phase artefact to the workspace plans/ directory.

        Uses the MCP file_write tool with a path-safety check.
        Falls back silently if write fails (non-blocking).
        """
        with suppress(Exception):
            self._mcp.call_uri("mcp://tooloo/file_write",
                               path=f"plans/{filename}", content=content)

    @staticmethod
    def _static_arch_diagram() -> str:
        """Static Mermaid architecture diagram for offline mode."""
        return (
            "```mermaid\n"
            "graph LR\n"
            "  router --> tribunal\n"
            "  router --> jit_booster\n"
            "  router --> psyche_bank\n"
            "  jit_booster --> executor\n"
            "  jit_booster --> graph\n"
            "  executor --> scope_evaluator\n"
            "  executor --> refinement\n"
            "  graph --> scope_evaluator\n"
            "  graph --> refinement\n"
            "  tribunal --> psyche_bank\n"
            "```"
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_wave_spec(self) -> list[tuple[str, list[str]]]:
        """Convert the component manifest into a TopologicalSorter-compatible spec."""
        return [
            (c["component"], c["deps"])
            for c in _COMPONENTS
        ]

    def _assess_component(self, env: Envelope) -> ComponentAssessment:
        """Full pipeline assessment for one component (runs inside a thread).

        Pipeline:
          1. Route   — isolated MandateRouter (no circuit-breaker side-effects)
          2. JIT     — Vertex AI SOTA signal fetch (primary) / structured (fallback)
          3. Tribunal — OWASP poison scan
          4. Plan    — micro 3-wave DAG (recon → analyse → improve)
          5. Scope   — wave-plan analysis
          6. Analyse — read source file + Vertex AI code-level analysis (live)
          7. Return  — ComponentAssessment with concrete LLM-generated suggestions
        """
        comp: dict[str, Any] = env.metadata["component"]
        mandate_text: str = comp["mandate"]
        component_name: str = comp["component"]

        # 1. Route through isolated router (chat mode — no CB side-effects)
        route: RouteResult = self._router.route_chat(mandate_text)

        # 2. Mandatory JIT SOTA boost
        jit_result: JITBoostResult = self._booster.fetch(
            route,
            action_context=self._focus_action_context(component_name),
        )
        self._router.apply_jit_boost(route, jit_result.boosted_confidence)

        # 3. Tribunal scan (mandate text is safe — no OWASP patterns)
        engram = Engram(
            slug=env.mandate_id,
            intent=route.intent,
            logic_body=mandate_text,
            domain="self-improvement",
            mandate_level="L1",
        )
        tribunal_result = self._tribunal.evaluate(engram)

        # 4. Micro-wave plan for this component (recon → analyse → improve)
        micro_spec: list[tuple[str, list[str]]] = [
            (f"{env.mandate_id}-recon", []),
            (f"{env.mandate_id}-analyse", [f"{env.mandate_id}-recon"]),
            (f"{env.mandate_id}-improve", [f"{env.mandate_id}-analyse"]),
        ]
        micro_waves = self._sorter.sort(micro_spec)

        # 5. Scope evaluation for the component's micro-plan
        scope = self._scope_evaluator.evaluate(
            micro_waves, intent=route.intent)

        # 6. LLM deep analysis — read source + call Vertex AI for concrete suggestions
        source_snippet = self._read_component_source(component_name)
        if source_snippet:
            suggestions = self._analyze_with_llm(
                component=component_name,
                description=comp["description"],
                mandate=(
                    f"Focus: {self._optimization_focus}. "
                    f"Prioritise efficiency, quality, accuracy, and speed.\n\n"
                    f"{mandate_text}"
                ),
                signals=jit_result.signals,
                source=source_snippet,
            )
        else:
            suggestions = self._derive_suggestions(
                component_name, jit_result.signals)

        value_score, value_rationale = self._score_improvement_value(
            component=component_name,
            suggestions=suggestions,
            jit_signals=jit_result.signals,
            confidence_delta=jit_result.boosted_confidence - jit_result.original_confidence,
            tribunal_passed=tribunal_result.passed,
            optimization_focus=self._optimization_focus,
        )

        return ComponentAssessment(
            component=component_name,
            description=comp["description"],
            intent=route.intent,
            original_confidence=jit_result.original_confidence,
            boosted_confidence=jit_result.boosted_confidence,
            jit_signals=jit_result.signals,
            jit_source=jit_result.source,
            tribunal_passed=tribunal_result.passed,
            scope_summary=scope.scope_summary,
            execution_success=tribunal_result.passed,
            execution_latency_ms=0.0,  # filled by JITExecutor wrapper
            suggestions=suggestions,
            value_score=value_score,
            value_rationale=value_rationale,
        )

    def _read_component_source(self, component: str, max_lines: int = 120) -> str:
        """Read the first ``max_lines`` of the component's source file.

        Returns empty string if the file is not found or cannot be read.
        Path traversal is prevented by resolving against _REPO_ROOT.
        """
        rel_path = _COMPONENT_SOURCE.get(component)
        if not rel_path:
            return ""
        abs_path = (_REPO_ROOT / rel_path).resolve()
        # Jail check — must stay inside the repo root (no ../ traversal)
        if not str(abs_path).startswith(str(_REPO_ROOT)):
            return ""
        try:
            lines = abs_path.read_text(encoding="utf-8").splitlines()
            return "\n".join(lines[:max_lines])
        except OSError:
            return ""

    def _analyze_with_llm(
        self,
        component: str,
        description: str,
        mandate: str,
        signals: list[str],
        source: str,
        max_lines: int = 120,
    ) -> list[str]:
        """Call Vertex AI (primary) / Gemini Direct (fallback) with the component
        source code to produce concrete code-level improvement suggestions.

        Falls back to ``_derive_suggestions`` when both LLM paths are unavailable.
        All output is treated as untrusted text — not eval'd, not exec'd.
        """
        signals_str = "\n".join(
            f"- {s}" for s in signals[:3]) if signals else "(none)"
        prompt = _ANALYSIS_PROMPT.format(
            component=component,
            description=description,
            mandate=mandate[:400],
            signals=signals_str,
            max_lines=max_lines,
            source=source[:3000],  # hard cap to stay within token limits
        )

        # Fast-path: skip live LLM calls in offline mode (no TOOLOO_LIVE_TESTS).
        # This keeps the offline cycle under 10 s instead of hitting the API.
        import os as _os
        _live = _os.environ.get("TOOLOO_LIVE_TESTS",
                                "").lower() in ("1", "true", "yes")
        if not _live:
            return self._derive_suggestions(component, signals)

        raw: str = ""
        if _vertex_client is not None:
            try:
                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                    model=self._vertex_model, contents=prompt,
                )
                raw = (resp.text or "").strip()
            except Exception:
                pass

        if not raw and _gemini_client is not None:
            try:
                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=GEMINI_MODEL, contents=prompt,
                )
                raw = (resp.text or "").strip()
            except Exception:
                pass

        if not raw:
            return self._derive_suggestions(component, signals)

        # Parse LLM output into paired FIX+CODE suggestion blocks.
        # Each returned string is a complete unit: "FIX N: file:line — desc\nCODE:\n<snippet>"
        # so the daemon can extract the file path, line hint, and code in one piece.
        lines = raw.splitlines()
        pairs: list[str] = []
        current_fix: str | None = None
        current_code_lines: list[str] = []
        in_fence = False
        in_code_section = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                if in_code_section and current_fix is not None:
                    current_code_lines.append(line)
                continue
            if stripped.upper().startswith("FIX "):
                # Commit previous pair before starting a new one
                if current_fix is not None:
                    pairs.append(
                        current_fix + "\nCODE:\n" +
                        "\n".join(current_code_lines)
                    )
                current_fix = stripped
                current_code_lines = []
                in_code_section = False
            elif stripped.startswith("CODE:") and current_fix is not None:
                in_code_section = True
                rest = stripped[5:].strip()
                if rest:
                    current_code_lines.append(rest)
            elif in_code_section and current_fix is not None:
                current_code_lines.append(line)  # preserve indentation

        if current_fix is not None:
            pairs.append(current_fix + "\nCODE:\n" +
                         "\n".join(current_code_lines))

        if pairs:
            return pairs[:3]

        # Fall back to first 3 non-empty, non-preamble lines when Gemini
        # didn't follow the FIX/CODE format.
        fallback: list[str] = []
        for line in lines:
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith(("```", "Here", "Below", "Sure",
                                             "Certainly", "Of course", "#"))
                and len(stripped) > 20
            ):
                fallback.append(stripped)
                if len(fallback) >= 3:
                    break
        return fallback if fallback else self._derive_suggestions(component, signals)

    @staticmethod
    def _derive_suggestions(
        component: str,
        signals: list[str],
    ) -> list[str]:
        """Derive actionable improvement suggestions from JIT SOTA signals."""
        if not signals:
            return [f"No JIT signals available — re-run with live Gemini for {component}."]

        # Prefix each signal with an action verb appropriate to the component
        action_prefix = {
            "router": "Calibrate",
            "tribunal": "Extend",
            "psyche_bank": "Enforce",
            "jit_booster": "Refresh",
            "executor": "Instrument",
            "graph": "Harden",
            "scope_evaluator": "Tune",
            "refinement": "Adjust",
            "n_stroke": "Optimise",
            "supervisor": "Streamline",
            "conversation": "Enhance",
            "config": "Validate",
        }.get(component, "Apply")

        return [f"{action_prefix}: {s}" for s in signals[:3]]

    @staticmethod
    def _normalise_focus(optimization_focus: str) -> tuple[str, ...]:
        tokens = [
            _FOCUS_ALIASES.get(token.strip().lower(), token.strip().lower())
            for token in optimization_focus.replace("/", ",").split(",")
            if token.strip()
        ]
        if not tokens:
            return ("balanced",)
        deduped: list[str] = []
        for token in tokens:
            if token and token not in deduped:
                deduped.append(token)
        return tuple(deduped or ["balanced"])

    def _focus_action_context(self, component: str) -> str:
        focus_str = ", ".join(self._optimization_focus)
        return (
            f"Targeted self-audit for {component}. Optimisation focus: {focus_str}. "
            "Bias JIT signals toward Python 3.12+, async architectures, deterministic "
            "outputs, execution speed, and structural robustness."
        )

    @staticmethod
    def _score_improvement_value(
        component: str,
        suggestions: list[str],
        jit_signals: list[str],
        confidence_delta: float,
        tribunal_passed: bool,
        optimization_focus: tuple[str, ...] = ("balanced",),
    ) -> tuple[float, str]:
        """Compute a 0.0-1.0 value score for applying this component's improvements.

        Scoring model (additive, capped at 1.0):
          +0.30  if component is in the critical-path tier (router/tribunal/n_stroke/executor)
          +0.20  if ≥3 concrete suggestions were produced
          +0.15  per 0.10 of JIT confidence_delta (max +0.30)
          +0.10  if ≥3 JIT signals were collected
          -0.20  if tribunal did NOT pass (security risk, apply with caution)

        Returns (score, rationale: str).
        """
        _CRITICAL_PATH = frozenset(
            {"router", "tribunal", "n_stroke", "executor", "jit_booster"})
        _HIGH_IMPACT = frozenset(
            {"graph", "scope_evaluator", "refinement", "supervisor"})

        score = 0.0
        reasons: list[str] = []

        if component in _CRITICAL_PATH:
            score += 0.30
            reasons.append("critical-path component (+0.30)")
        elif component in _HIGH_IMPACT:
            score += 0.20
            reasons.append("high-impact component (+0.20)")
        else:
            score += 0.10
            reasons.append("supporting component (+0.10)")

        if len(suggestions) >= 3:
            score += 0.20
            reasons.append(f"{len(suggestions)} concrete suggestions (+0.20)")
        elif len(suggestions) >= 1:
            score += 0.10
            reasons.append(f"{len(suggestions)} suggestion(s) (+0.10)")

        jit_bonus = min(max(confidence_delta / 0.10, 0.0) * 0.15, 0.30)
        if jit_bonus > 0:
            score += jit_bonus
            reasons.append(
                f"confidence delta {confidence_delta:+.2f} → JIT bonus +{jit_bonus:.2f}")

        if len(jit_signals) >= 3:
            score += 0.10
            reasons.append(f"{len(jit_signals)} JIT signals (+0.10)")

        if not tribunal_passed:
            score -= 0.20
            reasons.append("tribunal failed (-0.20, security caution)")

        focus_set = set(optimization_focus)
        if "balanced" not in focus_set:
            if focus_set & {"efficiency", "speed"}:
                if component in {"executor", "jit_booster", "n_stroke", "model_garden", "graph"}:
                    score += 0.12
                    reasons.append("focus bonus: speed/efficiency-critical component (+0.12)")
            if "quality" in focus_set and component in {
                "refinement",
                "scope_evaluator",
                "daemon",
                "branch_executor",
                "supervisor",
            }:
                score += 0.10
                reasons.append("focus bonus: structural quality component (+0.10)")
            if "accuracy" in focus_set and component in {
                "router",
                "conversation",
                "mandate_executor",
                "vector_store",
                "tribunal",
            }:
                score += 0.10
                reasons.append("focus bonus: deterministic accuracy component (+0.10)")

        score = min(max(score, 0.0), 1.0)
        rationale = f"focus={','.join(optimization_focus)}; " + "; ".join(reasons)
        return round(score, 3), rationale

    @staticmethod
    def _top_recommendations(
        assessments: list[ComponentAssessment],
        refinement_recs: list[str],
    ) -> list[str]:
        """Merge and deduplicate the highest-priority recommendations."""
        seen: set[str] = set()
        recs: list[str] = []

        # Priority 1: recommendations from failed assessments
        for a in assessments:
            if not a.execution_success:
                rec = f"[{a.component.upper()}] Re-assess: execution did not pass tribunal."
                if rec not in seen:
                    seen.add(rec)
                    recs.append(rec)

        # Priority 2: top suggestion from each component (first signal → strongest)
        for a in assessments:
            if a.suggestions:
                rec = f"[{a.component.upper()}] {a.suggestions[0]}"
                if rec not in seen:
                    seen.add(rec)
                    recs.append(rec)

        # Priority 3: refinement loop recommendations
        for r in refinement_recs:
            if r not in seen:
                seen.add(r)
                recs.append(r)

        return recs[:10]  # cap at 10 top recommendations
