# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.pipeline.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable

from engine.router import LockedIntent
from engine.executor import Envelope
from engine.cognitive import SystemAgency, ExecutionIntent
from engine.pipeline_types import NStrokeResult, StrokeRecord
from engine.model_selector import ModelSelection
from engine.tribunal import TribunalVerdict, TribunalResult
from engine.jit_booster import JITBoostResult
from engine.scope_evaluator import ScopeEvaluation
from engine.executor import ExecutionResult
from engine.refinement import RefinementReport
from engine.auto_fixer import AutoFixLoop

logger = logging.getLogger(__name__)

# PURE Architecture - Core Constants
MAX_STROKES = 7

class NStrokeEngine:
    """
    PURE Orchestration Bridge.
    Replaces the legacy N-Stroke heuristic engine with a unified (C+I) x E = EM loop.
    """

    def __init__(self, max_strokes: int = 7):
        self._max_strokes = max_strokes

    def _broadcast(self, payload: dict[str, Any]):
        """Legacy broadcast port for UI events."""
        # In a real system, this would hook into the SSE event bus.
        logger.debug(f"PURE Broadcast: {payload}")

    async def run(
        self,
        locked_intent: LockedIntent,
        pipeline_id: str | None = None,
        work_fn: Callable[[Envelope], Any] | None = None,
        simulation: bool = False,
        use_cognitive_middleware: bool = True,
    ) -> NStrokeResult:
        """
        PURE Execution Loop.
        Orchestrates mandate execution via the PureOrchestrator.
        """
        from engine.orchestrator import PureOrchestrator
        
        t0 = time.monotonic()
        pipeline_id = pipeline_id or f"pure-{uuid.uuid4().hex[:8]}"
        
        self._broadcast({
            "type": "n_stroke_start",
            "pipeline_id": pipeline_id,
            "intent": locked_intent.intent,
            "mode": "PURE_ORCHESTRATION"
        })

        # --- 1. Orchestration ---
        orchestrator = PureOrchestrator()
        context = {
            "intent": locked_intent.intent,
            "mandate_text": locked_intent.mandate_text,
            "confidence": locked_intent.confidence
        }
        
        # Execute the unified PURE loop
        engram = await orchestrator.execute_mandate(locked_intent.mandate_text, context)
        
        # --- 2. Result Mapping (Backwards Compatibility) ---
        satisfied = engram.em_actual.to_vec()[0] > 0.5 if engram.em_actual else False
        
        final_stroke = StrokeRecord(
            stroke=1,
            model_selection=ModelSelection(model="PURE-SOTA", tier=5, rationale="Matrix-driven orchestration"),
            preflight_jit=JITBoostResult(success=True, instructions="PURE"),
            preflight_tribunal=TribunalResult(slug=engram.context.what, delta=0.0, verdict=TribunalVerdict.STABLE_SUCCESS),
            plan=[[engram.context.what]],
            mcp_tools_injected=[],
            scope=ScopeEvaluation(tokens=0, files=0, complexity=0.1),
            midflight_jit=JITBoostResult(success=True, instructions="PURE"),
            execution_results=[ExecutionResult(mandate_id=engram.context.what, success=satisfied, output={}, latency=(time.monotonic()-t0))],
            refinement=RefinementReport(verdict="pass" if satisfied else "fail", failed_nodes=[]),
            healing_report=None,
            satisfied=satisfied,
            latency_ms=(time.monotonic() - t0) * 1000.0,
            divergence_metrics={"delta": getattr(engram.metadata.get("tribunal_result"), "delta", 0.0)}
        )

        # Tier-3: Autonomous Healing Case
        if not satisfied:
            logger.warning("PURE Execution Failure. Triggering Autonomous Healing Stroke.")
            fixer = AutoFixLoop()
            # Analyze and attempt repair on the failed mandate
            await fixer.analyze_and_fix(engram.context.what)
            # Mark the result as having invoked healing
            healing_invocations = 1
        else:
            healing_invocations = 0

        result = NStrokeResult(
            pipeline_id=pipeline_id,
            locked_intent=locked_intent,
            strokes=[final_stroke],
            final_verdict="pass" if satisfied else "fail",
            satisfied=satisfied,
            total_strokes=1,
            model_escalations=0,
            healing_invocations=healing_invocations,
            latency_ms=(time.monotonic() - t0) * 1000.0
        )

        self._broadcast({
            "type": "n_stroke_complete",
            "pipeline_id": pipeline_id,
            "satisfied": satisfied,
            "verdict": result.final_verdict,
            "latency": result.latency_ms
        })

        return result

# Legacy Aliases
TwoStrokeEngine = NStrokeEngine
