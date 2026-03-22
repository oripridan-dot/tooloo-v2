#!/usr/bin/env python3
"""
run_calibration_cycles.py — TooLoo V2 Precision Calibration Runner

Executes 3 cycles of calibration across all 28 engine components,
benchmarking each against real published SOTA data and computing
precise mathematical improvement proofs for all 16D, SOTA, and JIT
parameters.

Usage:
    python run_calibration_cycles.py
    python run_calibration_cycles.py --component jit_booster tribunal router
    python run_calibration_cycles.py --summary-only
    python run_calibration_cycles.py --apply-jit-params

Outputs:
    psyche_bank/calibration_proof.json         (full mathematical proof)
    psyche_bank/jit_calibration.json           (JIT parameter recommendations)
    psyche_bank/calibration_rules.cog.json     (PsycheBank rule injections)
    calibration_cycles_report.json             (workspace-level report)
"""
from __future__ import annotations
from engine.sota_benchmarks import (
    SOTA_CATALOGUE,
    COMPONENT_DOMAIN_MAP,
    DIMENSION_WEIGHTS_16D,
)
from engine.calibration_engine import (
    CalibrationEngine,
    CalibrationCycleReport,
    _COMPONENT_BASE_CONFIDENCE,
)

import argparse
import json
import re
import sys
from pathlib import Path

# Ensure repo root is on path
_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))


def print_banner() -> None:
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║      TooLoo V2 — 3-CYCLE PRECISION CALIBRATION ENGINE               ║
║                                                                      ║
║  Cycle 1 : SOTA Baseline Harvest (real published benchmarks)         ║
║  Cycle 2 : 16D Math Proof Engine (weighted composite deltas)         ║
║  Cycle 3 : JIT Parameter Calibration (Ebbinghaus recency + boost)   ║
║                                                                      ║
║  Source benchmarks: HumanEval, SWE-bench, MMLU, DORA 2024,          ║
║  MLPerf v4.1, OWASP 2025, MTEB, BEIR, GitHub Research, AutoGen,     ║
║  Constitutional AI v2, SWE-agent, Dask, Ray, GAIA, WebArena.         ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def print_benchmark_preview() -> None:
    """Display the SOTA benchmark catalogue statistics before running."""
    domains: dict[str, int] = {}
    total_gap = 0.0
    for b in SOTA_CATALOGUE:
        domains[b.domain] = domains.get(b.domain, 0) + 1
        total_gap += b.gap

    print(f"  SOTA Benchmark Catalogue: {len(SOTA_CATALOGUE)} benchmarks")
    print(f"  Domains: {len(domains)}")
    for d, n in sorted(domains.items()):
        print(f"    {d:<20} {n} benchmarks")
    print(f"  Mean absolute SOTA gap : {total_gap/len(SOTA_CATALOGUE):.4f}")
    print(f"  Components to calibrate: {len(COMPONENT_DOMAIN_MAP)}")
    print()


def apply_jit_params(report: CalibrationCycleReport) -> bool:
    """
    Apply calibrated JIT parameters back to engine/jit_booster.py.

    Updates:
      BOOST_PER_SIGNAL: float = <calibrated>
      MAX_BOOST_DELTA:  float = <calibrated>
    """
    booster_path = _REPO_ROOT / "engine" / "jit_booster.py"
    if not booster_path.exists():
        print("  [WARN] engine/jit_booster.py not found — skipping param apply.")
        return False

    content = booster_path.read_text(encoding="utf-8")
    bps = report.recommended_boost_per_signal
    mbd = report.recommended_max_boost

    # Patch BOOST_PER_SIGNAL
    content_new = re.sub(
        r"(BOOST_PER_SIGNAL:\s*float\s*=\s*)[\d.]+",
        f"\\g<1>{bps:.4f}",
        content,
    )
    # Patch MAX_BOOST_DELTA
    content_new = re.sub(
        r"(MAX_BOOST_DELTA:\s*float\s*=\s*)[\d.]+",
        f"\\g<1>{mbd:.4f}",
        content_new,
    )

    if content_new == content:
        print(
            "  [INFO] JIT parameters unchanged "
            f"(BOOST_PER_SIGNAL already {bps:.4f})."
        )
        return False

    booster_path.write_text(content_new, encoding="utf-8")
    print(
        f"  ✓ Applied JIT params to engine/jit_booster.py:\n"
        f"    BOOST_PER_SIGNAL = {bps:.4f}  (was 0.0500)\n"
        f"    MAX_BOOST_DELTA  = {mbd:.4f}  (was 0.2500)"
    )
    return True


