#!/usr/bin/env python3
"""Self-improvement cycle runner.

Single cycle (default) or multi-cycle batch mode via --cycles N.
Value scores are printed for each component so you can see at a glance
which improvements are highest-priority.

Usage:
    python _run_self_improve.py              # 1 cycle
    python _run_self_improve.py --cycles 3   # 3 cycles with trend analysis
"""

import argparse
import os

import engine.jit_booster as _jib_mod
from engine.self_improvement import SelfImprovementEngine, _COMPONENTS

# Offline patch — mirror conftest.py so cycles work without API keys
if os.environ.get("TOOLOO_LIVE_TESTS", "").lower() not in ("1", "true", "yes"):
    _jib_mod._vertex_client = None
    _jib_mod._gemini_client = None


W = 72
_wave_of = {c["component"]: c["wave"] for c in _COMPONENTS}
_wave_labels = {
    1: "Wave 1 [core-security]",
    2: "Wave 2 [performance]",
    3: "Wave 3 [meta-analysis]",
    4: "Wave 4 [orchestration]",
    5: "Wave 5 [intelligence-layer]",
    6: "Wave 6 [advanced-execution]",
}


def _run_one(cycle_num: int, total: int, focus: str) -> None:
    print(f"\n{'='*W}")
    print(f"  TooLoo V2 — Self-Improvement Cycle {cycle_num}/{total}")
    print(
        f"  Scope: {len(_COMPONENTS)} nodes · 6 waves · max x6 parallel · deep-parallel")
    print(f"  Focus: {focus}")
    print(f"{'='*W}")

    engine = SelfImprovementEngine(optimization_focus=focus)
    report = engine.run()

    elapsed_s = report.latency_ms / 1000
    print(f"\nRun ID  : {report.improvement_id}")
    print(f"Time    : {report.ts}")
    print(f"Elapsed : {elapsed_s:.2f}s")
    print(f"Verdict : {report.refinement_verdict.upper()}")
    print(f"Results : {report.components_assessed} components · {report.waves_executed} waves · "
          f"success={report.refinement_success_rate:.0%}")
    print(f"Signals : {report.total_signals} JIT SOTA signals harvested\n")

    assessments_by_wave = sorted(
        report.assessments,
        key=lambda a: (_wave_of.get(a.component, 99), a.component),
    )

    current_wave = None
    for a in assessments_by_wave:
        wave = _wave_of.get(a.component, 99)
        if wave != current_wave:
            current_wave = wave
            label = _wave_labels.get(wave, f"Wave {wave}")
            print(f"──── {label} {'─'*(W - 6 - len(label))}")
        status = "✓ PASS" if (
            a.tribunal_passed and a.execution_success) else "✗ FAIL"
        val_bar = "█" * int(a.value_score * 10) + "░" * \
            (10 - int(a.value_score * 10))
        print(
            f"  {status}  {a.component:<20}  "
            f"conf={a.original_confidence:.2f}→{a.boosted_confidence:.2f}  "
            f"value=[{val_bar}]{a.value_score:.2f}  jit={a.jit_source}"
        )
        for sig in a.jit_signals[:2]:
            print(f"           ↳ {sig[:74]}")
        for sug in (a.suggestions or [])[:1]:
            print(f"           → {sug[:74]}")
        print()

    print(f"──── Top Recommendations {'─'*(W - 26)}")
    for i, rec in enumerate(report.top_recommendations, 1):
        print(f"  {i:2}. {rec}")

    print(f"\n──── Value Score Summary (priority order) {'─'*(W - 43)}")
    for a in sorted(report.assessments, key=lambda x: -x.value_score):
        priority = "HIGH  " if a.value_score >= 0.7 else (
            "MEDIUM" if a.value_score >= 0.4 else "LOW   ")
        print(
            f"  {priority}  {a.component:<22}  {a.value_score:.2f}  {a.value_rationale[:40]}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="_run_self_improve.py",
        description="TooLoo V2 Self-Improvement Cycle Runner",
    )
    parser.add_argument("--cycles", "-n", type=int, default=1,
                        help="Number of improvement cycles to run (default 1). "
                             "Use run_cycles.py for richer multi-cycle analysis.")
    parser.add_argument(
        "--focus",
        type=str,
        default="balanced",
        help="Optimization focus, e.g. balanced or efficiency,quality,accuracy,speed",
    )
    args = parser.parse_args()

    for i in range(1, args.cycles + 1):
        _run_one(i, args.cycles, args.focus)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
