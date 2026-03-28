# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining run_cycles.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.403071
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

#!/usr/bin/env python3
"""run_cycles.py -- TooLoo V2 Batch Improvement Cycle Runner.

Runs multiple sequential SelfImprovementEngine cycles (default: 3) to
maximise SOTA signal coverage, identify cross-cycle trends, and accumulate
value-scored improvement recommendations across all 12 engine components.

Each cycle runs the full 5-wave DAG (12 components x parallel fan-out at
max_workers=6) and publishes a structured report.  Between cycles a brief
inter-cycle analysis compares value scores, surfaces newly surfaced signals,
and identifies stagnating components that need deeper investigation.

Usage
-----
  python run_cycles.py                  # 3 cycles, offline mode
  python run_cycles.py --cycles 5       # 5 cycles
  python run_cycles.py --cycles 3 --god-mode   # 3 cycles + write approved SOTA annotations
  TOOLOO_LIVE_TESTS=1 python run_cycles.py     # live Gemini/Vertex mode

Environment
-----------
  TOOLOO_LIVE_TESTS=1   -- enable live Gemini-powered LLM analysis
  RUN_CYCLES_N          -- override --cycles default (env fallback)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import engine.jit_booster as _jib_mod  # noqa: E402
from engine.vector_store import VectorStore  # noqa: E402
_LIVE_MODE: bool = os.environ.get(
    "TOOLOO_LIVE_TESTS", "").lower() in ("1", "true", "yes")
if not _LIVE_MODE:
    # Null out ALL live-inference clients across every engine module so the
    # full offline cycle completes in <10 s instead of hitting real APIs.
    _jib_mod._vertex_client = None
    _jib_mod._gemini_client = None
    import engine.self_improvement as _si_mod  # noqa: E402
    _si_mod._vertex_client = None
    _si_mod._gemini_client = None
    import engine.mandate_executor as _me_mod  # noqa: E402
    _me_mod._vertex_client = None
    _me_mod._gemini_client = None
    import engine.conversation as _conv_mod  # noqa: E402
    _conv_mod._vertex_client = None
    _conv_mod._gemini_client = None

from engine.self_improvement import SelfImprovementEngine, SelfImprovementReport, _COMPONENTS  # noqa: E402


_WAVE_OF: dict[str, int] = {c["component"]: c["wave"] for c in _COMPONENTS}
_WAVE_LABELS: dict[int, str] = {
    1: "Wave 1 [core-security]",
    2: "Wave 2 [performance]",
    3: "Wave 3 [meta-analysis]",
    4: "Wave 4 [orchestration]",
    5: "Wave 5 [intelligence-layer]",
    6: "Wave 6 [advanced-execution]",
}
_W = 72
_REPORT_PATH = _ROOT / "cycle_run_report.json"


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class CycleRunSummary:
    """Aggregated result across all cycles."""

    run_id: str
    ts: str
    total_cycles: int
    live_mode: bool
    cycle_reports: list[dict[str, Any]]
    # Per-component best value score across all cycles
    best_value_scores: dict[str, float] = field(default_factory=dict)
    # Components that improved their value score between cycles
    improving_components: list[str] = field(default_factory=list)
    # Components whose suggestions were semantically stagnant (cosine > 0.95)
    # across the last two consecutive cycles.  Replaces the old numeric-score
    # equality check which produced false positives in offline mode.
    stagnating_components: list[str] = field(default_factory=list)
    # Unique JIT signals harvested across all cycles (deduped)
    all_signals: list[str] = field(default_factory=list)
    total_signals_raw: int = 0
    total_latency_ms: float = 0.0
    final_verdict: str = "pass"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "ts": self.ts,
            "total_cycles": self.total_cycles,
            "live_mode": self.live_mode,
            "cycle_reports": self.cycle_reports,
            "best_value_scores": {k: round(v, 3) for k, v in self.best_value_scores.items()},
            "improving_components": self.improving_components,
            "stagnating_components": self.stagnating_components,
            "all_signals": self.all_signals[:20],
            "total_signals_raw": self.total_signals_raw,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "final_verdict": self.final_verdict,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    print(f"\n{'='*_W}")
    print(f"  {title}")
    print(f"{'='*_W}")


def _section(title: str) -> None:
    pad = max(0, _W - 6 - len(title))
    print(f"\n──── {title} {'─'*pad}")


def _print_report(cycle_num: int, report: SelfImprovementReport) -> None:
    """Pretty-print a single cycle's report."""
    elapsed = report.latency_ms / 1000
    _section(f"Cycle {cycle_num} · {report.improvement_id}")
    print(f"  Elapsed  : {elapsed:.2f}s")
    print(f"  Verdict  : {report.refinement_verdict.upper()}")
    print(f"  Components: {report.components_assessed}  "
          f"signals={report.total_signals}  "
          f"success={report.refinement_success_rate:.0%}")

    assessments_by_wave = sorted(
        report.assessments,
        key=lambda a: (_WAVE_OF.get(a.component, 99), a.component),
    )
    current_wave = None
    for a in assessments_by_wave:
        wave = _WAVE_OF.get(a.component, 99)
        if wave != current_wave:
            current_wave = wave
            label = _WAVE_LABELS.get(wave, f"Wave {wave}")
            print(f"\n  {label}")
        status = "✓" if (a.tribunal_passed and a.execution_success) else "✗"
        val_bar = "█" * int(a.value_score * 10) + "░" * \
            (10 - int(a.value_score * 10))
        print(
            f"    {status}  {a.component:<20}  "
            f"conf={a.original_confidence:.2f}→{a.boosted_confidence:.2f}  "
            f"value=[{val_bar}] {a.value_score:.2f}"
        )
        if a.value_rationale:
            print(f"         rationale: {a.value_rationale[:65]}")
        for sig in a.jit_signals[:1]:
            print(f"         signal   : {sig[:65]}")
        if a.suggestions:
            print(f"         suggest  : {a.suggestions[0][:65]}")


