#!/usr/bin/env python3
"""
scripts/sota_training_loop.py — Master SOTA Training Pipeline for TooLoo V2.

Closed-loop autonomous training:

  EPOCH N:
    1. HARVEST  → Fetch live SOTA data from leaderboards
    2. BASELINE → Run CalibrationEngine to measure current 16D alignment
    3. DIAGNOSE → Run SelfImprovementEngine with fresh SOTA signals
    4. VALIDATE → Re-run calibration to measure Δ16D gains
    5. LEARN    → Feed gains into training telemetry for meta-learning
    6. ADAPT    → Adjust ghost weights, focus, and wave priorities

  Repeat for N epochs until convergence (Δ16D < ε threshold)

Usage:
    python scripts/sota_training_loop.py                       # 3 epochs, dry-run
    python scripts/sota_training_loop.py --epochs 5            # 5 epochs
    python scripts/sota_training_loop.py --live --epochs 10    # live SOTA fetch
    python scripts/sota_training_loop.py --focus efficiency,security
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ── Project root ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Patch LLM clients for offline mode ────────────────────────────────────────
import engine.jit_booster as _jib_mod
import engine.self_improvement as _si_mod

_LIVE_MODE = False  # set by CLI


def _patch_offline() -> None:
    """Disable LLM clients when not in live mode."""
    _jib_mod._vertex_client = None
    _jib_mod._gemini_client = None
    _si_mod._vertex_client = None
    _si_mod._gemini_client = None


# ── Deferred imports (after sys.path fix) ─────────────────────────────────────
from engine.calibration_engine import CalibrationEngine, refresh_dynamic_confidence
from engine.self_improvement import SelfImprovementEngine
from engine.sota_benchmarks import (
    compute_16d_alignment_vector,
    snapshot_catalogue,
    update_catalogue,
    weighted_alignment,
    SOTA_CATALOGUE,
)
from engine.training_telemetry import (
    LearningCurve,
    MetaLearner,
    TrainingEpoch,
    build_epoch,
    load_telemetry,
    save_telemetry,
)

# ── Constants ─────────────────────────────────────────────────────────────────
_CONVERGENCE_EPSILON: float = 0.001  # Δ composite < 0.1% = converged
_DRY_RUN_BANNER = "[DRY-RUN]"


# ── Training Pipeline ─────────────────────────────────────────────────────────

class SOTATrainingPipeline:
    """Orchestrates the full closed-loop training cycle.

    Each epoch:
      1. Fetches SOTA data (live or from embedded catalogue)
      2. Runs calibration to get baseline 16D scores
      3. Runs self-improvement with meta-learning feedback
      4. Re-calibrates to measure Δ16D
      5. Records telemetry and adapts strategy for next epoch
    """

    def __init__(
        self,
        epochs: int = 3,
        focus: str = "balanced",
        live: bool = False,
        dry_run: bool = True,
    ) -> None:
        self._max_epochs = epochs
        self._initial_focus = focus
        self._live = live
        self._dry_run = dry_run

        # Load previous telemetry (resume from last training session)
        self._curve, self._meta = load_telemetry()

        # Engines
        self._calibration = CalibrationEngine()
        self._si_engine = SelfImprovementEngine(
            optimization_focus=focus,
            meta_feedback=self._meta.to_dict(),
        )

    async def run(self) -> dict[str, Any]:
        """Execute the training loop for N epochs or until convergence."""
        start = time.monotonic()
        prefix = _DRY_RUN_BANNER + " " if self._dry_run else ""

        print(f"\n{'═' * 70}")
        print(f"  {prefix}TooLoo V2 — SOTA Training Pipeline")
        print(f"  Epochs: {self._max_epochs} | Focus: {self._initial_focus} | "
              f"Live: {self._live} | Resume from epoch: {self._curve.epoch_count}")
        print(f"{'═' * 70}\n")

        results: list[dict[str, Any]] = []

        for epoch_num in range(1, self._max_epochs + 1):
            actual_epoch = self._curve.epoch_count + epoch_num
            print(f"\n{'─' * 70}")
            print(f"  EPOCH {actual_epoch} / {self._curve.epoch_count + self._max_epochs}")
            print(f"{'─' * 70}")

            epoch_result = await self._run_epoch(actual_epoch, epoch_num)
            results.append(epoch_result)

            # Check convergence
            if self._curve.is_converged():
                print(f"\n  ✓ CONVERGED at epoch {actual_epoch} — all 16D dimensions plateaued")
                break

        # ── Final summary ─────────────────────────────────────────────────
        total_time = time.monotonic() - start
        summary = self._build_summary(results, total_time)

        # Persist telemetry
        telem_path = save_telemetry(self._curve, self._meta)
        print(f"\n  Telemetry saved: {telem_path}")

        self._print_summary(summary)
        return summary

    async def _run_epoch(self, epoch_number: int, relative: int) -> dict[str, Any]:
        """Execute a single training epoch."""
        t0 = time.monotonic()

        # ── Phase 1: Harvest SOTA data ────────────────────────────────────
        print(f"\n  [1/5] HARVEST — Fetching SOTA data...")
        sota_count = self._harvest_sota()
        print(f"         → {sota_count} benchmarks in catalogue")

        # ── Phase 2: Baseline calibration ─────────────────────────────────
        print(f"  [2/5] BASELINE — Running 5-cycle calibration...")
        scores_before = compute_16d_alignment_vector()
        alignment_before = weighted_alignment(SOTA_CATALOGUE)
        refresh_dynamic_confidence()  # update scores from live code quality
        cal_report_before = self._calibration.run_5_cycles()
        baseline_composite = cal_report_before.system_alignment_after
        print(f"         → Composite: {baseline_composite:.4f} | "
              f"SOTA alignment: {alignment_before:.4f}")

        # ── Phase 3: Self-improvement with meta-feedback ──────────────────
        focus = self._meta.recommended_focus() if relative > 1 else self._initial_focus
        print(f"  [3/5] DIAGNOSE — Self-improvement (focus: {focus})...")
        meta_feedback = self._meta.to_dict()
        si_report = await self._si_engine.run(
            optimization_focus=focus,
            run_regression_gate=not self._dry_run,
            meta_feedback=meta_feedback,
        )
        improvement_count = sum(
            1 for a in si_report.assessments if a.execution_success
        )
        print(f"         → {improvement_count}/{si_report.components_assessed} "
              f"components improved | "
              f"verdict: {si_report.refinement_verdict}")

        # ── Phase 4: Re-calibrate (measure Δ) ────────────────────────────
        print(f"  [4/5] VALIDATE — Re-calibrating...")
        scores_after = compute_16d_alignment_vector()
        alignment_after = weighted_alignment(SOTA_CATALOGUE)
        refresh_dynamic_confidence()  # re-score after self-improvement changes
        cal_report_after = self._calibration.run_5_cycles()
        validated_composite = cal_report_after.system_alignment_after
        delta = CalibrationEngine.delta_from_previous(
            cal_report_before, cal_report_after
        )
        print(f"         → Composite: {validated_composite:.4f} | "
              f"Δ: {delta['delta_composite']:+.4f} | "
              f"IPA: {delta['ipa']:.4f}")

        # ── Phase 5: Learn & Adapt ────────────────────────────────────────
        print(f"  [5/5] LEARN — Recording telemetry & adapting strategy...")
        ghost_winner = getattr(self._si_engine, 'ghost_winner', 'ghost-conservative')
        ipa_mean = delta.get("ipa", 0.0)

        prev_lr = {
            dim: self._curve._learning_rates.get(dim, 0.0)
            for dim in scores_before
        }

        epoch = build_epoch(
            epoch_number=epoch_number,
            focus=focus,
            scores_before=scores_before,
            scores_after=scores_after,
            sota_alignment_before=alignment_before,
            sota_alignment_after=alignment_after,
            ghost_winner=ghost_winner,
            improvement_count=improvement_count,
            ipa_mean=ipa_mean,
            latency_ms=round((time.monotonic() - t0) * 1000, 2),
            previous_learning_rates=prev_lr,
        )

        self._curve.add_epoch(epoch)
        self._meta.record_epoch(epoch)

        # Print per-dimension summary
        improved = [d.name for d in epoch.dimensions if d.delta > 0.001]
        plateaued_count = len(self._curve.plateau_dimensions())
        print(f"         → Improved dims: {len(improved)} | "
              f"Plateaued: {plateaued_count}/16 | "
              f"Ghost winner: {ghost_winner}")
        print(f"         → Next focus: {self._meta.recommended_focus()}")
        print(f"         → Ghost weights: {self._meta.ghost_weights}")

        epoch_time = time.monotonic() - t0
        print(f"         → Epoch time: {epoch_time:.1f}s")

        return epoch.to_dict()

    def _harvest_sota(self) -> int:
        """Fetch and integrate SOTA data."""
        if self._live:
            try:
                from scripts.fetch_sota_leaderboards import fetch_live_sota
                benchmarks = fetch_live_sota()
                return update_catalogue(benchmarks) + len(SOTA_CATALOGUE)
            except Exception as e:
                print(f"         ⚠ Live fetch failed ({e}), using embedded catalogue")
                return len(SOTA_CATALOGUE)
        else:
            # Use embedded catalogue (already loaded)
            return len(SOTA_CATALOGUE)

    def _build_summary(
        self,
        results: list[dict[str, Any]],
        total_time: float,
    ) -> dict[str, Any]:
        """Build the final training summary."""
        return {
            "training_id": f"train-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}",
            "timestamp": datetime.now(UTC).isoformat(),
            "epochs_completed": len(results),
            "total_time_s": round(total_time, 2),
            "converged": self._curve.is_converged(),
            "total_16d_gain": round(self._curve.total_gain(), 4),
            "total_16d_gain_pct": round(self._curve.total_gain() * 100, 2),
            "composite_trajectory": [
                round(c, 4) for c in self._curve.composite_trajectory()
            ],
            "plateau_dimensions": self._curve.plateau_dimensions(),
            "active_dimensions": self._curve.active_dimensions(),
            "meta_learner": self._meta.to_dict(),
            "best_epoch": (
                self._curve.best_epoch().to_dict()
                if self._curve.best_epoch()
                else None
            ),
            "epoch_results": results,
        }

    def _print_summary(self, summary: dict[str, Any]) -> None:
        """Print a human-readable training summary."""
        prefix = _DRY_RUN_BANNER + " " if self._dry_run else ""

        print(f"\n{'═' * 70}")
        print(f"  {prefix}TRAINING COMPLETE — SUMMARY")
        print(f"{'═' * 70}")
        print(f"  Training ID:       {summary['training_id']}")
        print(f"  Epochs completed:  {summary['epochs_completed']}")
        print(f"  Total time:        {summary['total_time_s']:.1f}s")
        print(f"  Converged:         {summary['converged']}")
        print(f"  Total 16D gain:    {summary['total_16d_gain']:+.4f} "
              f"({summary['total_16d_gain_pct']:+.2f}%)")

        traj = summary.get("composite_trajectory", [])
        if traj:
            print(f"  Composite curve:   {' → '.join(f'{c:.4f}' for c in traj)}")

        plateaued = summary.get("plateau_dimensions", [])
        if plateaued:
            print(f"  Plateaued dims:    {', '.join(plateaued)}")

        active = summary.get("active_dimensions", [])
        if active:
            print(f"  Active dims:       {', '.join(active)}")

        meta = summary.get("meta_learner", {})
        ghost_w = meta.get("ghost_weights", {})
        if ghost_w:
            print(f"  Ghost weights:     {ghost_w}")
            print(f"  Next focus:        {meta.get('recommended_focus', 'balanced')}")

        print(f"{'═' * 70}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the TooLoo V2 SOTA Training Pipeline"
    )
    parser.add_argument(
        "--epochs", type=int, default=3,
        help="Number of training epochs (default: 3)"
    )
    parser.add_argument(
        "--focus", type=str, default="balanced",
        help="Optimization focus (e.g. 'efficiency,security,speed')"
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Use live SOTA data fetching via Gemini/Vertex AI"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Don't write file changes (default: True)"
    )
    parser.add_argument(
        "--no-dry-run", action="store_true",
        help="Allow file writes during self-improvement"
    )
    args = parser.parse_args()

    # Handle dry-run logic
    dry_run = not args.no_dry_run

    # Patch offline mode
    global _LIVE_MODE
    _LIVE_MODE = args.live
    if not args.live:
        _patch_offline()

    pipeline = SOTATrainingPipeline(
        epochs=args.epochs,
        focus=args.focus,
        live=args.live,
        dry_run=dry_run,
    )

    summary = asyncio.run(pipeline.run())

    # Write summary to file
    out_path = _ROOT / "psyche_bank" / "training_summary.json"
    out_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Summary written to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
