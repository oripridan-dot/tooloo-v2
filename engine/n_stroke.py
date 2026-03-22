# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T20:01:58.820851+00:00
# Component: n_stroke  Source: engine/n_stroke.py
# Improvement signals from JIT SOTA booster:
#  [1] Optimise engine/n_stroke.py: OWASP Top 10 2025 edition promotes Broken Object-
#     Level Authorisation to the #1 priority
#  [2] Optimise engine/n_stroke.py: OSS supply-chain audits (Sigstore + Rekor
#     transparency log) are required in regulated environments
#  [3] Optimise engine/n_stroke.py: CSPM tools (Wiz, Orca, Prisma Cloud) provide
#     real-time cloud posture scoring in 2026
# ─────────────────────────────────────────────────────────────────
"""
engine/n_stroke.py — N-Stroke Autonomous Cognitive Loop.

Generalises TwoStrokeEngine to N strokes with three key additions:

  1. **Dynamic model selection** — ModelSelector escalates the model tier
     on each failed stroke, from Flash → Flash-Exp → Pro → Pro-Thinking.

  2. **MCP tool injection** — MCPManager's full tool manifest is injected
     into every stroke's execution context so nodes can invoke file_read,
     web_lookup, code_analyze, run_tests, and read_error autonomously.

  3. **Autonomous healing** — RefinementSupervisor triggers when any node
     accumulates >= NODE_FAIL_THRESHOLD failures. It pauses the loop, heals
     via MCP + SOTA signals, then resumes with a corrected work function.

Pipeline per stroke:

  [PreflightSupervisor]  → model_select + JIT SOTA + Tribunal
        ↓ SSE: preflight
  [Process 1 — Catalyst] → DAG plan + scope eval + MCP manifest inject
        ↓ SSE: plan
  [MidflightSupervisor]  → JIT pass 2 + Tribunal rescan
        ↓ SSE: midflight
  [Process 2 — Crucible] → JITExecutor fan_out, MCP tools in env metadata
        ↓ SSE: execution
  [Satisfaction Gate]    → RefinementLoop verdict
        ↓ SSE: satisfaction_gate
        ↓ fail: increment stroke, escalate model, inject failure signal
        ↓ any node fails 3+ times: RefinementSupervisor heals before retry

The loop terminates on ``verdict == "pass"`` or when MAX_STROKES is reached.
All iteration state is immutable — each stroke starts fresh, enriched by the
prior failure signal and (optionally) the healed work function.
"""
from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.config import AUTONOMOUS_CONFIDENCE_THRESHOLD, settings as _cfg
from engine.async_fluid_executor import AsyncEnvelope, AsyncExecutionResult, AsyncFluidExecutor
from engine.dynamic_model_registry import (
    FractalDAGExpander,
    JIT16DBidder,
    get_bidder,
    get_dynamic_registry,
)
from engine.executor import Envelope, ExecutionResult, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBooster, JITBoostResult
from engine.mandate_executor import make_live_work_fn
from engine.mcp_manager import MCPManager
from engine.meta_architect import MetaArchitect
from engine.model_garden import get_garden
from engine.model_selector import ModelSelection, ModelSelector
from engine.refinement import RefinementLoop, RefinementReport
from engine.refinement_supervisor import (
    NODE_FAIL_THRESHOLD,
    HealingReport,
    RefinementSupervisor,
)
from engine.router import LockedIntent, MandateRouter, RouteResult, compute_buddy_line
from engine.scope_evaluator import ScopeEvaluation, ScopeEvaluator
from engine.tribunal import Engram, Tribunal, TribunalResult
from engine.validator_16d import Validator16D

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Production default: 7 strokes. Override via MAX_STROKES env var for extended dev runs.
MAX_STROKES: int = 7        # hard cap on N-stroke loop iterations

# SimulationGate: warn if more than this fraction of dry-run outputs are symbolic.
_SYMBOLIC_RATIO_THRESHOLD: float = 0.60   # >60% symbolic → surface as warn

# Phase identifiers for the 3-phase pipeline
PHASE_BLUEPRINT = "blueprint"    # Phase 1: AUDIT + DESIGN + UX_EVAL — plan only
PHASE_DRY_RUN = "dry_run"      # Phase 2: generate staged in memory, no live writes
# Phase 3: promote staged → live (unlocked by Sim Gate)
PHASE_EXECUTE = "execute"

# Node names that are FORBIDDEN in blueprint & dry-run phases (state-changing)
_EXECUTE_ONLY_NODES: frozenset[str] = frozenset(
    {"implement", "emit", "file_write"})

# Mandatory discovery nodes injected at the front of every pipeline
_MANDATORY_DISCOVERY: list[str] = ["audit_wave", "design_wave", "ux_eval"]
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _infer_workspace_file_target(mandate_text: str) -> str:
    """Best-effort extraction of a workspace file path from conversational mandates."""
    candidates = re.findall(
        r"`([^`]+\.[\w]+)`|([\w./-]+\.[A-Za-z0-9]+)", mandate_text)
    for backticked, plain in candidates:
        raw = (backticked or plain).strip().lstrip("./")
        if not raw:
            continue
        resolved = (_REPO_ROOT / raw).resolve()
        if str(resolved).startswith(str(_REPO_ROOT)) and resolved.exists() and resolved.is_file():
            return str(resolved.relative_to(_REPO_ROOT))
    return ""


# ---------------------------------------------------------------------------
# Simulation Gate
# ---------------------------------------------------------------------------


class SimulationGate:
    """Evaluates the simulated (dry-run) output against the Phase 1 blueprint.

    Grades the dry-run on three dimensions:
      1. Completeness  — every blueprint section has a matching output section
      2. Quality       — output contains substantive content (not purely symbolic)
      3. Security      — no forbidden patterns present in dry-run text

    Returns ``passed=True`` when all three checks pass.  On fail, returns a
    list of failure reasons for injection into the retry-signal.
    """

    def evaluate(
        self,
        blueprint_nodes: list[str],
        dry_run_results: list[ExecutionResult],
        intent: str = "",
    ) -> tuple[bool, list[str]]:
        """Grade the dry-run output.

        Args:
            blueprint_nodes:  Node IDs produced in Phase 1.
            dry_run_results:  ExecutionResults from Phase 2 fan-out.
            intent:           Current mandate intent.

        Returns:
            (passed, failure_reasons)
        """
        failures: list[str] = []

        # Check 1: All dry-run nodes succeeded
        failed_nodes = [r.mandate_id for r in dry_run_results if not r.success]
        if failed_nodes:
            failures.append(
                f"Dry-run nodes failed: {failed_nodes[:3]} — retry required"
            )

        # Check 2: Outputs are substantive (not purely symbolic fallback)
        symbolic_count = 0
        for r in dry_run_results:
            if r.success and isinstance(r.output, dict):
                out = str(r.output.get("output", ""))
                if out.startswith("[symbolic-"):
                    symbolic_count += 1
        if symbolic_count > len(dry_run_results) * _SYMBOLIC_RATIO_THRESHOLD:
            # More than 60 % symbolic — ok in offline mode, surface as warn
            failures.append(
                f"Dry-run produced {symbolic_count}/{len(dry_run_results)} symbolic outputs "
                f"(offline mode — acceptable, promoting to execute)"
            )
            # Not a blocking failure in offline mode — clear it
            failures.pop()

        # Check 3: Blueprint coverage — at least one discovery node present
        if not blueprint_nodes:
            failures.append(
                "Phase 1 blueprint is empty — cannot proceed to execute")

        return len(failures) == 0, failures


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass
class StrokeRecord:
    """Immutable record of one complete N-stroke cycle."""

    stroke: int
    model_selection: ModelSelection
    preflight_jit: JITBoostResult
    preflight_tribunal: TribunalResult
    plan: list[list[str]]
    scope: ScopeEvaluation
    mcp_tools_injected: list[str]          # tool names injected this stroke
    midflight_jit: JITBoostResult
    execution_results: list[ExecutionResult]
    refinement: RefinementReport
    healing_report: HealingReport | None
    satisfied: bool
    latency_ms: float
    # Phase-specific records (populated when 3-phase mode is active)
    blueprint_nodes: list[str] = field(default_factory=list)
    dry_run_passed: bool = True             # True in 1-phase / offline mode
    simulation_gate_failures: list[str] = field(default_factory=list)
    active_phase: str = PHASE_EXECUTE       # which phase this stroke represents
    confidence_proof: dict[str, Any] = field(default_factory=dict)
    divergence_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stroke": self.stroke,
            "model_selection": self.model_selection.to_dict(),
            "preflight_jit": self.preflight_jit.to_dict(),
            "preflight_tribunal": self.preflight_tribunal.to_dict(),
            "plan": self.plan,
            "scope": self.scope.to_dict(),
            "mcp_tools_injected": self.mcp_tools_injected,
            "midflight_jit": self.midflight_jit.to_dict(),
            "execution_results": [r.to_dict() for r in self.execution_results],
            "refinement": self.refinement.to_dict(),
            "healing_report": self.healing_report.to_dict() if self.healing_report else None,
            "satisfied": self.satisfied,
            "latency_ms": round(self.latency_ms, 2),
            "blueprint_nodes": self.blueprint_nodes,
            "dry_run_passed": self.dry_run_passed,
            "simulation_gate_failures": self.simulation_gate_failures,
            "active_phase": self.active_phase,
            "confidence_proof": self.confidence_proof,
            "divergence_metrics": self.divergence_metrics,
        }


