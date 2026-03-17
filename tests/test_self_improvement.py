"""
tests/test_self_improvement.py — TooLoo V2 self-improvement loop tests.

Covers:
  1. SelfImprovementEngine unit tests (offline)
     - report shape and field constraints
     - component manifest completeness (8 components × 3 waves)
     - wave ordering (wave 1 before wave 2 before wave 3)
     - JIT signals collected per component
     - all assessments present and well-formed
     - tribunal passes on safe mandate texts
     - recommendations list populated
     - refinement verdict valid
  2.  POST /v2/self-improve  HTTP e2e via TestClient
     - 200 status
     - response shape: self_improvement + latency_ms
     - all required fields in SelfImprovementReport
     - assessments count = 8
     - waves_executed = 3
     - health endpoint reports self_improvement: up

All tests are offline (no LLM / network).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import studio.api as api_module
from engine.self_improvement import (
    SelfImprovementEngine,
    SelfImprovementReport,
    _COMPONENTS,
)
from studio.api import app


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_router_state() -> None:
    api_module._router.reset()
    yield
    api_module._router.reset()


@pytest.fixture(scope="module")
def engine() -> SelfImprovementEngine:
    return SelfImprovementEngine()


@pytest.fixture(scope="module")
def report(engine: SelfImprovementEngine) -> SelfImprovementReport:
    """Run one full self-improvement cycle (offline) — reused across tests."""
    return engine.run()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Component Manifest
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestComponentManifest:
    def test_eight_components_defined(self) -> None:
        assert len(_COMPONENTS) == 8

    def test_all_waves_covered(self) -> None:
        waves = {c["wave"] for c in _COMPONENTS}
        assert waves == {1, 2, 3}

    def test_wave_1_has_three_components(self) -> None:
        assert sum(1 for c in _COMPONENTS if c["wave"] == 1) == 3

    def test_wave_2_has_three_components(self) -> None:
        assert sum(1 for c in _COMPONENTS if c["wave"] == 2) == 3

    def test_wave_3_has_two_components(self) -> None:
        assert sum(1 for c in _COMPONENTS if c["wave"] == 3) == 2

    def test_all_components_have_required_keys(self) -> None:
        for c in _COMPONENTS:
            assert "component" in c
            assert "description" in c
            assert "mandate" in c
            assert "wave" in c
            assert "deps" in c

    def test_mandate_texts_are_non_empty(self) -> None:
        for c in _COMPONENTS:
            assert len(
                c["mandate"]) > 20, f"{c['component']} mandate too short"

    def test_core_security_wave_components(self) -> None:
        wave1_names = {c["component"] for c in _COMPONENTS if c["wave"] == 1}
        assert wave1_names == {"router", "tribunal", "psyche_bank"}

    def test_performance_wave_components(self) -> None:
        wave2_names = {c["component"] for c in _COMPONENTS if c["wave"] == 2}
        assert wave2_names == {"jit_booster", "executor", "graph"}

    def test_meta_analysis_wave_components(self) -> None:
        wave3_names = {c["component"] for c in _COMPONENTS if c["wave"] == 3}
        assert wave3_names == {"scope_evaluator", "refinement"}

    def test_wave3_components_have_deps_on_wave2(self) -> None:
        wave3 = [c for c in _COMPONENTS if c["wave"] == 3]
        for c in wave3:
            assert len(
                c["deps"]) > 0, f"{c['component']} should declare dependencies"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. SelfImprovementReport shape
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSelfImprovementReportShape:
    def test_report_has_improvement_id(self, report: SelfImprovementReport) -> None:
        assert report.improvement_id.startswith("si-")

    def test_report_has_ts(self, report: SelfImprovementReport) -> None:
        assert report.ts  # ISO-8601 string

    def test_components_assessed_equals_eight(self, report: SelfImprovementReport) -> None:
        assert report.components_assessed == 8

    def test_waves_executed_equals_three(self, report: SelfImprovementReport) -> None:
        assert report.waves_executed == 3

    def test_total_signals_is_non_negative(self, report: SelfImprovementReport) -> None:
        assert report.total_signals >= 0

    def test_assessments_length_equals_eight(self, report: SelfImprovementReport) -> None:
        assert len(report.assessments) == 8

    def test_refinement_verdict_valid(self, report: SelfImprovementReport) -> None:
        assert report.refinement_verdict in ("pass", "warn", "fail")

    def test_refinement_success_rate_in_range(self, report: SelfImprovementReport) -> None:
        assert 0.0 <= report.refinement_success_rate <= 1.0

    def test_latency_ms_positive(self, report: SelfImprovementReport) -> None:
        assert report.latency_ms > 0

    def test_top_recommendations_is_list(self, report: SelfImprovementReport) -> None:
        assert isinstance(report.top_recommendations, list)

    def test_to_dict_has_all_keys(self, report: SelfImprovementReport) -> None:
        d = report.to_dict()
        required = {
            "improvement_id", "ts", "components_assessed", "waves_executed",
            "total_signals", "assessments", "top_recommendations",
            "refinement_verdict", "refinement_success_rate", "latency_ms",
        }
        assert required.issubset(d.keys())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. ComponentAssessment fields
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestComponentAssessments:
    def test_all_eight_components_present(self, report: SelfImprovementReport) -> None:
        names = {a.component for a in report.assessments}
        expected = {c["component"] for c in _COMPONENTS}
        assert names == expected

    def test_each_assessment_has_valid_intent(self, report: SelfImprovementReport) -> None:
        valid = {"BUILD", "DEBUG", "AUDIT", "DESIGN",
                 "EXPLAIN", "IDEATE", "SPAWN_REPO", "BLOCKED"}
        for a in report.assessments:
            assert a.intent in valid, f"{a.component} has unexpected intent {a.intent}"

    def test_boosted_confidence_gte_original(self, report: SelfImprovementReport) -> None:
        for a in report.assessments:
            assert a.boosted_confidence >= a.original_confidence, (
                f"{a.component}: boosted ({a.boosted_confidence}) < original ({a.original_confidence})"
            )

    def test_boosted_confidence_capped_at_one(self, report: SelfImprovementReport) -> None:
        for a in report.assessments:
            assert a.boosted_confidence <= 1.0, f"{a.component} boosted_confidence > 1.0"

    def test_jit_source_valid(self, report: SelfImprovementReport) -> None:
        for a in report.assessments:
            assert a.jit_source in ("gemini", "structured", "none"), (
                f"{a.component} has unknown jit_source {a.jit_source}"
            )

    def test_tribunal_passes_on_safe_mandates(self, report: SelfImprovementReport) -> None:
        # All self-improvement mandates are safe — tribunal must pass every one
        for a in report.assessments:
            assert a.tribunal_passed, f"Tribunal unexpectedly failed for {a.component}"

    def test_scope_summary_non_empty(self, report: SelfImprovementReport) -> None:
        for a in report.assessments:
            assert a.scope_summary, f"{a.component} has empty scope_summary"

    def test_suggestions_list_non_empty(self, report: SelfImprovementReport) -> None:
        for a in report.assessments:
            assert len(a.suggestions) > 0, f"{a.component} has no suggestions"

    def test_to_dict_has_all_keys(self, report: SelfImprovementReport) -> None:
        required = {
            "component", "description", "intent",
            "original_confidence", "boosted_confidence",
            "jit_signals", "jit_source", "tribunal_passed",
            "scope_summary", "execution_success", "execution_latency_ms",
            "suggestions",
        }
        for a in report.assessments:
            assert required.issubset(
                a.to_dict().keys()), f"{a.component} to_dict missing keys"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Offline structured-catalogue signals
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestOfflineSignals:
    def test_signals_come_from_structured_catalogue_offline(
        self, report: SelfImprovementReport
    ) -> None:
        # Offline (conftest patches _gemini_client=None) — all sources must be "structured"
        for a in report.assessments:
            assert a.jit_source == "structured", (
                f"{a.component} jit_source should be 'structured' in offline mode, got {a.jit_source}"
            )

    def test_total_signals_equals_sum_of_per_component_signals(
        self, report: SelfImprovementReport
    ) -> None:
        expected = sum(len(a.jit_signals) for a in report.assessments)
        assert report.total_signals == expected

    def test_at_least_one_signal_per_component_offline(
        self, report: SelfImprovementReport
    ) -> None:
        for a in report.assessments:
            assert len(a.jit_signals) >= 1, f"{a.component} has no JIT signals"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. HTTP e2e — POST /v2/self-improve
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSelfImproveEndpoint:
    def test_post_returns_200(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        assert r.status_code == 200

    def test_response_has_self_improvement_key(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        assert "self_improvement" in r.json()

    def test_response_has_latency_ms(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        assert r.json()["latency_ms"] > 0

    def test_self_improvement_has_improvement_id(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        si = r.json()["self_improvement"]
        assert si["improvement_id"].startswith("si-")

    def test_assessments_count_equals_eight(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        si = r.json()["self_improvement"]
        assert si["components_assessed"] == 8
        assert len(si["assessments"]) == 8

    def test_waves_executed_equals_three(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        assert r.json()["self_improvement"]["waves_executed"] == 3

    def test_refinement_verdict_present(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        verdict = r.json()["self_improvement"]["refinement_verdict"]
        assert verdict in ("pass", "warn", "fail")

    def test_top_recommendations_present(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        recs = r.json()["self_improvement"]["top_recommendations"]
        assert isinstance(recs, list)

    def test_all_assessment_keys_present(self, client: TestClient) -> None:
        r = client.post("/v2/self-improve")
        required = {
            "component", "description", "intent",
            "original_confidence", "boosted_confidence",
            "jit_signals", "jit_source", "tribunal_passed",
            "scope_summary", "execution_success",
            "execution_latency_ms", "suggestions",
        }
        for a in r.json()["self_improvement"]["assessments"]:
            assert required.issubset(
                a.keys()), f"Missing keys in assessment for {a.get('component')}"

    def test_improvement_ids_are_unique_across_calls(self, client: TestClient) -> None:
        r1 = client.post("/v2/self-improve")
        r2 = client.post("/v2/self-improve")
        id1 = r1.json()["self_improvement"]["improvement_id"]
        id2 = r2.json()["self_improvement"]["improvement_id"]
        assert id1 != id2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Health endpoint — self_improvement reported
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHealthReportsSelfImprovement:
    def test_health_includes_self_improvement_key(self, client: TestClient) -> None:
        r = client.get("/v2/health")
        assert r.status_code == 200
        assert r.json()["components"]["self_improvement"] == "up"