def print_proof_table(report: CalibrationCycleReport) -> None:
    """Print a compact proof table: component × cycle metrics."""
    print(f"\n{'─'*90}")
    print(
        f"  {'Component':<26} "
        f"{'Alignment':>10} "
        f"{'Δ16D pp':>9} "
        f"{'IPA':>7} "
        f"{'JIT gain pp':>11} "
        f"{'BPS':>7}"
    )
    print(f"  {'─'*26} {'─'*10} {'─'*9} {'─'*7} {'─'*11} {'─'*7}")

    proof_map = {p.component: p for p in report.cycle_2_proofs}
    jit_map = {j.component: j for j in report.cycle_3_jit}
    base_map = {b.component: b for b in report.cycle_1_baselines}

    for comp in sorted(proof_map.keys()):
        p = proof_map[comp]
        j = jit_map[comp]
        b = base_map[comp]
        jit_gain = (j.jit_composite - j.base_confidence) * 100
        print(
            f"  {comp:<26} "
            f"{b.alignment_score:10.4f} "
            f"{p.delta_16d*100:+9.2f} "
            f"{p.impact_per_action:7.2f}x "
            f"{jit_gain:+11.2f} "
            f"{j.boost_per_signal_calibrated:7.4f}"
        )

    print(f"{'─'*90}")
    print(
        f"  {'SYSTEM TOTALS / MEANS':<26} "
        f"{report.system_alignment_after:10.4f} "
        f"{report.system_16d_gain*100:+9.2f} "
        f"{'':>7} "
        f"{report.system_jit_gain*100:+11.2f} "
        f"{report.recommended_boost_per_signal:7.4f}"
    )
    print(f"{'─'*90}\n")


def print_16d_proof_detail(report: CalibrationCycleReport, component: str) -> None:
    """Print the full 16D proof for a single component."""
    proof = next(
        (p for p in report.cycle_2_proofs if p.component == component), None)
    if not proof:
        print(f"  [WARN] No proof found for component '{component}'")
        return

    print(f"\n  16D PROOF DETAIL — {component}")
    print(f"  {'─'*68}")
    print(f"  Cycle-1 alignment    : {proof.cycle_1_alignment:.4f}")
    print(f"  Base composite       : {proof.base_composite_16d:.4f}")
    print(f"  Calibrated composite : {proof.calibrated_composite_16d:.4f}")
    print(f"  Δ16D                 : +{proof.delta_16d*100:.2f} pp")
    print(f"  Impact-per-Action    : {proof.impact_per_action:.2f}×")
    print(f"  {'─'*68}")
    print(
        f"  {'Dimension':<22} "
        f"{'Base':>6} {'Cal':>6} {'Δ':>7} {'Weight':>7} {'WBoost':>7}"
    )
    print(f"  {'─'*22} {'─'*6} {'─'*6} {'─'*7} {'─'*7} {'─'*7}")
    for d in proof.dimension_deltas:
        print(
            f"  {d.dimension:<22} "
            f"{d.base_score:6.3f} {d.calibrated_score:6.3f} "
            f"{d.delta:+7.4f} "
            f"{d.weight:7.3f} {d.weight_boost:7.4f}"
        )
    print(f"\n  CERTIFICATE:\n  {proof.proof_certificate}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TooLoo V2 — 3-Cycle Precision Calibration Runner"
    )
    parser.add_argument(
        "--component",
        nargs="*",
        metavar="NAME",
        help="Only calibrate specific components (default: all 28)",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print summary without running (shows benchmark catalogue)",
    )
    parser.add_argument(
        "--apply-jit-params",
        action="store_true",
        help="Apply calibrated BOOST_PER_SIGNAL + MAX_BOOST_DELTA to jit_booster.py",
    )
    parser.add_argument(
        "--detail",
        metavar="COMPONENT",
        help="Print full 16D proof detail for one component after run",
    )
    parser.add_argument(
        "--output",
        default="calibration_cycles_report.json",
        metavar="FILE",
        help="Output report JSON path (default: calibration_cycles_report.json)",
    )
    args = parser.parse_args()

    print_banner()
    print_benchmark_preview()

    if args.summary_only:
        print("  --summary-only: showing benchmark catalogue. No cycles run.")
        print("\n  DIMENSION WEIGHTS (16D research-calibrated):")
        for dim, w in sorted(DIMENSION_WEIGHTS_16D.items(), key=lambda x: -x[1]):
            print(f"    {dim:<24}  weight={w:.2f}")
        return 0

    # ── Select components ─────────────────────────────────────────────────────
    components = None
    if args.component:
        valid = set(COMPONENT_DOMAIN_MAP.keys())
        for c in args.component:
            if c not in valid:
                print(
                    f"  [ERROR] Unknown component '{c}'. Valid: {sorted(valid)}")
                return 1
        components = args.component
        print(f"  Calibrating {len(components)} component(s): {components}")

    # ── Run 3 cycles ──────────────────────────────────────────────────────────
    engine = CalibrationEngine(components=components)
    report = engine.run_3_cycles()

    # ── Persist proof artefacts ───────────────────────────────────────────────
    engine.persist(report)

    # ── Workspace-level report ────────────────────────────────────────────────
    output_path = _REPO_ROOT / args.output
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Full report → {output_path}")

    # ── Print proof table ─────────────────────────────────────────────────────
    print_proof_table(report)

    # ── Optional: full 16D detail for one component ───────────────────────────
    if args.detail:
        print_16d_proof_detail(report, args.detail)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n  CALIBRATION SUMMARY")
    print("  " + "─" * 66)
    for line in report.summary.split("\n"):
        print(f"  {line}")

    # ── Apply JIT params to jit_booster.py ───────────────────────────────────
    if args.apply_jit_params:
        print("\n  Applying calibrated JIT parameters...")
        apply_jit_params(report)

    print("\n  Run complete.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
