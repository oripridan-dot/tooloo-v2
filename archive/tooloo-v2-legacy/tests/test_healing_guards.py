"""tests/test_healing_guards.py — Unit tests for engine/healing_guards.py.

Covers:
- ConvergenceGuard: first check, converging, stagnant, burnout, reset
- ReversibilityGuard: snapshot creation, hash integrity, rollback closure
- TransactionalSnapshot: to_dict shape
- ConvergenceMetrics: to_dict shape
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from engine.healing_guards import (
    ConvergenceGuard,
    ConvergenceMetrics,
    ReversibilityGuard,
    TransactionalSnapshot,
)


# ── ConvergenceMetrics DTO ────────────────────────────────────────────────────

class TestConvergenceMetricsDTO:
    def test_to_dict_shape(self):
        m = ConvergenceMetrics(
            stroke_number=2,
            failure_count=3,
            previous_failure_count=5,
            is_converging=True,
            iterations_to_convergence=2,
            burnout_risk=False,
        )
        d = m.to_dict()
        assert d["stroke_number"] == 2
        assert d["failure_count"] == 3
        assert d["previous_failure_count"] == 5
        assert d["is_converging"] is True
        assert d["iterations_to_convergence"] == 2
        assert d["burnout_risk"] is False

    def test_to_dict_all_keys_present(self):
        m = ConvergenceMetrics(stroke_number=1, failure_count=0)
        keys = m.to_dict().keys()
        expected = {"stroke_number", "failure_count", "previous_failure_count",
                    "is_converging", "iterations_to_convergence", "burnout_risk"}
        assert expected == set(keys)


# ── ConvergenceGuard ─────────────────────────────────────────────────────────

class TestConvergenceGuard:
    def test_first_check_always_converging(self):
        g = ConvergenceGuard()
        m = g.check(current_failure_count=10)
        assert m.stroke_number == 1
        assert m.is_converging is True
        assert m.burnout_risk is False
        assert m.previous_failure_count is None

    def test_improvement_detected(self):
        g = ConvergenceGuard()
        g.check(10)  # baseline
        m = g.check(8)  # improved by 2
        assert m.is_converging is True
        assert m.burnout_risk is False
        assert m.previous_failure_count == 10

    def test_no_improvement_increments_stagnant(self):
        g = ConvergenceGuard()
        g.check(10)
        m = g.check(10)  # same
        assert m.is_converging is False
        assert m.burnout_risk is False  # only 1 stagnant attempt

    def test_burnout_after_max_stagnant_attempts(self):
        g = ConvergenceGuard()
        g.check(10)  # stroke 1 baseline
        g.check(10)  # stagnant 1
        g.check(10)  # stagnant 2
        m = g.check(10)  # stagnant 3 — hits MAX_HEALING_ATTEMPTS=3
        assert m.burnout_risk is True

    def test_improvement_resets_stagnant_counter(self):
        g = ConvergenceGuard()
        g.check(10)
        g.check(10)  # stagnant 1
        g.check(8)   # improved — resets counter
        m = g.check(8)  # stagnant 1 again
        assert m.burnout_risk is False  # only 1 stagnant after reset

    def test_reset_clears_all_state(self):
        g = ConvergenceGuard()
        g.check(10)
        g.check(10)
        g.check(10)
        g.reset()
        assert g.failure_history == []
        assert g.stagnant_attempts == 0
        # After reset, next check is treated as stroke 1
        m = g.check(5)
        assert m.stroke_number == 1
        assert m.is_converging is True

    def test_stroke_number_increments(self):
        g = ConvergenceGuard()
        for i in range(5):
            m = g.check(10)
            assert m.stroke_number == i + 1

    def test_convergence_to_zero_failures(self):
        g = ConvergenceGuard()
        g.check(5)
        g.check(3)
        m = g.check(0)
        assert m.is_converging is True
        assert m.failure_count == 0


# ── TransactionalSnapshot DTO ─────────────────────────────────────────────────

class TestTransactionalSnapshot:
    def test_to_dict_shape(self):
        snap = TransactionalSnapshot(
            snapshot_id="snap-001",
            affected_files={"engine/router.py": "abc123"},
            timestamp_ns=1234567890,
            metadata={"stroke": 1},
        )
        d = snap.to_dict()
        assert d["snapshot_id"] == "snap-001"
        assert d["affected_files"] == {"engine/router.py": "abc123"}
        assert d["timestamp_ns"] == 1234567890
        assert d["metadata"]["stroke"] == 1


# ── ReversibilityGuard ────────────────────────────────────────────────────────

class TestReversibilityGuard:
    @pytest.fixture
    def workspace(self, tmp_path):
        """Temp workspace with one test file."""
        f = tmp_path / "engine" / "test_module.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# original content\n")
        return tmp_path

    def test_snapshot_existing_file(self, workspace):
        guard = ReversibilityGuard(workspace)
        snap = guard.snapshot_before_stroke(
            "snap-1", ["engine/test_module.py"])

        assert snap.snapshot_id == "snap-1"
        original_content = (workspace / "engine" /
                            "test_module.py").read_bytes()
        expected_hash = hashlib.sha256(original_content).hexdigest()
        assert snap.affected_files["engine/test_module.py"] == expected_hash

    def test_snapshot_nonexistent_file_uses_sentinel(self, workspace):
        guard = ReversibilityGuard(workspace)
        snap = guard.snapshot_before_stroke(
            "snap-noexist", ["engine/nonexistent.py"])
        assert snap.affected_files["engine/nonexistent.py"] == "NONEXISTENT"

    def test_snapshot_stored_in_guard(self, workspace):
        guard = ReversibilityGuard(workspace)
        guard.snapshot_before_stroke("snap-store", ["engine/test_module.py"])
        assert "snap-store" in guard.snapshots

    def test_multiple_files_snapshotted(self, workspace):
        # Create second file
        f2 = workspace / "engine" / "config.py"
        f2.write_text("# config\n")
        guard = ReversibilityGuard(workspace)
        snap = guard.snapshot_before_stroke(
            "snap-multi", ["engine/test_module.py", "engine/config.py"]
        )
        assert len(snap.affected_files) == 2
        assert "engine/test_module.py" in snap.affected_files
        assert "engine/config.py" in snap.affected_files

    def test_rollback_closure_creation(self, workspace):
        guard = ReversibilityGuard(workspace)
        guard.snapshot_before_stroke("snap-roll", ["engine/test_module.py"])
        target = workspace / "engine" / "test_module.py"
        original = target.read_text()

        def rollback() -> bool:
            target.write_text(original)
            return True

        guard.rollback_closures["snap-roll"] = rollback
        # Mutate the file
        target.write_text("# mutated content\n")
        assert target.read_text() == "# mutated content\n"
        # Rollback
        result = guard.rollback_closures["snap-roll"]()
        assert result is True
        assert target.read_text() == original

    def test_snapshot_immutable_metadata(self, workspace):
        guard = ReversibilityGuard(workspace)
        snap = guard.snapshot_before_stroke(
            "snap-meta", ["engine/test_module.py"])
        # Snapshot should record the state at time of creation
        original_hash = snap.affected_files["engine/test_module.py"]
        # Mutate file after snapshot
        (workspace / "engine" / "test_module.py").write_text("# changed\n")
        # Snapshot should be unchanged
        assert snap.affected_files["engine/test_module.py"] == original_hash