def _print_inter_cycle_analysis(
    cycle_num: int,
    prev_scores: dict[str, float],
    curr_scores: dict[str, float],
) -> None:
    """Compare value scores between two consecutive cycles."""
    if not prev_scores:
        return
    _section(f"Inter-cycle Δ value scores (cycle {cycle_num-1} → {cycle_num})")
    for comp in sorted(curr_scores):
        prev = prev_scores.get(comp, 0.0)
        curr = curr_scores[comp]
        delta = curr - prev
        arrow = "▲" if delta > 0.01 else ("▼" if delta < -0.01 else "─")
        print(f"    {arrow}  {comp:<22}  {prev:.2f} → {curr:.2f}  ({delta:+.2f})")


def _print_final_summary(summary: CycleRunSummary) -> None:
    _header(f"Batch Run Complete  [{summary.run_id}]")
    print(f"  Cycles   : {summary.total_cycles}")
    print(f"  Total latency : {summary.total_latency_ms/1000:.1f}s")
    print(f"  Unique signals: {len(summary.all_signals)}")
    print(f"  Verdict  : {summary.final_verdict.upper()}")

    _section("Best value scores (highest achieved across all cycles)")
    for comp, score in sorted(summary.best_value_scores.items(),
                              key=lambda x: -x[1]):
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        priority = "HIGH  " if score >= 0.7 else (
            "MEDIUM" if score >= 0.4 else "LOW   ")
        print(f"  {priority}  {comp:<22}  [{bar}] {score:.2f}")

    if summary.improving_components:
        _section("Components with improving value scores across cycles")
        for c in summary.improving_components:
            print(f"    ↑  {c}")

    if summary.stagnating_components:
        _section("Stagnating components (unchanged score — consider live mode)")
        for c in summary.stagnating_components:
            print(f"    →  {c}")

    _section("Top JIT SOTA signals (deduped, cross-cycle)")
    for i, sig in enumerate(summary.all_signals[:10], 1):
        print(f"  {i:2}. {sig[:68]}")

    print()
    print(f"  Full report: {_REPORT_PATH}")
    print()


# ── Runner ────────────────────────────────────────────────────────────────────