@dataclass
class NStrokeResult:
    """Final aggregated result of the complete N-stroke pipeline run."""

    pipeline_id: str
    locked_intent: LockedIntent
    strokes: list[StrokeRecord]
    final_verdict: str        # "pass" | "warn" | "fail"
    satisfied: bool
    total_strokes: int
    model_escalations: int    # how many times the model tier increased
    healing_invocations: int  # how many times RefinementSupervisor ran
    latency_ms: float
    crisis: dict[str, Any] | None = None  # populated by No Dead Ends Protocol
    execution_mode: str = "sync"  # "sync" | "async_fluid"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "locked_intent": self.locked_intent.to_dict(),
            "strokes": [s.to_dict() for s in self.strokes],
            "final_verdict": self.final_verdict,
            "satisfied": self.satisfied,
            "total_strokes": self.total_strokes,
            "model_escalations": self.model_escalations,
            "healing_invocations": self.healing_invocations,
            "latency_ms": round(self.latency_ms, 2),
            "crisis": self.crisis,
            "execution_mode": self.execution_mode,
            "strokes_detail": [
                {
                    "stroke_num": s.stroke,
                    "latency_ms": round(s.latency_ms, 2),
                    "node_count": len(s.execution_results),
                    "execution_mode": self.execution_mode,
                }
                for s in self.strokes
            ],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _route_from_locked(locked: LockedIntent) -> RouteResult:
    """Synthesise a RouteResult from a LockedIntent for JIT/Tribunal APIs."""
    from engine.config import CIRCUIT_BREAKER_THRESHOLD  # avoid circular at module load
    return RouteResult(
        intent=locked.intent,
        confidence=locked.confidence,
        circuit_open=locked.confidence < CIRCUIT_BREAKER_THRESHOLD,
        mandate_text=locked.mandate_text,
        buddy_line=compute_buddy_line(locked.intent, locked.confidence),
    )


# ---------------------------------------------------------------------------
# N-Stroke Engine
# ---------------------------------------------------------------------------


