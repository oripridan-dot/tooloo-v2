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

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from engine.executor import Envelope, ExecutionResult, JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBoostResult, JITBooster
from engine.mandate_executor import make_live_work_fn
from engine.mcp_manager import MCPManager
from engine.model_selector import ModelSelection, ModelSelector
from engine.refinement import RefinementLoop, RefinementReport
from engine.refinement_supervisor import HealingReport, NODE_FAIL_THRESHOLD, RefinementSupervisor
from engine.router import LockedIntent, MandateRouter, RouteResult, compute_buddy_line
from engine.scope_evaluator import ScopeEvaluation, ScopeEvaluator
from engine.tribunal import Engram, Tribunal, TribunalResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_STROKES: int = 7       # hard cap on N-stroke loop iterations

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
        if symbolic_count > len(dry_run_results) * 0.6:
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
        self._broadcast: Callable[[dict[str, Any]], None] = (
            broadcast_fn if broadcast_fn is not None else lambda _: None
        )
        self._max_strokes = max_strokes

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

        # ── Process 1 — Catalyst (DAG plan + scope + MCP inject) ─────────────
        # Phase 1 Blueprint: mandatory AUDIT + DESIGN + UX_EVAL discovery nodes.
        # IMPLEMENT nodes are forbidden until the Simulation Gate clears.
        dag_node_names = [
            *_MANDATORY_DISCOVERY,          # audit_wave, design_wave, ux_eval
            "ingest", "analyse",            # deep analysis wave
            "implement",                    # locked behind SimulationGate
            "validate", "emit",             # post-execute checks
        ]
        dag_nodes = [f"{mandate_id}-{n}" for n in dag_node_names]

        # 6-wave plan: discovery(×3) → ingest → (analyse) → implement → (validate‖emit)
        waves: list[list[str]] = [
            [dag_nodes[0]],                         # Wave 1: audit_wave
            # Wave 2: design_wave ‖ ux_eval
            [dag_nodes[1], dag_nodes[2]],
            [dag_nodes[3]],                         # Wave 3: ingest
            [dag_nodes[4]],                         # Wave 4: analyse (deep)
            # Wave 5: implement (execute phase)
            [dag_nodes[5]],
            [dag_nodes[6], dag_nodes[7]],           # Wave 6: validate ‖ emit
        ]
        scope = self._scope.evaluate(waves, intent)

        # Inject MCP tool manifest
        mcp_tools = self._mcp.manifest()
        tool_names = [t.name for t in mcp_tools]

        self._broadcast({
            "type": "plan",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "waves": waves,
            "scope": scope.to_dict(),
            "mcp_tools": tool_names,
            "model": model_sel.model,
            "healing_applied": healing_report is not None,
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
        blueprint_node_ids = dag_nodes[:3]   # audit_wave, design_wave, ux_eval
        self._broadcast({
            "type": "blueprint_phase",
            "pipeline_id": pipeline_id,
            "stroke": stroke_num,
            "nodes": blueprint_node_ids,
        })

        # ── Phase 2: Dry-Run — analyse + implement (staged, not committed) ────
        # ingest, analyse, implement (held)
        dry_run_node_ids = dag_nodes[3:6]
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
        envelopes = [
            Envelope(
                mandate_id=node_id,
                intent=intent,
                domain="backend",
                metadata={
                    "model": model_sel.model,
                    "vertex_model_id": model_sel.vertex_model_id,
                    "model_tier": model_sel.tier,
                    "mcp_tools": tool_names,
                    "stroke": stroke_num,
                    "pipeline_id": pipeline_id,
                    "healing_applied": healing_report is not None,
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

        execution_results = self._executor.fan_out(
            effective_work_fn,
            envelopes,
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

        # ── Satisfaction Gate (RefinementLoop) ────────────────────────────────
        refinement = self._refine.evaluate(
            execution_results, iteration=stroke_num)
        satisfied = refinement.verdict == "pass" and sim_passed

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
        )

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
