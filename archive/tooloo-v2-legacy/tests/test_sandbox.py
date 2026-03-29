"""Tests for engine/sandbox.py — SandboxOrchestrator and PROMOTE_THRESHOLD."""
from __future__ import annotations

from engine.sandbox import PROMOTE_THRESHOLD, SandboxOrchestrator


class TestSandboxPromoteThreshold:
    def test_promote_threshold_value(self):
        # DEV MODE: PROMOTE_THRESHOLD is 0.50
        assert PROMOTE_THRESHOLD == 0.50

    def test_compute_readiness_tribunal_fail_is_hard_gate(self):
        """Tribunal failure must always return 0.0 readiness."""
        orchestrator = SandboxOrchestrator()
        readiness = orchestrator._compute_readiness(
            tribunal_passed=False,
            exec_success_rate=1.0,
            refinement_verdict="pass",
            confidence=0.99,
            impact=0.99,
        )
        assert readiness == 0.0, "Tribunal failure must hard-gate readiness to 0"

    def test_compute_readiness_above_threshold_when_all_pass(self):
        """High-confidence full-pass run must meet promote threshold."""
        orchestrator = SandboxOrchestrator()
        readiness = orchestrator._compute_readiness(
            tribunal_passed=True,
            exec_success_rate=1.0,
            refinement_verdict="pass",
            confidence=0.95,
            impact=0.90,
        )
        assert readiness >= PROMOTE_THRESHOLD, (
            f"Expected readiness >= {PROMOTE_THRESHOLD}, got {readiness}"
        )

    def test_compute_readiness_below_threshold_on_failure(self):
        """Failed execution with low confidence must fall below promote threshold."""
        orchestrator = SandboxOrchestrator()
        readiness = orchestrator._compute_readiness(
            tribunal_passed=True,
            exec_success_rate=0.0,
            refinement_verdict="fail",
            confidence=0.30,
            impact=0.10,
        )
        assert readiness < PROMOTE_THRESHOLD, (
            f"Expected readiness < {PROMOTE_THRESHOLD}, got {readiness}"
        )

    def test_compute_readiness_in_valid_range(self):
        orchestrator = SandboxOrchestrator()
        for tribunal in (True, False):
            for rate in (0.0, 0.5, 1.0):
                for verdict in ("pass", "warn", "fail"):
                    r = orchestrator._compute_readiness(
                        tribunal_passed=tribunal,
                        exec_success_rate=rate,
                        refinement_verdict=verdict,
                        confidence=0.75,
                        impact=0.70,
                    )
                    assert 0.0 <= r <= 1.0, (
                        f"readiness {r} out of [0,1] for tribunal={tribunal}, "
                        f"rate={rate}, verdict={verdict}"
                    )


class TestSandboxOrchestrator:
    def test_instantiation(self):
        orchestrator = SandboxOrchestrator()
        assert orchestrator is not None

    def test_all_reports_initially_empty(self):
        orchestrator = SandboxOrchestrator()
        assert orchestrator.all_reports() == []

    def test_vector_store_summary_shape(self):
        orchestrator = SandboxOrchestrator()
        summary = orchestrator.vector_store_summary()
        assert "size" in summary
        assert "dup_threshold" in summary
        assert summary["dup_threshold"] == 0.90
