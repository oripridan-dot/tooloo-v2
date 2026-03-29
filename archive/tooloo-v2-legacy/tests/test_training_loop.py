"""
tests/test_training_loop.py — TooLoo V2 SOTA Training Pipeline tests.

Covers:
  1. TrainingTelemetry unit tests
     - LearningCurve epoch tracking
     - Convergence / plateau detection
     - MetaLearner ghost weight adaptation
     - Persistence (save / load round-trip)
  2. Training epoch builder
  3. SOTA catalogue extensions (update, snapshot, 16D alignment)
  4. Pipeline dry-run execution

All tests are offline (no LLM / network).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

# ── Ensure root on path ───────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Patch LLM clients before importing engine modules
import engine.jit_booster as _jib_mod
import engine.self_improvement as _si_mod

_jib_mod._vertex_client = None
_jib_mod._gemini_client = None
_si_mod._vertex_client = None
_si_mod._gemini_client = None

from engine.sota_benchmarks import (
    DIMENSION_WEIGHTS_16D,
    SOTA_CATALOGUE,
    SOTABenchmark,
    compute_16d_alignment_vector,
    snapshot_catalogue,
    update_catalogue,
    weighted_alignment,
)
from engine.training_telemetry import (
    DimensionSnapshot,
    LearningCurve,
    MetaLearner,
    TrainingEpoch,
    build_epoch,
    load_telemetry,
    save_telemetry,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_scores(base: float = 0.85) -> dict[str, float]:
    """Create a 16D score dict with all dimensions set to base."""
    return {dim: base for dim in DIMENSION_WEIGHTS_16D}


def _make_epoch(
    epoch_number: int = 1,
    before: float = 0.85,
    after: float = 0.87,
) -> TrainingEpoch:
    """Build a test epoch with uniform scores."""
    return build_epoch(
        epoch_number=epoch_number,
        focus="balanced",
        scores_before=_make_scores(before),
        scores_after=_make_scores(after),
        sota_alignment_before=0.80,
        sota_alignment_after=0.82,
        ghost_winner="ghost-conservative",
        improvement_count=12,
        ipa_mean=0.015,
        latency_ms=400.0,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Learning Curve
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestLearningCurve:
    def test_starts_empty(self) -> None:
        curve = LearningCurve()
        assert curve.epoch_count == 0
        assert curve.total_gain() == 0.0
        assert not curve.is_converged()

    def test_add_epoch(self) -> None:
        curve = LearningCurve()
        epoch = _make_epoch(1, 0.85, 0.87)
        curve.add_epoch(epoch)
        assert curve.epoch_count == 1

    def test_composite_trajectory(self) -> None:
        curve = LearningCurve()
        curve.add_epoch(_make_epoch(1, 0.85, 0.87))
        curve.add_epoch(_make_epoch(2, 0.87, 0.89))
        traj = curve.composite_trajectory()
        assert len(traj) == 2
        assert traj[1] > traj[0]

    def test_total_gain_positive(self) -> None:
        curve = LearningCurve()
        curve.add_epoch(_make_epoch(1, 0.85, 0.87))
        curve.add_epoch(_make_epoch(2, 0.87, 0.89))
        assert curve.total_gain() > 0

    def test_best_epoch(self) -> None:
        curve = LearningCurve()
        curve.add_epoch(_make_epoch(1, 0.85, 0.87))  # Δ = 0.02
        curve.add_epoch(_make_epoch(2, 0.87, 0.90))  # Δ = 0.03
        best = curve.best_epoch()
        assert best is not None
        assert best.epoch_number == 2

    def test_convergence_not_detected_early(self) -> None:
        curve = LearningCurve()
        curve.add_epoch(_make_epoch(1, 0.85, 0.90))
        assert not curve.is_converged()

    def test_convergence_detected_on_plateau(self) -> None:
        curve = LearningCurve()
        # 3 epochs with near-zero delta → plateau
        curve.add_epoch(_make_epoch(1, 0.90, 0.9001))
        curve.add_epoch(_make_epoch(2, 0.9001, 0.9002))
        curve.add_epoch(_make_epoch(3, 0.9002, 0.9003))
        assert curve.is_converged()

    def test_plateau_dimensions(self) -> None:
        curve = LearningCurve()
        curve.add_epoch(_make_epoch(1, 0.90, 0.9001))
        curve.add_epoch(_make_epoch(2, 0.9001, 0.9002))
        curve.add_epoch(_make_epoch(3, 0.9002, 0.9003))
        plateaued = curve.plateau_dimensions()
        assert len(plateaued) == 16  # All dims plateaued

    def test_active_dimensions_when_improving(self) -> None:
        curve = LearningCurve()
        curve.add_epoch(_make_epoch(1, 0.85, 0.90))
        active = curve.active_dimensions()
        # With < PLATEAU_WINDOW epochs, nothing is plateaued
        assert len(active) == 16

    def test_to_dict_shape(self) -> None:
        curve = LearningCurve()
        curve.add_epoch(_make_epoch(1, 0.85, 0.87))
        d = curve.to_dict()
        assert "epoch_count" in d
        assert "total_gain" in d
        assert "converged" in d
        assert "epochs" in d
        assert len(d["epochs"]) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Meta-Learner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMetaLearner:
    def test_initial_weights_uniform(self) -> None:
        meta = MetaLearner()
        weights = meta.ghost_weights
        assert len(weights) == 3
        assert all(abs(w - 0.33) < 0.02 for w in weights.values())

    def test_record_epoch_updates_wins(self) -> None:
        meta = MetaLearner()
        epoch = _make_epoch()
        meta.record_epoch(epoch)
        assert meta._ghost_total == 1
        assert meta._ghost_wins.get("ghost-conservative", 0) == 1

    def test_ghost_weights_adapt_after_multiple_epochs(self) -> None:
        meta = MetaLearner()
        # ghost-aggressive wins 3 times
        for i in range(3):
            e = build_epoch(
                epoch_number=i + 1,
                focus="speed",
                scores_before=_make_scores(0.85),
                scores_after=_make_scores(0.87),
                sota_alignment_before=0.80,
                sota_alignment_after=0.82,
                ghost_winner="ghost-aggressive",
                improvement_count=10,
                ipa_mean=0.01,
                latency_ms=300.0,
            )
            meta.record_epoch(e)

        # ghost-aggressive should have highest weight
        weights = meta.ghost_weights
        assert weights["ghost-aggressive"] > weights["ghost-conservative"]
        assert weights["ghost-aggressive"] > weights["ghost-sota"]

    def test_recommended_focus(self) -> None:
        meta = MetaLearner()
        focus = meta.recommended_focus()
        assert isinstance(focus, str)
        assert len(focus) > 0

    def test_to_dict_shape(self) -> None:
        meta = MetaLearner()
        meta.record_epoch(_make_epoch())
        d = meta.to_dict()
        assert "ghost_weights" in d
        assert "ghost_wins" in d
        assert "recommended_focus" in d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Training Epoch Builder
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestBuildEpoch:
    def test_epoch_has_16_dimensions(self) -> None:
        epoch = _make_epoch()
        assert len(epoch.dimensions) == 16

    def test_epoch_delta_positive_on_improvement(self) -> None:
        epoch = _make_epoch(1, 0.85, 0.90)
        assert epoch.delta_composite > 0

    def test_epoch_id_format(self) -> None:
        epoch = _make_epoch()
        assert epoch.epoch_id.startswith("epoch-")

    def test_to_dict_round_trip(self) -> None:
        epoch = _make_epoch()
        d = epoch.to_dict()
        assert d["epoch_number"] == 1
        assert "dimensions" in d
        assert len(d["dimensions"]) == 16


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Persistence (save / load)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTelemetryPersistence:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        curve = LearningCurve()
        curve.add_epoch(_make_epoch())
        meta = MetaLearner()
        meta.record_epoch(_make_epoch())

        out = save_telemetry(curve, meta, tmp_path / "telem.json")
        assert out.exists()

    def test_load_round_trip(self, tmp_path: Path) -> None:
        # Save
        curve = LearningCurve()
        curve.add_epoch(_make_epoch(1, 0.85, 0.87))
        curve.add_epoch(_make_epoch(2, 0.87, 0.89))
        meta = MetaLearner()
        for e in curve.epochs:
            meta.record_epoch(e)

        path = tmp_path / "telem.json"
        save_telemetry(curve, meta, path)

        # Load
        loaded_curve, loaded_meta = load_telemetry(path)
        assert loaded_curve.epoch_count == 2
        assert loaded_meta._ghost_total == 2

    def test_load_from_missing_file(self, tmp_path: Path) -> None:
        curve, meta = load_telemetry(tmp_path / "nonexistent.json")
        assert curve.epoch_count == 0
        assert meta._ghost_total == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. SOTA Catalogue Extensions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestSOTACatalogueExtensions:
    def test_compute_16d_alignment_vector(self) -> None:
        vec = compute_16d_alignment_vector()
        assert len(vec) == 16
        assert all(0.0 <= v <= 1.0 for v in vec.values())

    def test_snapshot_catalogue(self) -> None:
        snap = snapshot_catalogue()
        assert "benchmark_count" in snap
        assert "domains" in snap
        assert "overall_weighted_alignment" in snap
        assert snap["benchmark_count"] > 0

    def test_update_catalogue_adds_new(self) -> None:
        original_count = len(SOTA_CATALOGUE)
        test_bm = SOTABenchmark(
            metric_name="test_unique_metric_xyz_123",
            sota_value=0.99,
            unit="ratio",
            sota_model_or_system="TestModel",
            tooloo_current=0.85,
            domain="intelligence",
            source="Test",
            pub_year=2026,
            notes="test benchmark",
        )
        updated = update_catalogue([test_bm])
        assert updated == 1
        assert len(SOTA_CATALOGUE) == original_count + 1

        # Cleanup — remove the test benchmark
        SOTA_CATALOGUE[:] = [
            b for b in SOTA_CATALOGUE
            if b.metric_name != "test_unique_metric_xyz_123"
        ]
