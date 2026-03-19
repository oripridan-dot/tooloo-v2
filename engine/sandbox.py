"""
engine/sandbox.py — Mirror Sandbox Orchestrator.

Each sandbox is an isolated "mirror app" — a parallel environment where a feature
mandate runs through the full TooLoo V2 pipeline. Results are evaluated and
reported before any feature is allowed to land on the main pipeline or user code.

Execution pipeline per sandbox (serial within each):
  1. VectorStore dedup   — reject near-identical features (threshold 0.90)
  2. Router              — classify intent (route_chat: isolated, no CB side-effects)
  3. JITBooster          — SOTA signals, compute boosted confidence
  4. Tribunal            — OWASP poison scan — hard security gate
  5. ScopeEvaluator      — allocate workers, produce 6-node wave plan
  6. JITExecutor         — fan-out execution (isolated sub-workers, max 4)
  7. RefinementLoop      — success/failure analysis
  8. DimensionScorer     — 9-dimension evaluation:
                             legal · safety · security · accuracy · honesty ·
                             efficiency · quality · performance · time_awareness
  9. ReadinessGate       — readiness_score ≥ PROMOTE_THRESHOLD → STATE_PROVEN

Parallelism:
  SandboxOrchestrator.run_parallel() fans out up to max_workers (default 25)
  sandboxes concurrently. Each sandbox uses its own sub-executor (max 4 workers).

Graph + vector indexing:
  CognitiveGraph tracks sandbox dependency chains across the orchestrator.
  VectorStore deduplicates feature submissions at submission time.

Broadcast:
  All state transitions are pushed via broadcast_fn → SSE event stream.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from engine.executor import Envelope, JITExecutor
from engine.graph import CognitiveGraph, TopologicalSorter
from engine.jit_booster import JITBooster
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.router import MandateRouter
from engine.scope_evaluator import ScopeEvaluator
from engine.tribunal import Engram, Tribunal
from engine.vector_store import VectorStore

# ── Constants ─────────────────────────────────────────────────────────────────
# DEV MODE: promote threshold lowered 0.72→0.50; internal workers raised 4→8
PROMOTE_THRESHOLD: float = 0.50    # readiness_score ≥ this → STATE_PROVEN
MAX_SANDBOX_WORKERS: int = 25      # orchestrator-level (overridable via .env)
_INTERNAL_WORKERS: int = 8         # per-sandbox sub-executor

# ── Sandbox states ────────────────────────────────────────────────────────────
STATE_QUEUED = "queued"
STATE_RUNNING = "running"
STATE_PROVEN = "proven"
STATE_FAILED = "failed"
STATE_BLOCKED = "blocked"
STATE_DUPLICATE = "duplicate"

# ── Dimension scoring weights ─────────────────────────────────────────────────
# Maps: dimension → {impact, difficulty, timeline} — used for weighted aggregation.
_DIM_WEIGHTS: dict[str, dict[str, float]] = {
    "legal":          {"impact": 0.70, "difficulty": 0.80, "timeline": 0.90},
    "safety":         {"impact": 0.90, "difficulty": 0.70, "timeline": 0.80},
    "security":       {"impact": 0.90, "difficulty": 0.80, "timeline": 0.80},
    "accuracy":       {"impact": 0.85, "difficulty": 0.60, "timeline": 0.60},
    "honesty":        {"impact": 0.75, "difficulty": 0.50, "timeline": 0.50},
    "efficiency":     {"impact": 0.80, "difficulty": 0.70, "timeline": 0.70},
    "quality":        {"impact": 0.85, "difficulty": 0.75, "timeline": 0.75},
    "performance":    {"impact": 0.80, "difficulty": 0.80, "timeline": 0.80},
    "time_awareness": {"impact": 0.70, "difficulty": 0.50, "timeline": 0.90},
}


class DimensionScorer:
    """Reusable 9-dimension evaluator shared by sandboxing and benchmarks.

    This wraps TooLoo's existing heuristic scoring formulas in a small stateless
    object so other workflows can evaluate efficiency / quality / accuracy
    without re-implementing sandbox math in ad-hoc scripts.
    """

    def score(
        self,
        *,
        original_conf: float,
        boosted_conf: float,
        tribunal_passed: bool,
        refinement_verdict: str,
        exec_success_rate: float,
    ) -> list[DimensionScore]:
        vm = {"pass": 1.0, "warn": 0.72, "fail": 0.35}.get(
            refinement_verdict, 0.5)
        templates: list[tuple[str, float, str]] = [
            ("legal",          min(1.0, boosted_conf * 0.85),
             "JIT SOTA signal alignment"),
            ("safety",         0.95 if tribunal_passed else 0.35,
             "Tribunal OWASP scan result"),
            ("security",       0.92 if tribunal_passed else 0.25,
             "Tribunal poison verdict"),
            ("accuracy",       min(1.0, original_conf * 1.1),
             "Router intent confidence (pre-boost)"),
            ("honesty",        min(1.0, original_conf * 1.05),
             "Routing transparency"),
            ("efficiency",     min(1.0, exec_success_rate * vm * 1.15),
             "Execution success x refinement"),
            ("quality",        (boosted_conf + exec_success_rate * vm) / 2,
             "Confidence x success composite"),
            ("performance",    min(1.0, boosted_conf * exec_success_rate),
             "JIT x execution composite"),
            ("time_awareness", min(1.0, exec_success_rate * vm * 0.9 + 0.1),
             "Execution timing efficiency"),
        ]
        return [
            DimensionScore(
                name=name,
                score=round(max(0.0, min(1.0, score)), 3),
                confidence=round(boosted_conf, 3),
                notes=notes,
            )
            for name, score, notes in templates
        ]


# ── DTOs ──────────────────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    name: str
    score: float        # 0.0-1.0
    confidence: float   # underlying boosted confidence
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 3),
            "confidence": round(self.confidence, 3),
            "notes": self.notes,
        }


@dataclass
class SandboxReport:
    """Complete result of one sandbox execution cycle."""
    sandbox_id: str
    feature_title: str
    feature_text: str
    state: str
    intent: str
    confidence: float
    tribunal_passed: bool
    scope_summary: str
    exec_success_rate: float
    refinement_verdict: str
    dimension_scores: list[DimensionScore]
    impact_score: float
    difficulty_score: float
    readiness_score: float
    timeline_days: int
    recommendations: list[str]
    similar_sandboxes: list[dict[str, Any]]
    latency_ms: float
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())
    roadmap_item_id: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sandbox_id": self.sandbox_id,
            "feature_title": self.feature_title,
            "feature_text": self.feature_text[:300],
            "state": self.state,
            "intent": self.intent,
            "confidence": round(self.confidence, 3),
            "tribunal_passed": self.tribunal_passed,
            "scope_summary": self.scope_summary,
            "exec_success_rate": round(self.exec_success_rate, 3),
            "refinement_verdict": self.refinement_verdict,
            "dimension_scores": [d.to_dict() for d in self.dimension_scores],
            "impact_score": round(self.impact_score, 3),
            "difficulty_score": round(self.difficulty_score, 3),
            "readiness_score": round(self.readiness_score, 3),
            "timeline_days": self.timeline_days,
            "recommendations": self.recommendations,
            "similar_sandboxes": self.similar_sandboxes,
            "latency_ms": round(self.latency_ms, 2),
            "created_at": self.created_at,
            "roadmap_item_id": self.roadmap_item_id,
            "notes": self.notes,
        }


# ── Orchestrator ──────────────────────────────────────────────────────────────

class SandboxOrchestrator:
    """Supervises all sandbox executions.

    Each sandbox is isolated — its own route/tribunal/execution context —
    but optionally shares the JITBooster and PsycheBank with the main
    Governor API for consistency of SOTA signals and rule learning.

    Thread-safe registry tracks all completed reports.
    VectorStore deduplicates features before spawning.
    CognitiveGraph records sandbox dependency chains.
    """

    def __init__(
        self,
        max_workers: int = MAX_SANDBOX_WORKERS,
        broadcast_fn: Callable[[dict[str, Any]], None] | None = None,
        booster: JITBooster | None = None,
        bank: PsycheBank | None = None,
    ) -> None:
        self._max_workers = max_workers
        self._broadcast = broadcast_fn or (lambda _: None)
        self._bank = bank or PsycheBank()
        self._tribunal = Tribunal(bank=self._bank)
        # Isolated router — never trips the shared circuit-breaker
        self._router = MandateRouter()
        self._booster = booster or JITBooster()
        self._scope_evaluator = ScopeEvaluator()
        self._refinement_loop = RefinementLoop()
        self._dimension_scorer = DimensionScorer()
        self._sorter = TopologicalSorter()
        self._inner_executor = JITExecutor(max_workers=_INTERNAL_WORKERS)
        self._outer_executor = JITExecutor(max_workers=max_workers)
        # Graph tracks sandbox dependency chains
        self._graph = CognitiveGraph()
        # Vector store deduplicates feature submissions (threshold 0.90)
        self._vector_store = VectorStore(dup_threshold=0.90)
        self._registry: dict[str, SandboxReport] = {}
        self._lock = threading.RLock()

    # ── Core execution ────────────────────────────────────────────────────────

    def run_sandbox(
        self,
        feature_text: str,
        feature_title: str = "",
        roadmap_item_id: str | None = None,
        sandbox_id: str | None = None,
    ) -> SandboxReport:
        """Run the full TooLoo pipeline in an isolated sandbox for one feature."""
        t0 = time.monotonic()
        sandbox_id = sandbox_id or f"sb-{uuid.uuid4().hex[:8]}"
        feature_title = feature_title or feature_text[:60].strip()

        # 1. Vector deduplication — search before adding to corpus
        similar = self._vector_store.search(
            feature_text, top_k=3, threshold=0.2)
        is_new = self._vector_store.add(
            doc_id=sandbox_id,
            text=feature_text,
            metadata={"title": feature_title, "sandbox_id": sandbox_id},
        )

        if not is_new:
            report = SandboxReport(
                sandbox_id=sandbox_id,
                feature_title=feature_title,
                feature_text=feature_text,
                state=STATE_DUPLICATE,
                intent="BLOCKED",
                confidence=0.0,
                tribunal_passed=False,
                scope_summary="Near-duplicate feature — sandbox skipped.",
                exec_success_rate=0.0,
                refinement_verdict="warn",
                dimension_scores=[],
                impact_score=0.0,
                difficulty_score=0.0,
                readiness_score=0.0,
                timeline_days=0,
                recommendations=[
                    "Near-duplicate feature detected. Review similar sandboxes before proceeding."
                ],
                similar_sandboxes=[r.to_dict() for r in similar],
                latency_ms=round((time.monotonic() - t0) * 1000, 2),
                roadmap_item_id=roadmap_item_id,
            )
            with self._lock:
                self._registry[sandbox_id] = report
            self._broadcast({
                "type": "sandbox", "sandbox_id": sandbox_id,
                "state": STATE_DUPLICATE, "report": report.to_dict(),
            })
            return report

        self._broadcast({
            "type": "sandbox", "sandbox_id": sandbox_id,
            "state": STATE_RUNNING, "feature_title": feature_title,
        })

        # 2. Route (route_chat: isolated, never trips shared circuit-breaker)
        route = self._router.route_chat(feature_text)

        # 3. JIT SOTA boost
        jit_result = self._booster.fetch(route)
        self._router.apply_jit_boost(route, jit_result.boosted_confidence)

        # 4. Tribunal — OWASP hard security gate
        engram = Engram(
            slug=sandbox_id,
            intent=route.intent,
            logic_body=feature_text,
            domain="sandbox",
            mandate_level="L2",
        )
        tribunal_result = self._tribunal.evaluate(engram)

        # 5. Build 6-node isolated DAG plan
        spec: list[tuple[str, list[str]]] = [
            (f"{sandbox_id}-scope",    []),
            (f"{sandbox_id}-analyze",  [f"{sandbox_id}-scope"]),
            (f"{sandbox_id}-design",   [f"{sandbox_id}-analyze"]),
            (f"{sandbox_id}-impl",     [f"{sandbox_id}-design"]),
            (f"{sandbox_id}-validate", [f"{sandbox_id}-impl"]),
            (f"{sandbox_id}-refine",   [f"{sandbox_id}-validate"]),
        ]
        plan = self._sorter.sort(spec)

        # 6. Scope evaluation
        scope = self._scope_evaluator.evaluate(plan, intent=route.intent)

        # 7. Fan-out execution (isolated sub-workers)
        envelopes = [
            Envelope(
                mandate_id=f"{sandbox_id}-w{i}",
                intent=route.intent,
                domain="sandbox",
                metadata={"wave": i, "nodes": wave, "sandbox_id": sandbox_id},
            )
            for i, wave in enumerate(plan)
        ]

        def _sandbox_work(env: Envelope) -> str:
            return f"sandbox-wave-{env.metadata['wave']}-done"

        exec_results = self._inner_executor.fan_out(
            _sandbox_work, envelopes, max_workers=scope.recommended_workers,
        )

        # 8. Refinement
        refinement = self._refinement_loop.evaluate(exec_results)

        # 9. Dimension scoring
        dim_scores = self._score_dimensions(
            original_conf=jit_result.original_confidence,
            boosted_conf=jit_result.boosted_confidence,
            tribunal_passed=tribunal_result.passed,
            refinement_verdict=refinement.verdict,
            exec_success_rate=refinement.success_rate,
        )

        # 10. Aggregate scores
        impact = self._aggregate(dim_scores, "impact")
        difficulty = self._aggregate(dim_scores, "difficulty")
        timeline_days = self._estimate_timeline(difficulty, len(plan))
        readiness = self._compute_readiness(
            tribunal_passed=tribunal_result.passed,
            exec_success_rate=refinement.success_rate,
            refinement_verdict=refinement.verdict,
            confidence=route.confidence,
            impact=impact,
        )

        # 11. Classify final state
        if not tribunal_result.passed:
            state = STATE_BLOCKED
        elif readiness >= PROMOTE_THRESHOLD:
            state = STATE_PROVEN
        else:
            state = STATE_FAILED

        # 12. Build recommendations
        recs = list(refinement.recommendations)
        if readiness < PROMOTE_THRESHOLD:
            recs.append(
                f"Readiness {readiness:.2f} below threshold {PROMOTE_THRESHOLD} — "
                "iterate before promoting to main pipeline."
            )
        if similar:
            recs.append(
                f"Found {len(similar)} related feature(s) — consider merging: "
                + ", ".join(r.id for r in similar[:2])
            )

        report = SandboxReport(
            sandbox_id=sandbox_id,
            feature_title=feature_title,
            feature_text=feature_text,
            state=state,
            intent=route.intent,
            confidence=route.confidence,
            tribunal_passed=tribunal_result.passed,
            scope_summary=scope.scope_summary,
            exec_success_rate=refinement.success_rate,
            refinement_verdict=refinement.verdict,
            dimension_scores=dim_scores,
            impact_score=impact,
            difficulty_score=difficulty,
            readiness_score=readiness,
            timeline_days=timeline_days,
            recommendations=recs,
            similar_sandboxes=[r.to_dict() for r in similar[:2]],
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            roadmap_item_id=roadmap_item_id,
        )
        with self._lock:
            self._registry[sandbox_id] = report
        self._broadcast({
            "type": "sandbox", "sandbox_id": sandbox_id,
            "state": state, "report": report.to_dict(),
        })
        return report

    def run_parallel(
        self,
        features: list[dict[str, str]],
    ) -> list[SandboxReport]:
        """Fan-out up to max_workers sandboxes in parallel.

        Each entry in ``features`` should contain:
          text            — feature description (required)
          title           — feature title (optional)
          roadmap_item_id — linked roadmap item ID (optional)
        """
        envelopes = [
            Envelope(
                mandate_id=f"sb-{uuid.uuid4().hex[:8]}",
                intent="BUILD",
                domain="sandbox",
                metadata=feat,
            )
            for feat in features
        ]

        def _work(env: Envelope) -> SandboxReport:
            return self.run_sandbox(
                feature_text=env.metadata.get("text", ""),
                feature_title=env.metadata.get("title", ""),
                roadmap_item_id=env.metadata.get("roadmap_item_id"),
                sandbox_id=env.mandate_id,
            )

        results = self._outer_executor.fan_out(
            _work, envelopes, max_workers=self._max_workers,
        )
        return [r.output for r in results if r.success and r.output is not None]

    # ── Scoring helpers ───────────────────────────────────────────────────────

    def _score_dimensions(
        self,
        original_conf: float,
        boosted_conf: float,
        tribunal_passed: bool,
        refinement_verdict: str,
        exec_success_rate: float,
    ) -> list[DimensionScore]:
        """Score each of the 9 evaluation dimensions."""
        return self._dimension_scorer.score(
            original_conf=original_conf,
            boosted_conf=boosted_conf,
            tribunal_passed=tribunal_passed,
            refinement_verdict=refinement_verdict,
            exec_success_rate=exec_success_rate,
        )

    def _aggregate(self, dim_scores: list[DimensionScore], key: str) -> float:
        if not dim_scores:
            return 0.0
        total = weight_sum = 0.0
        for ds in dim_scores:
            w = _DIM_WEIGHTS.get(ds.name, {}).get(key, 0.5)
            total += ds.score * w
            weight_sum += w
        return round(total / max(weight_sum, 1e-9), 3)

    def _estimate_timeline(self, difficulty: float, wave_count: int) -> int:
        """Estimate implementation days (1-90) from difficulty + plan depth."""
        return min(90, max(1, int(difficulty * 60)) + wave_count * 2)

    def _compute_readiness(
        self,
        tribunal_passed: bool,
        exec_success_rate: float,
        refinement_verdict: str,
        confidence: float,
        impact: float,
    ) -> float:
        """Composite readiness score (0-1). Tribunal failure is a hard gate."""
        if not tribunal_passed:
            return 0.0
        verdict_score = {"pass": 1.0, "warn": 0.65, "fail": 0.25}.get(
            refinement_verdict, 0.0
        )
        return round(
            min(1.0, max(0.0,
                exec_success_rate * 0.35
                + confidence * 0.25
                + verdict_score * 0.25
                + impact * 0.15
                         )),
            3,
        )

    # ── Registry access ───────────────────────────────────────────────────────

    def get_report(self, sandbox_id: str) -> SandboxReport | None:
        with self._lock:
            return self._registry.get(sandbox_id)

    def all_reports(self) -> list[SandboxReport]:
        with self._lock:
            return list(self._registry.values())

    def vector_store_summary(self) -> dict[str, Any]:
        return self._vector_store.to_dict()

    def graph_summary(self) -> dict[str, Any]:
        nodes = self._graph.nodes()
        edges = [{"from": u, "to": v} for u, v in self._graph.edges()]
        return {"nodes": nodes, "edges": edges}
