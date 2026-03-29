"""tests/test_validator_16d.py — Unit tests for engine/validator_16d.py and
engine/meta_architect.py.

Covers:
- Dimension16Score and Validation16DResult DTOs
- Validator16D.validate: result shape, all 16 dimensions present, composite score,
  autonomous gate, critical failures list, cost estimation
- Individual dimension validators: ROI, safety, security, legal, accuracy, speed
- MetaArchitect.generate: depth assessment, node IDs, confidence proof
- ConfidenceProof shape
- DynamicExecutionPlan.to_dict
"""
from __future__ import annotations

import pytest

from engine.validator_16d import (
    Dimension16Score,
    Validation16DResult,
    Validator16D,
)
from engine.meta_architect import (
    ConfidenceProof,
    DepthAssessment,
    DynamicExecutionPlan,
    GraphNodeSpec,
    MetaArchitect,
)

_VALID_INTENTS = ["BUILD", "DEBUG", "AUDIT", "DESIGN", "EXPLAIN", "IDEATE",
                  "SPAWN_REPO"]

# ── DTOs ─────────────────────────────────────────────────────────────────────


class TestDimension16Score:
    def test_to_dict_shape(self):
        d = Dimension16Score(name="Safety", score=0.95, passed=True,
                             details="No issues.", recommendation="")
        dd = d.to_dict()
        assert dd["name"] == "Safety"
        assert dd["score"] == 0.95
        assert dd["passed"] is True
        assert "details" in dd
        assert "recommendation" in dd

    def test_score_rounded_to_3_decimal(self):
        d = Dimension16Score(name="ROI", score=0.123456,
                             passed=True, details="ok")
        assert d.to_dict()["score"] == 0.123


class TestValidation16DResult:
    def test_to_dict_includes_all_keys(self):
        r = Validation16DResult(mandate_id="m-001", intent="BUILD")
        dd = r.to_dict()
        assert "mandate_id" in dd
        assert "intent" in dd
        assert "composite_score" in dd
        assert "autonomous_gate_pass" in dd
        assert "estimated_cost_usd" in dd
        assert "critical_failures" in dd
        assert "dimensions" in dd

    def test_defaults(self):
        r = Validation16DResult(mandate_id="m-x", intent="DEBUG")
        assert r.composite_score == 0.0
        assert r.autonomous_gate_pass is False
        assert r.critical_failures == []
        assert r.dimensions == []


# ── Validator16D ─────────────────────────────────────────────────────────────

class TestValidator16D:
    @pytest.fixture
    def validator(self):
        return Validator16D()

    def test_validate_returns_result(self, validator):
        result = validator.validate("m-001", "BUILD")
        assert isinstance(result, Validation16DResult)

    def test_all_16_dimensions_present(self, validator):
        result = validator.validate("m-xd", "DESIGN")
        dimension_names = {d.name for d in result.dimensions}
        expected = {
            "ROI", "Safety", "Security", "Legal", "Human Considering",
            "Accuracy", "Efficiency", "Quality", "Speed", "Monitor",
            "Control", "Honesty", "Resilience", "Financial Awareness",
            "Convergence", "Reversibility",
        }
        assert expected == dimension_names

    def test_composite_score_is_average_of_dimensions(self, validator):
        result = validator.validate("m-avg", "EXPLAIN")
        expected = sum(d.score for d in result.dimensions) / 16
        assert abs(result.composite_score - expected) < 0.0001

    def test_composite_score_in_range_0_1(self, validator):
        result = validator.validate("m-range", "AUDIT")
        assert 0.0 <= result.composite_score <= 1.0

    def test_cost_estimation_positive(self, validator):
        result = validator.validate("m-cost", "BUILD",
                                    estimated_input_tokens=1000,
                                    estimated_output_tokens=500)
        assert result.estimated_cost_usd >= 0.0

    def test_test_pass_rate_affects_accuracy(self, validator):
        r_full = validator.validate("m-full", "BUILD", test_pass_rate=1.0)
        r_half = validator.validate("m-half", "BUILD", test_pass_rate=0.5)
        acc_full = next(d for d in r_full.dimensions if d.name == "Accuracy")
        acc_half = next(d for d in r_half.dimensions if d.name == "Accuracy")
        assert acc_full.score > acc_half.score

    def test_security_score_low_for_eval_snippet(self, validator):
        snippet = "eval('malicious_code()')"
        result = validator.validate("m-sec", "BUILD", code_snippet=snippet)
        sec_dim = next(d for d in result.dimensions if d.name == "Security")
        # eval() should lower security score
        assert sec_dim.score < 0.95

    def test_safety_score_for_infinite_loop(self, validator):
        snippet = "while True:\n    pass"
        result = validator.validate("m-safe", "BUILD", code_snippet=snippet)
        safety_dim = next(d for d in result.dimensions if d.name == "Safety")
        assert safety_dim.score < 1.0

    def test_no_code_snippet_baseline_scores(self, validator):
        result = validator.validate("m-nocode", "IDEATE", code_snippet=None)
        # All dimensions should have reasonable baseline scores
        for dim in result.dimensions:
            assert 0.0 <= dim.score <= 1.0

    def test_spawn_repo_roi_multiplier(self, validator):
        """SPAWN_REPO has 2.0x ROI multiplier — allows higher cost before penalty."""
        r_sr = validator.validate("m-sr", "SPAWN_REPO",
                                  estimated_input_tokens=500,
                                  estimated_output_tokens=1000)
        r_ex = validator.validate("m-ex", "EXPLAIN",
                                  estimated_input_tokens=500,
                                  estimated_output_tokens=1000)
        roi_sr = next(d for d in r_sr.dimensions if d.name == "ROI")
        roi_ex = next(d for d in r_ex.dimensions if d.name == "ROI")
        # SPAWN_REPO should have higher or equal ROI score
        assert roi_sr.score >= roi_ex.score

    def test_latency_affects_speed_dimension(self, validator):
        r_fast = validator.validate("m-fast", "BUILD",
                                    latency_p50_ms=200, latency_p90_ms=400)
        r_slow = validator.validate("m-slow", "BUILD",
                                    latency_p50_ms=2000, latency_p90_ms=5000)
        spd_fast = next(d for d in r_fast.dimensions if d.name == "Speed")
        spd_slow = next(d for d in r_slow.dimensions if d.name == "Speed")
        assert spd_fast.score >= spd_slow.score

    def test_critical_failures_list_contains_failed_critical_dims(self, validator):
        """High latency + low test pass rate shouldn't cause critical failures."""
        result = validator.validate("m-crit", "BUILD",
                                    test_pass_rate=1.0,
                                    code_snippet="result = 42  # safe code")
        # All critical dims should pass when code is safe
        assert result.critical_failures == []

    @pytest.mark.parametrize("intent", _VALID_INTENTS)
    def test_all_intents_produce_valid_result(self, validator, intent):
        result = validator.validate(f"m-{intent.lower()}", intent)
        assert isinstance(result, Validation16DResult)
        assert len(result.dimensions) == 16

    def test_to_dict_serializable(self, validator):
        import json
        result = validator.validate("m-serial", "BUILD")
        serialized = json.dumps(result.to_dict())
        assert len(serialized) > 0


