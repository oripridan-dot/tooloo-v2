#!/usr/bin/env python3
"""Run TooLoo's targeted self-audit and autonomous improvement loop.

Workflow:
  1. Run a baseline benchmark across the 17 engine components.
  2. Run a focused self-improvement cycle.
  3. Select the weakest components and feed them into Ouroboros.
  4. Run the benchmark again and calculate deltas.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmark_metrics import BenchmarkReport, run_benchmark
from engine.config import AUTONOMOUS_EXECUTION_ENABLED
from engine.self_improvement import SelfImprovementEngine, _COMPONENT_SOURCE
from ouroboros_cycle import OuroborosCycle, _ALLOWED_ENGINE_PATHS

_ROOT = Path(__file__).resolve().parent


@dataclass
class AuditDelta:
    efficiency_delta: float
    quality_delta: float
    accuracy_delta: float
    avg_speed_delta_ms: float
    executor_p50_delta_ms: float
    executor_p90_delta_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "efficiency_delta": round(self.efficiency_delta, 3),
            "quality_delta": round(self.quality_delta, 3),
            "accuracy_delta": round(self.accuracy_delta, 3),
            "avg_speed_delta_ms": round(self.avg_speed_delta_ms, 2),
            "executor_p50_delta_ms": round(self.executor_p50_delta_ms, 2),
            "executor_p90_delta_ms": round(self.executor_p90_delta_ms, 2),
        }


def _component_priority(benchmark: BenchmarkReport) -> list[str]:
    ranked = sorted(
        benchmark.components,
        key=lambda component: (
            (component.efficiency + component.quality + component.accuracy) / 3,
            component.speed_ms,
        ),
    )
    selected: list[str] = []
    for component in ranked:
        rel_path = _COMPONENT_SOURCE.get(component.component, "")
        if rel_path and rel_path in _ALLOWED_ENGINE_PATHS and rel_path not in selected:
            selected.append(rel_path)
    return selected


def _compute_delta(before: BenchmarkReport, after: BenchmarkReport) -> AuditDelta:
    return AuditDelta(
        efficiency_delta=after.aggregate.avg_efficiency - before.aggregate.avg_efficiency,
        quality_delta=after.aggregate.avg_quality - before.aggregate.avg_quality,
        accuracy_delta=after.aggregate.avg_accuracy - before.aggregate.avg_accuracy,
        avg_speed_delta_ms=after.aggregate.avg_speed_ms - before.aggregate.avg_speed_ms,
        executor_p50_delta_ms=after.aggregate.executor_p50_ms - before.aggregate.executor_p50_ms,
        executor_p90_delta_ms=after.aggregate.executor_p90_ms - before.aggregate.executor_p90_ms,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute TooLoo targeted self-audit")
    parser.add_argument(
        "--focus",
        default="efficiency,quality,accuracy,speed",
        help="Optimization focus for the audit and self-improvement cycle",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="How many weakest allowed components to feed into Ouroboros",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan improvements without attempting autonomous file writes",
    )
    parser.add_argument(
        "--output",
        default="targeted_self_audit_report.json",
        help="Path to write the combined audit report",
    )
    args = parser.parse_args()

    focus = args.focus
    baseline = run_benchmark(focus)

    si_engine = SelfImprovementEngine(optimization_focus=focus)
    self_improvement = si_engine.run(run_regression_gate=False)

    candidates = _component_priority(baseline)[:max(1, args.top_k)]
    cycle = OuroborosCycle(
        god_mode=AUTONOMOUS_EXECUTION_ENABLED and not args.dry_run,
        dry_run=args.dry_run,
        component_filter=candidates,
    )
    ouroboros = cycle.run()

    post = run_benchmark(focus)
    delta = _compute_delta(baseline, post)

    report = {
        "run_id": f"audit-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "ts": datetime.now(UTC).isoformat(),
        "focus": focus,
        "baseline": baseline.to_dict(),
        "self_improvement": self_improvement.to_dict(),
        "selected_components": candidates,
        "ouroboros": ouroboros.to_dict(),
        "post_benchmark": post.to_dict(),
        "delta": delta.to_dict(),
    }
    output_path = (_ROOT / args.output).resolve()
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Targeted self-audit complete: {report['run_id']}")
    print(f"Focus             : {focus}")
    print(f"Selected components: {', '.join(candidates) if candidates else '(none)'}")
    print(f"Ouroboros verdict : {ouroboros.overall_verdict}")
    print(
        "Delta             : "
        f"eff={delta.efficiency_delta:+.3f}  "
        f"qual={delta.quality_delta:+.3f}  "
        f"acc={delta.accuracy_delta:+.3f}  "
        f"avg_speed={delta.avg_speed_delta_ms:+.2f}ms"
    )
    print(f"Report            : {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())