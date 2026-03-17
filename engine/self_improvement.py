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
  Wave 1 [core-security]  : router · tribunal · psyche_bank           (×3 parallel)
  Wave 2 [performance]    : jit_booster · executor · graph             (×3 parallel)
  Wave 3 [meta-analysis]  : scope_evaluator · refinement               (×2 parallel)

Scope: 8 nodes · 3 waves · max ×3 parallel · strategy: deep-parallel
Risk:  router (circuit-breaker state), tribunal (OWASP patterns must not trigger
       on self-audit mandates — uses benign audit-only text)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from engine.executor import Envelope, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBooster
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.router import MandateRouter
from engine.scope_evaluator import ScopeEvaluator
from engine.tribunal import Engram, Tribunal

if TYPE_CHECKING:
    from engine.jit_booster import JITBoostResult
    from engine.router import RouteResult

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
        }


# ── Engine ────────────────────────────────────────────────────────────────────


class SelfImprovementEngine:
    """Run the full pipeline against each engine component to surface improvement
    opportunities.

    Uses a *dedicated* MandateRouter in ``route_chat`` mode so the self-improvement
    cycle never trips the shared circuit-breaker used by the Governor API.

    Usage::

        engine = SelfImprovementEngine()
        report = engine.run()
    """

    # Suggestions derived from verdicts — extracted from refinement recommendations
    _WAVE_LABELS = {1: "core-security", 2: "performance", 3: "meta-analysis"}

    def __init__(
        self,
        booster: JITBooster | None = None,
        bank: PsycheBank | None = None,
    ) -> None:
        # Isolated router — never touches the shared circuit-breaker
        self._router = MandateRouter()
        self._booster = booster or JITBooster()
        self._bank = bank or PsycheBank()
        self._tribunal = Tribunal(bank=self._bank)
        self._executor = JITExecutor(max_workers=3)
        self._sorter = TopologicalSorter()
        self._scope_evaluator = ScopeEvaluator()
        self._refinement_loop = RefinementLoop()

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> SelfImprovementReport:
        """Execute the self-improvement cycle and return a ``SelfImprovementReport``."""
        t0 = time.monotonic()
        improvement_id = f"si-{uuid.uuid4().hex[:8]}"

        # Build wave spec from component manifest
        wave_spec = self._build_wave_spec()
        waves = self._sorter.sort(wave_spec)

        assessments: list[ComponentAssessment] = []

        for wave_idx, wave_nodes in enumerate(waves, start=1):
            wave_components = [
                c for c in _COMPONENTS
                if c["wave"] == wave_idx
            ]

            # Fan-out all components in this wave in parallel
            envelopes = [
                Envelope(
                    mandate_id=f"{improvement_id}-{c['component']}",
                    intent="AUDIT",
                    domain="self-improvement",
                    metadata={"component": c},
                )
                for c in wave_components
            ]

            wave_results = self._executor.fan_out(
                self._assess_component, envelopes
            )

            for result in wave_results:
                if result.success and isinstance(result.output, ComponentAssessment):
                    assessments.append(result.output)
                else:
                    # Emit a degraded assessment so the report is always complete
                    comp = next(
                        c for c in wave_components
                        if f"{improvement_id}-{c['component']}" == result.mandate_id
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
                    ))

        # Build refinement envelopes representing the component assessments
        # local import avoids circularity at module level
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
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_wave_spec(self) -> list[tuple[str, list[str]]]:
        """Convert the component manifest into a TopologicalSorter-compatible spec."""
        return [
            (c["component"], c["deps"])
            for c in _COMPONENTS
        ]

    def _assess_component(self, env: Envelope) -> ComponentAssessment:
        """Full pipeline assessment for one component (runs inside a thread)."""
        comp: dict[str, Any] = env.metadata["component"]
        mandate_text: str = comp["mandate"]
        component_name: str = comp["component"]

        # 1. Route through isolated router (chat mode — no CB side-effects)
        route: RouteResult = self._router.route_chat(mandate_text)

        # 2. Mandatory JIT SOTA boost
        jit_result: JITBoostResult = self._booster.fetch(route)
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

        # 4. Micro-wave plan for this component (recon → plan → generate → validate)
        micro_spec: list[tuple[str, list[str]]] = [
            (f"{env.mandate_id}-recon", []),
            (f"{env.mandate_id}-analyse", [f"{env.mandate_id}-recon"]),
            (f"{env.mandate_id}-improve", [f"{env.mandate_id}-analyse"]),
        ]
        micro_waves = self._sorter.sort(micro_spec)

        # 5. Scope evaluation for the component's micro-plan
        scope = self._scope_evaluator.evaluate(
            micro_waves, intent=route.intent)

        # Derive component-specific suggestions from JIT signals
        suggestions = self._derive_suggestions(
            component_name, jit_result.signals)

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
        )

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
        }.get(component, "Apply")

        return [f"{action_prefix}: {s}" for s in signals[:3]]

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