def run_batch(n_cycles: int = 3) -> CycleRunSummary:
    """Run ``n_cycles`` SelfImprovementEngine cycles sequentially.

    Returns a CycleRunSummary aggregating value scores, signal deduplication,
    trend detection (improving / stagnating components), and a final verdict.
    """
    run_id = f"batch-{uuid.uuid4().hex[:8]}"
    t_all = time.monotonic()

    _header(
        f"TooLoo V2 — Batch Improvement Cycle Runner  [{run_id}]"
    )
    print(f"  Cycles : {n_cycles}")
    print(
        f"  Mode   : {'LIVE (Vertex/Gemini)' if _LIVE_MODE else 'OFFLINE (structured catalogue)'}")
    print(f"  Components: {len(_COMPONENTS)} across 6 waves")
    print("  Parallelism: max_workers=6 per wave")
    print()

    cycle_reports: list[dict[str, Any]] = []
    all_scores_by_cycle: list[dict[str, float]] = []
    all_signals_seen: set[str] = set()
    all_signals_list: list[str] = []
    total_signals_raw = 0

    engine = SelfImprovementEngine()
    # Live-mode TTL pin: ensure JIT cache doesn't expire mid-batch.
    # If the configured TTL is shorter than the estimated run window
    # (n_cycles × 10 min is a safe upper-bound), extend it so Cycle 2+
    # can reuse Cycle 1's warm cache instead of re-querying Gemini cold.
    if _LIVE_MODE:
        from engine.config import MODEL_GARDEN_CACHE_TTL as _cfg_ttl
        _min_ttl = max(_cfg_ttl, n_cycles * 600)
        engine._booster._live_cache_ttl_seconds = _min_ttl

    # Semantic stagnation detector.  Uses VectorStore cosine similarity to
    # compare the suggestions text emitted in the last two consecutive cycles.
    # Threshold 0.95 means “essentially the same output” (signal: stagnating).
    _STAGNATION_THRESHOLD: float = 0.95
    # Maps component name → dict of cycle texts indexed by cycle number
    _suggestions_by_cycle: list[dict[str, str]] = []
    for cycle_num in range(1, n_cycles + 1):
        print(f"▶  Cycle {cycle_num}/{n_cycles} …")
        report = engine.run()

        cycle_reports.append(report.to_dict())
        total_signals_raw += report.total_signals

        # Collect value scores for this cycle
        curr_scores: dict[str, float] = {
            a.component: a.value_score for a in report.assessments
        }
        all_scores_by_cycle.append(curr_scores)

        # Collect flattened suggestions text per component for semantic diff
        curr_suggestions: dict[str, str] = {
            a.component: " ".join(a.suggestions)
            for a in report.assessments
            if a.suggestions
        }
        _suggestions_by_cycle.append(curr_suggestions)

        # Deduplicate JIT signals
        for a in report.assessments:
            for sig in a.jit_signals:
                if sig not in all_signals_seen:
                    all_signals_seen.add(sig)
                    all_signals_list.append(sig)

        _print_report(cycle_num, report)

        if len(all_scores_by_cycle) >= 2:
            _print_inter_cycle_analysis(
                cycle_num,
                all_scores_by_cycle[-2],
                curr_scores,
            )

    # ── Aggregate ────────────────────────────────────────────────────────────
    # Best value score per component across all cycles
    best_scores: dict[str, float] = {}
    for scores in all_scores_by_cycle:
        for comp, score in scores.items():
            if score > best_scores.get(comp, 0.0):
                best_scores[comp] = score

    # Improving: value score rose between consecutive cycles in ≥ 1 pair
    improving: list[str] = []
    stagnating: list[str] = []

    if len(all_scores_by_cycle) >= 2:
        for comp in best_scores:
            score_series = [s.get(comp, 0.0) for s in all_scores_by_cycle]
            any_increase = any(
                score_series[i] > score_series[i - 1] + 0.01
                for i in range(1, len(score_series))
            )
            if any_increase:
                improving.append(comp)

    # Semantic stagnation: compare suggestions text from the last two cycles
    # using VectorStore cosine similarity.  Numeric score equality is a poor
    # proxy in offline mode (all scores are near-identical heuristics).
    if len(_suggestions_by_cycle) >= 2:
        _vs = VectorStore(dup_threshold=_STAGNATION_THRESHOLD)
        for comp in best_scores:
            text_prev = _suggestions_by_cycle[-2].get(comp, "")
            text_curr = _suggestions_by_cycle[-1].get(comp, "")
            if not text_prev or not text_curr:
                continue
            # Add previous cycle's text as the reference document
            _vs.add(f"{comp}-prev", text_prev)
            results = _vs.search(text_curr, top_k=1,
                                 threshold=_STAGNATION_THRESHOLD)
            if results:
                stagnating.append(comp)
            # Reset store for next component
            _vs.remove(f"{comp}-prev")

    # Final verdict: fail if >25% of components have value_score < 0.3 in last cycle
    last_scores = all_scores_by_cycle[-1] if all_scores_by_cycle else {}
    low_value_count = sum(1 for s in last_scores.values() if s < 0.3)
    final_verdict = "fail" if low_value_count > len(
        last_scores) * 0.25 else "pass"

    summary = CycleRunSummary(
        run_id=run_id,
        ts=datetime.now(UTC).isoformat(),
        total_cycles=n_cycles,
        live_mode=_LIVE_MODE,
        cycle_reports=cycle_reports,
        best_value_scores=best_scores,
        improving_components=sorted(improving),
        stagnating_components=sorted(stagnating),
        all_signals=all_signals_list,
        total_signals_raw=total_signals_raw,
        total_latency_ms=round((time.monotonic() - t_all) * 1000, 2),
        final_verdict=final_verdict,
    )

    _print_final_summary(summary)

    _REPORT_PATH.write_text(json.dumps(summary.to_dict(), indent=2))
    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_cycles = int(os.environ.get("RUN_CYCLES_N", "3"))
    parser = argparse.ArgumentParser(
        prog="run_cycles.py",
        description="TooLoo V2 — Batch Improvement Cycle Runner",
    )
    parser.add_argument(
        "--cycles", "-n",
        type=int,
        default=default_cycles,
        help=f"Number of SelfImprovement cycles to run (default {default_cycles}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = run_batch(n_cycles=args.cycles)
    return 0 if summary.final_verdict in ("pass", "warn") else 1


if __name__ == "__main__":
    raise SystemExit(main())