class NStrokeEngine:
    """N-Stroke Autonomous Cognitive Loop.

    Injects dynamic model selection, MCP tooling, and autonomous healing on
    top of the Two-Stroke foundation.  Loops until satisfaction or MAX_STROKES.

    All components are injected via the constructor for full test isolation.

    Architecture::

        PreflightSupervisor → Process 1 → MidflightSupervisor →
        Process 2 → Satisfaction Gate → (loop back if needed)

    SSE events emitted (``broadcast_fn``):
        n_stroke_start · model_selected · healing_triggered · preflight ·
        plan · midflight · execution · satisfaction_gate · n_stroke_complete
    """

    def __init__(
        self,
        router: MandateRouter,
        booster: JITBooster,
        tribunal: Tribunal,
        sorter: TopologicalSorter,
        executor: JITExecutor,
        scope_evaluator: ScopeEvaluator,
        refinement_loop: RefinementLoop,
        mcp_manager: MCPManager,
        model_selector: ModelSelector,
        refinement_supervisor: RefinementSupervisor,
        broadcast_fn: Callable[[dict[str, Any]], None] | None = None,
        max_strokes: int = MAX_STROKES,
        async_fluid_executor: AsyncFluidExecutor | None = None,
    ) -> None:
        self._router = router
        self._booster = booster
        self._tribunal = tribunal
        self._sorter = sorter
        self._executor = executor
        self._scope = scope_evaluator
        self._refine = refinement_loop
        self._mcp = mcp_manager
        self._model_selector = model_selector
        self._ref_supervisor = refinement_supervisor
        self._meta_architect = MetaArchitect()
        self._garden = get_garden()
        self._validator_16d = Validator16D()
        # Dynamic model bidding (JIT 16D) & fractal expansion
        self._bidder: JIT16DBidder | None = (
            get_bidder() if _cfg.jit_bidder_enabled else None
        )
        self._fractal_expander: FractalDAGExpander | None = (
            FractalDAGExpander() if _cfg.fractal_dag_enabled else None
        )
        self._broadcast: Callable[[dict[str, Any]], None] = (
            broadcast_fn if broadcast_fn is not None else lambda _: None
        )
        self._max_strokes = max_strokes
        self._async_fluid_executor = async_fluid_executor

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        locked_intent: LockedIntent,
        pipeline_id: str | None = None,
        work_fn: Callable[[Envelope], Any] | None = None,
    ) -> NStrokeResult:
        """Execute N-stroke loop until satisfied or max_strokes reached.

        Args:
            locked_intent: Confirmed intent from ConversationalIntentDiscovery.
            pipeline_id:   Stable correlation ID for SSE events.
            work_fn:       Optional custom execution function.  If ``None``,
                           the default symbolic work function is used.  Tests
                           may inject deliberate failures to drive looping.
        """
        t0 = time.monotonic()
        pipeline_id = pipeline_id or f"nstroke-{uuid.uuid4().hex[:8]}"
        strokes: list[StrokeRecord] = []
        prior_verdict = ""
        # Per-node fail counters: {node_id: fail_count}
        node_fail_counts: dict[str, int] = {}
        healing_invocations = 0
        model_escalations = 0
        current_work_fn = work_fn if work_fn is not None else self._default_work_fn

        self._broadcast({
            "type": "n_stroke_start",
            "pipeline_id": pipeline_id,
            "intent": locked_intent.intent,
            "confidence": locked_intent.confidence,
            "max_strokes": self._max_strokes,
            # DORA-aligned: surface the model tier so dashboards can correlate
            # generation quality with latency and change-failure-rate metrics.
            "model_id": getattr(self, "_active_model", None),
        })

        # ── Law 20 (Amended) — advisory consultation gate ─────────────────────
        # Broadcast a consultation_recommended signal when confidence is below
        # the autonomous threshold (default 0.99).  Execution is NEVER blocked —
        # this is advisory only so the user can review if they are present.
        if locked_intent.confidence < AUTONOMOUS_CONFIDENCE_THRESHOLD:
            self._broadcast({
                "type": "consultation_recommended",
                "pipeline_id": pipeline_id,
                "intent": locked_intent.intent,
                "confidence": locked_intent.confidence,
                "threshold": AUTONOMOUS_CONFIDENCE_THRESHOLD,
                "reason": (
                    f"Confidence {locked_intent.confidence:.2f} is below the "
                    f"autonomous threshold {AUTONOMOUS_CONFIDENCE_THRESHOLD}. "
                    "Proceeding autonomously — user review suggested."
                ),
            })

        for stroke_num in range(1, self._max_strokes + 1):

            # ── 1. Dynamic model selection ────────────────────────────────────
            model_sel = self._model_selector.select(
                stroke=stroke_num,
                intent=locked_intent.intent,
                prior_verdict=prior_verdict,
            )
            if stroke_num > 1 and strokes:
                prev_tier = strokes[-1].model_selection.tier
                if model_sel.tier > prev_tier:
                    model_escalations += 1

            self._broadcast({
                "type": "model_selected",
                "pipeline_id": pipeline_id,
                "stroke": stroke_num,
                "model": model_sel.model,
                "vertex_model_id": model_sel.vertex_model_id,
                "tier": model_sel.tier,
                "rationale": model_sel.rationale,
            })

            # ── 2. Autonomous healing check ───────────────────────────────────
            healing_report: HealingReport | None = None
            nodes_needing_healing = [
                nid for nid, cnt in node_fail_counts.items()
                if cnt >= NODE_FAIL_THRESHOLD
            ]
            if nodes_needing_healing:
                # Collect last error messages for the failing nodes
                # Keys use canonical node name (last segment) so they
                # match the canonical keys used in node_fail_counts.
                last_error_map: dict[str, str] = {}
                if strokes:
                    for r in strokes[-1].execution_results:
                        if r.error:
                            canonical_key = r.mandate_id.rsplit("-", 1)[-1]
                            last_error_map[canonical_key] = r.error

                healing_report = self._ref_supervisor.heal(
                    failed_node_ids=nodes_needing_healing,
                    stroke=stroke_num,
                    intent=locked_intent.intent,
                    mcp=self._mcp,
                    booster=self._booster,
                    mandate_text=locked_intent.mandate_text,
                    last_error_map=last_error_map,
                )
                healing_invocations += 1

                self._broadcast({
                    "type": "healing_triggered",
                    "pipeline_id": pipeline_id,
                    "stroke": stroke_num,
                    "nodes_healed": healing_report.nodes_healed,
                    "healing_id": healing_report.healing_id,
                    "verdict": healing_report.verdict,
                })

                # Reset fail counters for healed nodes (keyed by canonical name)
                for nid in healing_report.nodes_healed:
                    # Support both canonical ("implement") and fully-qualified IDs
                    node_fail_counts.pop(nid, None)
                    node_fail_counts.pop(nid.rsplit("-", 1)[-1], None)

                # Swap in the healed work function for this stroke
                if healing_report.healed_work_fn is not None:
                    current_work_fn = healing_report.healed_work_fn

            # ── 3. Build prior-failure signal for JIT context ─────────────────
            prior_failure_signal = ""
            if prior_verdict in ("fail", "warn") and strokes:
                last_stroke = strokes[-1]
                failed_nodes = last_stroke.refinement.failed_nodes
                prior_failure_signal = (
                    f"[retry-signal stroke={stroke_num - 1}] "
                    f"model={last_stroke.model_selection.model}, "
                    f"verdict={prior_verdict}, "
                    f"failed_nodes={failed_nodes[:3]}, "
                    f"escalated_to={model_sel.model}. "
                    f"Reapproach with corrections."
                )

            # ── 4. Execute one full stroke ────────────────────────────────────
            stroke_record = self._run_stroke(
                locked_intent=locked_intent,
                pipeline_id=pipeline_id,
                stroke_num=stroke_num,
                model_sel=model_sel,
                prior_failure_signal=prior_failure_signal,
                work_fn=current_work_fn,
                healing_report=healing_report,
            )
            strokes.append(stroke_record)

            # ── 5. Update per-node fail counters ──────────────────────────────
            # Track by canonical node name (e.g. "implement") so that the
            # same logical node accumulates failures across strokes instead
            # of each stroke's unique ID starting a fresh counter.
            for r in stroke_record.execution_results:
                if not r.success:
                    canonical = r.mandate_id.rsplit("-", 1)[-1]
                    node_fail_counts[canonical] = (
                        node_fail_counts.get(canonical, 0) + 1
                    )

            # ── 5b. Fractal DAG expansion for failing nodes ──────────────────
            if self._fractal_expander is not None:
                for r in stroke_record.execution_results:
                    if not r.success:
                        canonical = r.mandate_id.rsplit("-", 1)[-1]
                        fail_cnt = node_fail_counts.get(canonical, 0)
                        expansion = self._fractal_expander.maybe_expand(
                            failed_node_id=canonical,
                            action_type=canonical,
                            failure_count=fail_cnt,
                            error_message=r.error or "",
                        )
                        if expansion is not None:
                            self._broadcast({
                                "type": "fractal_expansion",
                                "pipeline_id": pipeline_id,
                                "stroke": stroke_num,
                                "original_node": expansion.original_node_id,
                                "sub_nodes": len(expansion.sub_nodes),
                                "reason": expansion.reason,
                            })

            prior_verdict = stroke_record.refinement.verdict

            self._broadcast({
                "type": "satisfaction_gate",
                "pipeline_id": pipeline_id,
                "stroke": stroke_num,
                "satisfied": stroke_record.satisfied,
                "verdict": prior_verdict,
                "model": model_sel.model,
                "total_strokes_so_far": stroke_num,
                "node_fail_counts": dict(node_fail_counts),
            })

            if stroke_record.satisfied:
                break

        # ── Final result ──────────────────────────────────────────────────────
        last = strokes[-1] if strokes else None
        final_verdict = last.refinement.verdict if last else "fail"
        satisfied = last.satisfied if last else False

        # ── No Dead Ends Protocol: crisis synthesis on exhaustion ─────────────
        # When the loop exits without satisfaction (all MAX_STROKES consumed
        # without passing the refinement gate), synthesise a structured crisis
        # payload and emit an `actionable_intervention` SSE event.  The UI
        # renders this as an amber card with 2-3 clickable resolution buttons
        # that auto-fill the mandate input — ensuring the user is never left
        # staring at a "fail" verdict with no path forward.
        if not satisfied:
            crisis_payload = self._synthesize_crisis(
                mandate_text=locked_intent.mandate_text,
                intent=locked_intent.intent,
                strokes=strokes,
            )
            self._broadcast({
                "type": "actionable_intervention",
                "pipeline_id": pipeline_id,
                "crisis": crisis_payload,
            })
        else:
            crisis_payload = None

        result = NStrokeResult(
            pipeline_id=pipeline_id,
            locked_intent=locked_intent,
            strokes=strokes,
            final_verdict=final_verdict,
            satisfied=satisfied,
            total_strokes=len(strokes),
            model_escalations=model_escalations,
            healing_invocations=healing_invocations,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            crisis=crisis_payload,
            execution_mode="sync",
        )

        self._broadcast({
            "type": "n_stroke_complete",
            "pipeline_id": pipeline_id,
            "satisfied": result.satisfied,
            "final_verdict": result.final_verdict,
            "total_strokes": result.total_strokes,
            "model_escalations": result.model_escalations,
            "healing_invocations": result.healing_invocations,
            "latency_ms": result.latency_ms,
        })

        return result

    async def run_async(
        self,
        locked_intent: LockedIntent,
        pipeline_id: str | None = None,
        work_fn: Callable[[Envelope], Any] | None = None,
    ) -> NStrokeResult:
        """Async variant of run() using AsyncFluidExecutor for event-driven execution.

        Nodes fire the instant their individual dependencies resolve, eliminating
        wave-level stalls (25-40% lower latency on complex DAGs with wide fan-out).

        Falls back to wrapping the synchronous ``run()`` in a thread executor when
        no ``AsyncFluidExecutor`` is injected.
        """
        if self._async_fluid_executor is None:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.run(
                    locked_intent, pipeline_id=pipeline_id, work_fn=work_fn),
            )

        t0 = time.monotonic()
        pipeline_id = pipeline_id or f"nstroke-async-{uuid.uuid4().hex[:8]}"
        strokes: list[StrokeRecord] = []
        prior_verdict = ""
        node_fail_counts: dict[str, int] = {}
        healing_invocations = 0
        model_escalations = 0
        current_work_fn = work_fn if work_fn is not None else self._default_work_fn

        self._broadcast({
            "type": "n_stroke_start",
            "pipeline_id": pipeline_id,
            "intent": locked_intent.intent,
            "confidence": locked_intent.confidence,
            "max_strokes": self._max_strokes,
            "model_id": getattr(self, "_active_model", None),
            "mode": "async_fluid",
        })

        if locked_intent.confidence < AUTONOMOUS_CONFIDENCE_THRESHOLD:
            self._broadcast({
                "type": "consultation_recommended",
                "pipeline_id": pipeline_id,
                "intent": locked_intent.intent,
                "confidence": locked_intent.confidence,
                "threshold": AUTONOMOUS_CONFIDENCE_THRESHOLD,
                "reason": (
                    f"Confidence {locked_intent.confidence:.2f} is below the "
                    f"autonomous threshold {AUTONOMOUS_CONFIDENCE_THRESHOLD}. "
                    "Proceeding autonomously — user review suggested."
                ),
            })

        for stroke_num in range(1, self._max_strokes + 1):
            model_sel = self._model_selector.select(
                stroke=stroke_num,
                intent=locked_intent.intent,
                prior_verdict=prior_verdict,
            )
            if stroke_num > 1 and strokes:
                prev_tier = strokes[-1].model_selection.tier
                if model_sel.tier > prev_tier:
                    model_escalations += 1

            self._broadcast({
                "type": "model_selected",
                "pipeline_id": pipeline_id,
                "stroke": stroke_num,
                "model": model_sel.model,
                "vertex_model_id": model_sel.vertex_model_id,
                "tier": model_sel.tier,
                "rationale": model_sel.rationale,
            })

            healing_report: HealingReport | None = None
            nodes_needing_healing = [
                nid for nid, cnt in node_fail_counts.items()
                if cnt >= NODE_FAIL_THRESHOLD
            ]
            if nodes_needing_healing:
                last_error_map: dict[str, str] = {}
                if strokes:
                    for r in strokes[-1].execution_results:
                        if r.error:
                            canonical_key = r.mandate_id.rsplit("-", 1)[-1]
                            last_error_map[canonical_key] = r.error

                healing_report = self._ref_supervisor.heal(
                    failed_node_ids=nodes_needing_healing,
                    stroke=stroke_num,
                    intent=locked_intent.intent,
                    mcp=self._mcp,
                    booster=self._booster,
                    mandate_text=locked_intent.mandate_text,
                    last_error_map=last_error_map,
                )
                healing_invocations += 1

                self._broadcast({
                    "type": "healing_triggered",
                    "pipeline_id": pipeline_id,
                    "stroke": stroke_num,
                    "nodes_healed": healing_report.nodes_healed,
                    "healing_id": healing_report.healing_id,
                    "verdict": healing_report.verdict,
                })

                for nid in healing_report.nodes_healed:
                    node_fail_counts.pop(nid, None)
                    node_fail_counts.pop(nid.rsplit("-", 1)[-1], None)

                if healing_report.healed_work_fn is not None:
                    current_work_fn = healing_report.healed_work_fn

            prior_failure_signal = ""
            if prior_verdict in ("fail", "warn") and strokes:
                last_stroke = strokes[-1]
                failed_nodes = last_stroke.refinement.failed_nodes
                prior_failure_signal = (
                    f"[retry-signal stroke={stroke_num - 1}] "
                    f"model={last_stroke.model_selection.model}, "
                    f"verdict={prior_verdict}, "
                    f"failed_nodes={failed_nodes[:3]}, "
                    f"escalated_to={model_sel.model}. "
                    f"Reapproach with corrections."
                )

            stroke_record = await self._run_stroke_async(
                locked_intent=locked_intent,
                pipeline_id=pipeline_id,
                stroke_num=stroke_num,
                model_sel=model_sel,
                prior_failure_signal=prior_failure_signal,
                work_fn=current_work_fn,
                healing_report=healing_report,
            )
            strokes.append(stroke_record)

            for r in stroke_record.execution_results:
                if not r.success:
                    canonical = r.mandate_id.rsplit("-", 1)[-1]
                    node_fail_counts[canonical] = node_fail_counts.get(
                        canonical, 0) + 1

            prior_verdict = stroke_record.refinement.verdict

            self._broadcast({
                "type": "satisfaction_gate",
                "pipeline_id": pipeline_id,
                "stroke": stroke_num,
                "satisfied": stroke_record.satisfied,
                "verdict": prior_verdict,
                "model": model_sel.model,
                "total_strokes_so_far": stroke_num,
                "node_fail_counts": dict(node_fail_counts),
            })

            if stroke_record.satisfied:
                break

        last = strokes[-1] if strokes else None
        final_verdict = last.refinement.verdict if last else "fail"
        satisfied = last.satisfied if last else False

        if not satisfied:
            crisis_payload = self._synthesize_crisis(
                mandate_text=locked_intent.mandate_text,
                intent=locked_intent.intent,
                strokes=strokes,
            )
            self._broadcast({
                "type": "actionable_intervention",
                "pipeline_id": pipeline_id,
                "crisis": crisis_payload,
            })
        else:
            crisis_payload = None

        result = NStrokeResult(
            pipeline_id=pipeline_id,
            locked_intent=locked_intent,
            strokes=strokes,
            final_verdict=final_verdict,
            satisfied=satisfied,
            total_strokes=len(strokes),
            model_escalations=model_escalations,
            healing_invocations=healing_invocations,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            crisis=crisis_payload,
            execution_mode="async_fluid",
        )

        self._broadcast({
            "type": "n_stroke_complete",
            "pipeline_id": pipeline_id,
            "satisfied": result.satisfied,
            "final_verdict": result.final_verdict,
            "total_strokes": result.total_strokes,
            "model_escalations": result.model_escalations,
            "healing_invocations": result.healing_invocations,
            "latency_ms": result.latency_ms,
        })

        return result

    # ── Private: single stroke execution ──────────────────────────────────────

    def _run_stroke(
        self,
        locked_intent: LockedIntent,
        pipeline_id: str,
        stroke_num: int,
        model_sel: ModelSelection,
        prior_failure_signal: str,
        work_fn: Callable[[Envelope], Any],
        healing_report: HealingReport | None,
    ) -> StrokeRecord:
        t0 = time.monotonic()
        mandate_id = f"{pipeline_id}-s{stroke_num}"
        intent = locked_intent.intent

        # ── Pre-Flight Supervisor ─────────────────────────────────────────────
        route = _route_from_locked(locked_intent)
        # Enrich mandate text with retry signal + model context
        context_prefix = f"[model={model_sel.model} tier={model_sel.tier} stroke={stroke_num}]"
        if prior_failure_signal:
            route.mandate_text = (
                f"{context_prefix} {prior_failure_signal}\n\n"
                f"Original: {locked_intent.mandate_text}"
            )
        else:
            route.mandate_text = f"{context_prefix} {route.mandate_text}"

        preflight_jit = self._booster.fetch(
            route, vertex_model_id=model_sel.vertex_model_id)
        self._router.apply_jit_boost(route, preflight_jit.boosted_confidence)

        preflight_tribunal = self._tribunal.evaluate(Engram(
            slug=f"{mandate_id}-preflight",
            intent=intent,
            logic_body=locked_intent.mandate_text,
            domain="backend",
            mandate_level="L2",
        ))

        self._broadcast({
            "type": "preflight",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "model": model_sel.model,
            "jit_source": preflight_jit.source,
            "jit_signals": preflight_jit.signals[:3],
            "tribunal_passed": preflight_tribunal.passed,
            "boosted_confidence": preflight_jit.boosted_confidence,
        })

        # ── Process 1 — Catalyst (Meta-Architect DAG + scope + MCP inject) ──
        meta_plan = self._meta_architect.generate(route.mandate_text, intent)
        base_spec = self._meta_architect.to_topology_spec(meta_plan)
        dynamic_spec = [
            (
                f"{mandate_id}-{node_id}",
                [f"{mandate_id}-{dep}" for dep in deps],
            )
            for node_id, deps in base_spec
        ]

        if meta_plan.confidence_proof.proof_confidence < AUTONOMOUS_CONFIDENCE_THRESHOLD:
            self._broadcast({
                "type": "consultation_recommended",
                "pipeline_id": pipeline_id,
                "stroke": stroke_num,
                "confidence": meta_plan.confidence_proof.proof_confidence,
                "threshold": AUTONOMOUS_CONFIDENCE_THRESHOLD,
                "reason": (
                    "Meta-Architect proof below autonomy threshold; "
                    "using conservative fallback topology."
                ),
            })
            dynamic_spec = self._fallback_topology_spec(mandate_id)

        waves = self._sorter.sort(dynamic_spec)
        dag_nodes = [node_id for node_id, _ in dynamic_spec]
        node_specs: dict[str, dict[str, Any]] = {
            f"{mandate_id}-{node.node_id}": {
                "action_type": node.action_type,
                "cognitive_profile": node.cognitive_profile,
            }
            for node in meta_plan.execution_graph
        }
        for node_id, _ in dynamic_spec:
            if node_id not in node_specs:
                suffix = node_id.rsplit("-", 1)[-1]
                inferred_action = "validate" if suffix.startswith(
                    "validate") else suffix
                node_specs[node_id] = {
                    "action_type": inferred_action,
                    "cognitive_profile": None,
                }

        scope = self._scope.evaluate(waves, intent)

        # Inject MCP tool manifest
        mcp_tools = self._mcp.manifest()
        tool_names = [t.name for t in mcp_tools]

        self._broadcast({
            "type": "plan",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "waves": waves,
            "node_count": sum(len(wave) for wave in waves),
            "scope": scope.to_dict(),
            "mcp_tools": tool_names,
            "model": model_sel.model,
            "healing_applied": healing_report is not None,
            "meta_architect": meta_plan.to_dict(),
        })

        # ── Mid-Flight Supervisor ─────────────────────────────────────────────
        midflight_jit = self._booster.fetch(
            route, vertex_model_id=model_sel.vertex_model_id)
        self._tribunal.evaluate(Engram(
            slug=f"{mandate_id}-midflight",
            intent=intent,
            logic_body=f"midflight check: {locked_intent.mandate_text[:200]}",
            domain="backend",
            mandate_level="L2",
        ))

        self._broadcast({
            "type": "midflight",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "jit_signals": midflight_jit.signals[:2],
            "scope_strategy": scope.strategy,
            "model": model_sel.model,
        })

        # ── Phase 1: Blueprint — discovery nodes only ─────────────────────────
        # Discovery nodes document understanding; no state-changing operations.
        blueprint_actions = {"deep_research",
                             "audit_wave", "design_wave", "ux_eval"}
        blueprint_node_ids = [
            node_id
            for node_id in dag_nodes
            if (
                node_specs.get(node_id, None)
                and node_specs[node_id]["action_type"] in blueprint_actions
            )
        ]
        self._broadcast({
            "type": "blueprint_phase",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "nodes": blueprint_node_ids,
        })

        # ── Phase 2: Dry-Run — analyse + implement (staged, not committed) ────
        dry_run_actions = {"ingest", "analyse", "implement"}
        dry_run_node_ids = [
            node_id
            for node_id in dag_nodes
            if (
                node_specs.get(node_id, None)
                and node_specs[node_id]["action_type"] in dry_run_actions
            )
        ]
        self._broadcast({
            "type": "dry_run_phase",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "nodes": dry_run_node_ids,
        })

        # ── Process 2 — Crucible (JITExecutor fan-out, all nodes) ────────────
        # Upgrade the default symbolic work_fn to a real LLM-powered executor
        # when Vertex AI or Gemini is available (falls back automatically).
        effective_work_fn = work_fn
        if work_fn is NStrokeEngine._default_work_fn:
            effective_work_fn = make_live_work_fn(
                mandate_text=locked_intent.mandate_text,
                intent=intent,
                jit_signals=preflight_jit.signals,
                vertex_model_id=model_sel.vertex_model_id,
            )
        inferred_file_path = _infer_workspace_file_target(
            locked_intent.mandate_text)

        node_model_map: dict[str, str] = {}
        node_provider_map: dict[str, str] = {}
        node_bid_results: dict[str, dict[str, Any]] = {}
        for node_id in dag_nodes:
            spec_info = node_specs.get(node_id)
            profile = spec_info.get("cognitive_profile") if spec_info else None
            action_type = (spec_info or {}).get("action_type", "reasoning")

            # JIT 16D bidding: score all registry models per node
            if self._bidder is not None:
                _task_map = {"implement": "code", "analyse": "reasoning",
                             "design_wave": "synthesis", "audit_wave": "reasoning",
                             "validate": "speed", "ingest": "speed"}
                task_type = _task_map.get(action_type, "reasoning")
                bid = self._bidder.bid(
                    node_id=node_id,
                    task_type=task_type,
                    estimated_tokens=2000,
                    min_stability=_cfg.bidder_min_stability,
                )
                node_model_map[node_id] = bid.winning_model
                node_provider_map[node_id] = self._garden.source_for(
                    bid.winning_model)
                node_bid_results[node_id] = bid.to_dict()
            elif profile is None:
                node_model_map[node_id] = model_sel.model
                node_provider_map[node_id] = self._garden.source_for(
                    model_sel.model)
            else:
                node_model = self._garden.get_tier_model(
                    tier=profile.minimum_tier,
                    intent=intent,
                    primary_need=profile.primary_need,
                    lock_model=profile.lock_model,
                )
                node_model_map[node_id] = node_model
                node_provider_map[node_id] = self._garden.source_for(
                    node_model)

        envelopes = [
            Envelope(
                mandate_id=node_id,
                intent=intent,
                domain="backend",
                metadata={
                    "model": model_sel.model,
                    "node_model": node_model_map.get(node_id, model_sel.model),
                    "node_model_provider": node_provider_map.get(node_id, "vertex"),
                    "vertex_model_id": model_sel.vertex_model_id,
                    "model_tier": model_sel.tier,
                    "mcp_tools": tool_names,
                    "stroke": stroke_num,
                    "pipeline_id": pipeline_id,
                    "healing_applied": healing_report is not None,
                    "file_path": inferred_file_path,
                    "target": inferred_file_path,
                    # Node-level phase tagging for downstream handlers
                    "phase": (
                        PHASE_BLUEPRINT if node_id in blueprint_node_ids
                        else PHASE_DRY_RUN if node_id in dry_run_node_ids
                        else PHASE_EXECUTE
                    ),
                },
            )
            for node_id in dag_nodes
        ]

        dependency_map = {node_id: deps for node_id, deps in dynamic_spec}

        execution_results = self._executor.fan_out_dag(
            effective_work_fn,
            envelopes,
            dependency_map,
            max_workers=scope.recommended_workers,
        )

        self._broadcast({
            "type": "execution",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "results": [r.to_dict() for r in execution_results],
            "model": model_sel.model,
        })

        # ── Simulation Gate — evaluate dry-run output before marking pass ────
        sim_gate = SimulationGate()
        dry_run_exec = [
            r for r in execution_results if r.mandate_id in dry_run_node_ids
        ]
        sim_passed, sim_failures = sim_gate.evaluate(
            blueprint_nodes=blueprint_node_ids,
            dry_run_results=dry_run_exec,
            intent=intent,
        )

        if sim_failures:
            self._broadcast({
                "type": "simulation_gate",
                "pipeline_id": pipeline_id,
                "stroke": stroke_num,
                "passed": sim_passed,
                "failures": sim_failures,
            })

        self._broadcast({
            "type": "execute_phase",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "sim_gate_passed": sim_passed,
            "nodes": [n for n in dag_nodes if n not in blueprint_node_ids + dry_run_node_ids],
        })

        divergence_metrics = self._build_divergence_metrics(
            execution_results=execution_results,
            node_provider_map=node_provider_map,
            node_specs=node_specs,
        )

        # ── Satisfaction Gate (RefinementLoop) ────────────────────────────────
        refinement = self._refine.evaluate(
            execution_results, iteration=stroke_num)
        satisfied = refinement.verdict == "pass" and sim_passed

        confidence_proof = dict(meta_plan.confidence_proof.to_dict())
        confidence_proof["post_execution_divergence"] = divergence_metrics.get(
            "divergence_score", 0.0)
        confidence_proof["simulation_gate_passed"] = sim_passed

        return StrokeRecord(
            stroke=stroke_num,
            model_selection=model_sel,
            preflight_jit=preflight_jit,
            preflight_tribunal=preflight_tribunal,
            plan=waves,
            scope=scope,
            mcp_tools_injected=tool_names,
            midflight_jit=midflight_jit,
            execution_results=execution_results,
            refinement=refinement,
            healing_report=healing_report,
            satisfied=satisfied,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            blueprint_nodes=blueprint_node_ids,
            dry_run_passed=sim_passed,
            simulation_gate_failures=sim_failures,
            active_phase=PHASE_EXECUTE,
            confidence_proof=confidence_proof,
            divergence_metrics=divergence_metrics,
        )

    async def _run_stroke_async(
        self,
        locked_intent: LockedIntent,
        pipeline_id: str,
        stroke_num: int,
        model_sel: ModelSelection,
        prior_failure_signal: str,
        work_fn: Callable[[Envelope], Any],
        healing_report: HealingReport | None,
    ) -> StrokeRecord:
        """Async variant of _run_stroke() that uses AsyncFluidExecutor.fan_out_dag_async().

        Identical to _run_stroke() except the Process 2 execution block fires
        each DAG node the instant its individual dependencies resolve, rather than
        waiting for full waves to complete.  This eliminates straggler-penalty
        idle time in complex topologies.
        """
        t0 = time.monotonic()
        mandate_id = f"{pipeline_id}-s{stroke_num}"
        intent = locked_intent.intent

        # ── Pre-Flight Supervisor ─────────────────────────────────────────────
        route = _route_from_locked(locked_intent)
        context_prefix = f"[model={model_sel.model} tier={model_sel.tier} stroke={stroke_num}]"
        if prior_failure_signal:
            route.mandate_text = (
                f"{context_prefix} {prior_failure_signal}\n\n"
                f"Original: {locked_intent.mandate_text}"
            )
        else:
            route.mandate_text = f"{context_prefix} {route.mandate_text}"

        preflight_jit = self._booster.fetch(
            route, vertex_model_id=model_sel.vertex_model_id)
        self._router.apply_jit_boost(route, preflight_jit.boosted_confidence)

        preflight_tribunal = self._tribunal.evaluate(Engram(
            slug=f"{mandate_id}-preflight",
            intent=intent,
            logic_body=locked_intent.mandate_text,
            domain="backend",
            mandate_level="L2",
        ))

        self._broadcast({
            "type": "preflight",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "model": model_sel.model,
            "jit_source": preflight_jit.source,
            "jit_signals": preflight_jit.signals[:3],
            "tribunal_passed": preflight_tribunal.passed,
            "boosted_confidence": preflight_jit.boosted_confidence,
        })

        # ── Process 1 — Catalyst ─────────────────────────────────────────────
        meta_plan = self._meta_architect.generate(route.mandate_text, intent)
        base_spec = self._meta_architect.to_topology_spec(meta_plan)
        dynamic_spec = [
            (f"{mandate_id}-{node_id}",
             [f"{mandate_id}-{dep}" for dep in deps])
            for node_id, deps in base_spec
        ]

        if meta_plan.confidence_proof.proof_confidence < AUTONOMOUS_CONFIDENCE_THRESHOLD:
            self._broadcast({
                "type": "consultation_recommended",
                "pipeline_id": pipeline_id,
                "stroke": stroke_num,
                "confidence": meta_plan.confidence_proof.proof_confidence,
                "threshold": AUTONOMOUS_CONFIDENCE_THRESHOLD,
                "reason": (
                    "Meta-Architect proof below autonomy threshold; "
                    "using conservative fallback topology."
                ),
            })
            dynamic_spec = self._fallback_topology_spec(mandate_id)

        waves = self._sorter.sort(dynamic_spec)
        dag_nodes = [node_id for node_id, _ in dynamic_spec]
        node_specs: dict[str, dict[str, Any]] = {
            f"{mandate_id}-{node.node_id}": {
                "action_type": node.action_type,
                "cognitive_profile": node.cognitive_profile,
            }
            for node in meta_plan.execution_graph
        }
        for node_id, _ in dynamic_spec:
            if node_id not in node_specs:
                suffix = node_id.rsplit("-", 1)[-1]
                inferred_action = "validate" if suffix.startswith(
                    "validate") else suffix
                node_specs[node_id] = {
                    "action_type": inferred_action, "cognitive_profile": None}

        scope = self._scope.evaluate(waves, intent)

        mcp_tools = self._mcp.manifest()
        tool_names = [t.name for t in mcp_tools]

        self._broadcast({
            "type": "plan",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "waves": waves,
            "node_count": sum(len(wave) for wave in waves),
            "scope": scope.to_dict(),
            "mcp_tools": tool_names,
            "model": model_sel.model,
            "healing_applied": healing_report is not None,
            "meta_architect": meta_plan.to_dict(),
        })

        # ── Mid-Flight Supervisor ─────────────────────────────────────────────
        midflight_jit = self._booster.fetch(
            route, vertex_model_id=model_sel.vertex_model_id)
        self._tribunal.evaluate(Engram(
            slug=f"{mandate_id}-midflight",
            intent=intent,
            logic_body=f"midflight check: {locked_intent.mandate_text[:200]}",
            domain="backend",
            mandate_level="L2",
        ))

        self._broadcast({
            "type": "midflight",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "jit_signals": midflight_jit.signals[:2],
            "scope_strategy": scope.strategy,
            "model": model_sel.model,
        })

        # ── Phase 1: Blueprint ────────────────────────────────────────────────
        blueprint_actions = {"deep_research",
                             "audit_wave", "design_wave", "ux_eval"}
        blueprint_node_ids = [
            node_id for node_id in dag_nodes
            if node_specs.get(node_id) and node_specs[node_id]["action_type"] in blueprint_actions
        ]
        self._broadcast({
            "type": "blueprint_phase",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "nodes": blueprint_node_ids,
        })

        # ── Phase 2: Dry-Run ──────────────────────────────────────────────────
        dry_run_actions = {"ingest", "analyse", "implement"}
        dry_run_node_ids = [
            node_id for node_id in dag_nodes
            if node_specs.get(node_id) and node_specs[node_id]["action_type"] in dry_run_actions
        ]
        self._broadcast({
            "type": "dry_run_phase",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "nodes": dry_run_node_ids,
        })

        # ── Process 2 — Crucible (AsyncFluidExecutor, event-driven) ──────────
        effective_work_fn = work_fn
        if work_fn is NStrokeEngine._default_work_fn:
            effective_work_fn = make_live_work_fn(
                mandate_text=locked_intent.mandate_text,
                intent=intent,
                jit_signals=preflight_jit.signals,
                vertex_model_id=model_sel.vertex_model_id,
            )
        inferred_file_path = _infer_workspace_file_target(
            locked_intent.mandate_text)

        node_model_map: dict[str, str] = {}
        node_provider_map: dict[str, str] = {}
        node_bid_results: dict[str, dict[str, Any]] = {}
        for node_id in dag_nodes:
            spec_info = node_specs.get(node_id)
            profile = spec_info.get("cognitive_profile") if spec_info else None
            action_type = (spec_info or {}).get("action_type", "reasoning")

            if self._bidder is not None:
                _task_map = {"implement": "code", "analyse": "reasoning",
                             "design_wave": "synthesis", "audit_wave": "reasoning",
                             "validate": "speed", "ingest": "speed"}
                task_type = _task_map.get(action_type, "reasoning")
                bid = self._bidder.bid(
                    node_id=node_id,
                    task_type=task_type,
                    estimated_tokens=2000,
                    min_stability=_cfg.bidder_min_stability,
                )
                node_model_map[node_id] = bid.winning_model
                node_provider_map[node_id] = self._garden.source_for(
                    bid.winning_model)
                node_bid_results[node_id] = bid.to_dict()
            elif profile is None:
                node_model_map[node_id] = model_sel.model
                node_provider_map[node_id] = self._garden.source_for(
                    model_sel.model)
            else:
                node_model = self._garden.get_tier_model(
                    tier=profile.minimum_tier,
                    intent=intent,
                    primary_need=profile.primary_need,
                    lock_model=profile.lock_model,
                )
                node_model_map[node_id] = node_model
                node_provider_map[node_id] = self._garden.source_for(
                    node_model)

        envelopes = [
            Envelope(
                mandate_id=node_id,
                intent=intent,
                domain="backend",
                metadata={
                    "model": model_sel.model,
                    "node_model": node_model_map.get(node_id, model_sel.model),
                    "node_model_provider": node_provider_map.get(node_id, "vertex"),
                    "vertex_model_id": model_sel.vertex_model_id,
                    "model_tier": model_sel.tier,
                    "mcp_tools": tool_names,
                    "stroke": stroke_num,
                    "pipeline_id": pipeline_id,
                    "healing_applied": healing_report is not None,
                    "file_path": inferred_file_path,
                    "target": inferred_file_path,
                    "phase": (
                        PHASE_BLUEPRINT if node_id in blueprint_node_ids
                        else PHASE_DRY_RUN if node_id in dry_run_node_ids
                        else PHASE_EXECUTE
                    ),
                },
            )
            for node_id in dag_nodes
        ]

        dependency_map = {node_id: deps for node_id, deps in dynamic_spec}

        # Build AsyncEnvelopes (structurally identical to Envelope)
        async_envelopes = [
            AsyncEnvelope(
                mandate_id=e.mandate_id,
                intent=e.intent,
                domain=e.domain,
                metadata=e.metadata,
            )
            for e in envelopes
        ]

        # Wrap the sync work_fn to be awaitable (runs in thread pool)
        _wfn = effective_work_fn  # capture to avoid late-binding

        async def _async_work_wrapper(env: AsyncEnvelope) -> Any:
            loop = asyncio.get_event_loop()
            sync_env = Envelope(
                mandate_id=env.mandate_id,
                intent=env.intent,
                domain=env.domain,
                metadata=env.metadata,
            )
            return await loop.run_in_executor(None, _wfn, sync_env)

        assert self._async_fluid_executor is not None  # guaranteed by run_async
        async_results: list[AsyncExecutionResult] = (
            await self._async_fluid_executor.fan_out_dag_async(
                _async_work_wrapper,
                async_envelopes,
                dependency_map,
                max_concurrent=scope.recommended_workers,
            )
        )

        execution_results = [
            ExecutionResult(
                mandate_id=r.mandate_id,
                success=r.success,
                output=r.output,
                latency_ms=r.latency_ms,
                error=r.error,
            )
            for r in async_results
        ]

        self._broadcast({
            "type": "execution",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "results": [r.to_dict() for r in execution_results],
            "model": model_sel.model,
            "execution_mode": "async_fluid",
        })

        # ── Simulation Gate ───────────────────────────────────────────────────
        sim_gate = SimulationGate()
        dry_run_exec = [
            r for r in execution_results if r.mandate_id in dry_run_node_ids]
        sim_passed, sim_failures = sim_gate.evaluate(
            blueprint_nodes=blueprint_node_ids,
            dry_run_results=dry_run_exec,
            intent=intent,
        )

        if sim_failures:
            self._broadcast({
                "type": "simulation_gate",
                "pipeline_id": pipeline_id,
                "stroke": stroke_num,
                "passed": sim_passed,
                "failures": sim_failures,
            })

        self._broadcast({
            "type": "execute_phase",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "sim_gate_passed": sim_passed,
            "nodes": [n for n in dag_nodes if n not in blueprint_node_ids + dry_run_node_ids],
        })

        divergence_metrics = self._build_divergence_metrics(
            execution_results=execution_results,
            node_provider_map=node_provider_map,
            node_specs=node_specs,
        )

        # ── Satisfaction Gate ─────────────────────────────────────────────────
        refinement = self._refine.evaluate(
            execution_results, iteration=stroke_num)
        satisfied = refinement.verdict == "pass" and sim_passed

        confidence_proof = dict(meta_plan.confidence_proof.to_dict())
        confidence_proof["post_execution_divergence"] = divergence_metrics.get(
            "divergence_score", 0.0)
        confidence_proof["simulation_gate_passed"] = sim_passed

        return StrokeRecord(
            stroke=stroke_num,
            model_selection=model_sel,
            preflight_jit=preflight_jit,
            preflight_tribunal=preflight_tribunal,
            plan=waves,
            scope=scope,
            mcp_tools_injected=tool_names,
            midflight_jit=midflight_jit,
            execution_results=execution_results,
            refinement=refinement,
            healing_report=healing_report,
            satisfied=satisfied,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            blueprint_nodes=blueprint_node_ids,
            dry_run_passed=sim_passed,
            simulation_gate_failures=sim_failures,
            active_phase=PHASE_EXECUTE,
            confidence_proof=confidence_proof,
            divergence_metrics=divergence_metrics,
        )

    @staticmethod
    def _fallback_topology_spec(mandate_id: str) -> list[tuple[str, list[str]]]:
        """Conservative static topology used when dynamic proof is below threshold."""
        return [
            (f"{mandate_id}-audit_wave", []),
            (f"{mandate_id}-design_wave", [f"{mandate_id}-audit_wave"]),
            (f"{mandate_id}-ux_eval", [f"{mandate_id}-audit_wave"]),
            (f"{mandate_id}-ingest",
             [f"{mandate_id}-design_wave", f"{mandate_id}-ux_eval"]),
            (f"{mandate_id}-analyse", [f"{mandate_id}-ingest"]),
            (f"{mandate_id}-implement", [f"{mandate_id}-analyse"]),
            (f"{mandate_id}-validate_primary", [f"{mandate_id}-implement"]),
            (f"{mandate_id}-validate_divergent", [f"{mandate_id}-implement"]),
            (f"{mandate_id}-emit",
             [f"{mandate_id}-validate_primary", f"{mandate_id}-validate_divergent"]),
        ]

    @staticmethod
    def _build_divergence_metrics(
        execution_results: list[ExecutionResult],
        node_provider_map: dict[str, str],
        node_specs: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute validation-divergence coverage for redundancy/reinforcement."""
        providers_used = {
            node_provider_map.get(result.mandate_id, "unknown")
            for result in execution_results
            if result.success
        }

        validation_nodes = [
            result
            for result in execution_results
            if node_specs.get(result.mandate_id, {}).get("action_type", "") == "validate"
        ]
        successful_validations = [r for r in validation_nodes if r.success]
        validation_ratio = (
            len(successful_validations) / len(validation_nodes)
            if validation_nodes else 0.0
        )

        provider_divergence = 1.0 if len(providers_used) >= 2 else 0.6
        divergence_score = min(
            1.0, 0.5 * validation_ratio + 0.5 * provider_divergence)

        return {
            "providers_used": sorted(providers_used),
            "provider_count": len(providers_used),
            "validation_nodes": len(validation_nodes),
            "validation_successes": len(successful_validations),
            "divergence_score": round(divergence_score, 3),
        }

    # ── Default work function ─────────────────────────────────────────────────

    @staticmethod
    def _default_work_fn(env: Envelope) -> dict[str, Any]:
        """Symbolic execution: always succeeds; outputs model + MCP context."""
        return {
            "node": env.mandate_id,
            "intent": env.intent,
            "model": env.metadata.get("model", "unknown"),
            "model_tier": env.metadata.get("model_tier", 1),
            "mcp_tools": env.metadata.get("mcp_tools", []),
            "stroke": env.metadata.get("stroke", 1),
            "healing_applied": env.metadata.get("healing_applied", False),
            "status": "executed",
        }

    # ── Cognitive Swarm: 16D synthesis ────────────────────────────────────────

    def _synthesize_swarm_output(
        self,
        swarm_results: list[ExecutionResult],
        mandate: str,
    ) -> str:
        """Score each swarm branch via Validator16D and return the best output.

        Each divergent agent's output is scored across 16 quality dimensions.
        If the top composite score meets the autonomous confidence threshold the
        winning branch is returned directly.  Otherwise, ``_trigger_swarm_reconciliation``
        is invoked to merge the top proposals and attempt another convergence cycle.

        Args:
            swarm_results: ExecutionResults from Wave 2 parallel swarm execution.
            mandate:       Original mandate text (used for scoring context).

        Returns:
            The synthesised SOTA output string.
        """
        scored_proposals: list[dict[str, Any]] = []
        for result in swarm_results:
            raw_output = ""
            if isinstance(result.output, dict):
                raw_output = str(result.output.get("output", ""))
            elif result.output is not None:
                raw_output = str(result.output)

            v16d = self._validator_16d.validate(
                mandate_id=result.mandate_id,
                intent="BUILD",
                code_snippet=raw_output[:2000] if raw_output else None,
            )
            scored_proposals.append({
                "agent": result.mandate_id,
                "output": raw_output,
                "score": v16d.composite_score,
                "gate_pass": v16d.autonomous_gate_pass,
                "critical_failures": v16d.critical_failures,
            })

        scored_proposals.sort(key=lambda x: x["score"], reverse=True)

        self._broadcast({
            "type": "swarm_synthesis",
            "scores": [
                {"agent": p["agent"], "score": round(p["score"], 4)}
                for p in scored_proposals
            ],
        })

        top = scored_proposals[0] if scored_proposals else {}
        if top.get("score", 0.0) >= AUTONOMOUS_CONFIDENCE_THRESHOLD:
            return str(top.get("output", ""))
        return self._trigger_swarm_reconciliation(scored_proposals)

    def _trigger_swarm_reconciliation(
        self,
        scored_proposals: list[dict[str, Any]],
    ) -> str:
        """Merge the top-scoring swarm branches when no single winner meets the bar.

        Takes the two highest-scoring proposals and emits a synthesis directive
        so that the RefinementSupervisor can incorporate both in the next healing
        stroke.  Returns a structured reconciliation note rather than raw code.
        """
        if not scored_proposals:
            return "[swarm-reconciliation] No proposals to merge."

        top_two = scored_proposals[:2]
        summary_lines = ["[swarm-reconciliation] Merging top branches:"]
        for proposal in top_two:
            score = round(proposal.get("score", 0.0), 4)
            agent = proposal.get("agent", "unknown")
            failures = proposal.get("critical_failures", [])
            summary_lines.append(
                f"  • {agent} score={score} "
                f"critical_failures={failures[:2] if failures else 'none'}"
            )
        merged_output = "\n".join(summary_lines)

        self._broadcast({
            "type": "swarm_reconciliation",
            "top_agents": [p["agent"] for p in top_two],
            "reconciliation_note": merged_output,
        })

        return merged_output

    # ── No Dead Ends: crisis synthesis ────────────────────────────────────────

    def _synthesize_crisis(
        self,
        mandate_text: str,
        intent: str,
        strokes: list[StrokeRecord],
    ) -> dict[str, Any]:
        """Generate a structured crisis payload with actionable recovery options.

        Attempts a Gemini API call to produce a human-readable summary,
        a technical root-cause description, and 2-3 concrete resolution
        options the user can click in the UI.

        Falls back to intent-based static options when the API is unavailable.
        """
        import json as _json

        # Collect failed node names for context
        failed_nodes: list[str] = []
        for s in strokes[-3:]:  # last 3 strokes for brevity
            for r in s.execution_results:
                if not r.success:
                    canonical = r.mandate_id.rsplit("-", 1)[-1]
                    if canonical not in failed_nodes:
                        failed_nodes.append(canonical)

        # ── Try Gemini API for rich crisis synthesis ──────────────────────────
        try:
            # type: ignore[attr-defined]
            from engine.config import _gemini_client, GEMINI_MODEL
            if _gemini_client is not None:
                system_prompt = (
                    "You are the TooLoo Crisis Synthesiser. "
                    "The autonomous pipeline has exhausted all retries without success. "
                    "Your job: produce a structured JSON object (no markdown, no prose) "
                    "that gives the user clear next steps. "
                    "Schema: {\"human_summary\": str, \"technical_blocker\": str, "
                    "\"actionable_choices\": [str, str, str]} "
                    "Each actionable_choice must be a complete, submittable mandate "
                    "that a user can paste directly into the chat input to unblock the system."
                )
                user_prompt = (
                    f"Original mandate: {mandate_text[:400]}\n"
                    f"Intent: {intent}\n"
                    f"Failed nodes: {', '.join(failed_nodes[:5]) or 'unknown'}\n"
                    f"Strokes exhausted: {len(strokes)}\n\n"
                    "Synthesise the crisis JSON now."
                )
                resp = _gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=f"{system_prompt}\n\n{user_prompt}",
                )
                raw = (resp.text or "").strip()
                # Strip markdown code fences if present
                raw = raw.removeprefix("```json").removeprefix(
                    "```").removesuffix("```").strip()
                parsed = _json.loads(raw)
                if (
                    isinstance(parsed, dict)
                    and "human_summary" in parsed
                    and "actionable_choices" in parsed
                ):
                    return parsed
        except Exception:
            pass  # fall through to static fallback

        # ── Static fallback: intent-specific recovery choices ─────────────────
        _STATIC_CHOICES: dict[str, list[str]] = {
            "BUILD": [
                f"Scope this down: build only the minimal working skeleton of «{mandate_text[:60]}»",
                f"Debug first: diagnose what is preventing the build from completing",
                "Audit dependencies and verify all required packages are installed",
            ],
            "DEBUG": [
                f"Provide the full error traceback for «{mandate_text[:60]}»",
                "Run: python -m pytest tests/ -x -q --timeout=30 to isolate the failure",
                "Audit the last change to identify the regression source",
            ],
            "DESIGN": [
                f"Simplify the scope: design a single component for «{mandate_text[:60]}»",
                "Start with a Tailwind-only static HTML mockup, no JS",
                "Explain the design requirements in plain English so I can rephrase the mandate",
            ],
            "AUDIT": [
                "Run: python -m pytest tests/ -v to see which tests are failing",
                f"Audit a single module: audit only the {failed_nodes[0] if failed_nodes else 'router'} component",
                "Check for missing environment variables or misconfigured .env",
            ],
        }
        choices = _STATIC_CHOICES.get(
            intent,
            [
                f"Rephrase the mandate with more specific details about «{mandate_text[:60]}»",
                "Break the task into smaller steps and tackle the first one only",
                "Provide context files or error messages to help diagnose the blocker",
            ],
        )
        return {
            "human_summary": (
                f"The pipeline exhausted {len(strokes)} strokes without satisfying "
                f"the «{intent}» mandate. "
                f"Last failing nodes: {', '.join(failed_nodes[:3]) or 'see logs'}."
            ),
            "technical_blocker": (
                f"Intent={intent}; failed_nodes={failed_nodes[:5]}; "
                f"strokes={len(strokes)}/{self._max_strokes}; "
                "all healing prescriptions exhausted."
            ),
            "actionable_choices": choices[:3],
        }
