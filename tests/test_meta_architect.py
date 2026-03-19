from __future__ import annotations

from datetime import UTC, datetime

from engine.executor import JITExecutor
from engine.graph import TopologicalSorter
from engine.jit_booster import JITBooster
from engine.mcp_manager import MCPManager
from engine.meta_architect import MetaArchitect
from engine.model_selector import ModelSelector
from engine.n_stroke import NStrokeEngine
from engine.psyche_bank import PsycheBank
from engine.refinement import RefinementLoop
from engine.refinement_supervisor import RefinementSupervisor
from engine.router import LockedIntent, MandateRouter
from engine.scope_evaluator import ScopeEvaluator
from engine.tribunal import Tribunal


def _locked(text: str) -> LockedIntent:
    return LockedIntent(
        intent="BUILD",
        confidence=0.95,
        value_statement="Dynamic DAG validation",
        constraint_summary="",
        mandate_text=text,
        context_turns=[],
        locked_at=datetime.now(UTC).isoformat(),
    )


def _engine() -> NStrokeEngine:
    return NStrokeEngine(
        router=MandateRouter(),
        booster=JITBooster(),
        tribunal=Tribunal(bank=PsycheBank()),
        sorter=TopologicalSorter(),
        executor=JITExecutor(),
        scope_evaluator=ScopeEvaluator(),
        refinement_loop=RefinementLoop(),
        mcp_manager=MCPManager(),
        model_selector=ModelSelector(),
        refinement_supervisor=RefinementSupervisor(),
        broadcast_fn=lambda _event: None,
        max_strokes=2,
    )


def test_meta_architect_high_roi_injects_deep_research() -> None:
    planner = MetaArchitect()
    plan = planner.generate(
        "Perform a dynamic architecture refactor with model routing and security validation",
        "BUILD",
    )
    node_ids = [n.node_id for n in plan.execution_graph]
    assert "deep_research" in node_ids
    assert plan.depth_assessment.investigation_roi == "high"


def test_meta_architect_low_roi_skips_deep_research() -> None:
    planner = MetaArchitect()
    plan = planner.generate("fix typo in log message", "DEBUG")
    node_ids = [n.node_id for n in plan.execution_graph]
    assert "deep_research" not in node_ids


def test_meta_architect_proof_confidence_within_bounds() -> None:
    planner = MetaArchitect()
    plan = planner.generate(
        "architect dynamic dag with divergence validation and autonomous execution",
        "BUILD",
    )
    assert 0.0 <= plan.confidence_proof.proof_confidence <= 1.0
    assert plan.confidence_proof.divergence_coverage >= 0.7


def test_n_stroke_emits_confidence_proof_and_divergence_metrics() -> None:
    result = _engine().run(
        _locked("build dynamic execution graph with divergent validation lanes")
    )
    stroke = result.strokes[0]
    assert "proof_confidence" in stroke.confidence_proof
    assert "divergence_score" in stroke.divergence_metrics
    assert stroke.divergence_metrics["validation_nodes"] >= 1