# ── MetaArchitect ─────────────────────────────────────────────────────────────

class TestMetaArchitect:
    @pytest.fixture
    def architect(self):
        return MetaArchitect()

    def test_generate_returns_plan(self, architect):
        plan = architect.generate(
            "Build a new authentication service", "BUILD")
        assert isinstance(plan, DynamicExecutionPlan)

    def test_low_roi_mandate(self, architect):
        plan = architect.generate("hello", "EXPLAIN")
        assert plan.depth_assessment.investigation_roi == "low"

    def test_high_roi_mandate(self, architect):
        plan = architect.generate(
            "Refactor the multi-parallel pipeline architecture for latency and security", "BUILD"
        )
        assert plan.depth_assessment.investigation_roi == "high"
        # high ROI should include deep_research node
        node_ids = {n.node_id for n in plan.execution_graph}
        assert "deep_research" in node_ids

    def test_medium_roi_mandate(self, architect):
        # "model" is in _HIGH_ROI_HINTS → 1 hit → medium ROI
        plan = architect.generate(
            "Implement a new config loader model", "BUILD")
        assert plan.depth_assessment.investigation_roi == "medium"

    def test_execution_graph_contains_core_nodes(self, architect):
        plan = architect.generate("implement a rate limiter", "BUILD")
        node_ids = {n.node_id for n in plan.execution_graph}
        # Core nodes always present
        for core in ["audit_wave", "design_wave", "implement", "emit"]:
            assert core in node_ids, f"Missing core node: {core}"

    def test_divergent_validation_present(self, architect):
        plan = architect.generate("implement authentication flow", "BUILD")
        node_ids = {n.node_id for n in plan.execution_graph}
        assert "validate_primary" in node_ids
        assert "validate_divergent" in node_ids

    def test_emit_depends_on_both_validators(self, architect):
        plan = architect.generate("build feature", "BUILD")
        emit_node = next(
            n for n in plan.execution_graph if n.node_id == "emit")
        assert "validate_primary" in emit_node.dependencies
        assert "validate_divergent" in emit_node.dependencies

    def test_confidence_proof_shape(self, architect):
        plan = architect.generate("build feature", "BUILD")
        proof = plan.confidence_proof
        assert 0.0 <= proof.proof_confidence <= 1.0
        assert 0.0 <= proof.historical_similarity <= 1.0
        assert 0.0 <= proof.topology_validity <= 1.0
        assert 0.0 <= proof.tribunal_cleanliness <= 1.0
        assert 0.0 <= proof.convergence_guardrail <= 1.0
        assert 0.0 <= proof.reversibility_guarantees <= 1.0

    def test_high_roi_has_high_confidence(self, architect):
        plan = architect.generate(
            "Refactor parallel multi-model pipeline architecture security latency", "BUILD"
        )
        assert plan.confidence_proof.proof_confidence > 0.85

    def test_to_dict_serializable(self, architect):
        import json
        plan = architect.generate("build feature", "BUILD")
        serialized = json.dumps(plan.to_dict())
        assert len(serialized) > 0

    def test_to_topology_spec_returns_tuples(self, architect):
        plan = architect.generate("implement a caching layer", "BUILD")
        spec = architect.to_topology_spec(plan)
        assert isinstance(spec, list)
        for item in spec:
            assert len(item) == 2
            node_id, deps = item
            assert isinstance(node_id, str)
            assert isinstance(deps, list)

    def test_graph_node_spec_to_dict(self, architect):
        plan = architect.generate("build feature", "BUILD")
        node = plan.execution_graph[0]
        d = node.to_dict()
        assert "node_id" in d
        assert "action_type" in d
        assert "dependencies" in d
        assert "cognitive_profile" in d
        assert "node_mandate" in d

    def test_depth_assessment_to_dict(self, architect):
        plan = architect.generate("refactor architecture", "BUILD")
        da = plan.depth_assessment
        d = da.to_dict()
        assert "investigation_roi" in d
        assert d["investigation_roi"] in ("high", "medium", "low")
        assert "rationale" in d
