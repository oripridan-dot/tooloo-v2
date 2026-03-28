# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining benchmark_metrics.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.407413
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

#!/usr/bin/env python3
"""Targeted self-audit benchmark for TooLoo V2's 17 engine components.

Measures four metrics across the self-improvement component manifest:
  - efficiency
  - quality
  - accuracy
  - speed

The first three are scored via ``engine.sandbox.DimensionScorer``.
Speed is sourced from the existing latency instrumentation in
``engine.executor.JITExecutor`` and ``engine.refinement.RefinementLoop``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import engine.jit_booster as _jib_mod
import engine.self_improvement as _si_mod
from engine.executor import ExecutionResult
from engine.refinement import RefinementLoop
from engine.sandbox import DimensionScorer
from engine.self_improvement import SelfImprovementEngine, _COMPONENTS

if os.environ.get("TOOLOO_LIVE_TESTS", "").lower() not in ("1", "true", "yes"):
    _jib_mod._vertex_client = None
    _jib_mod._gemini_client = None
    _si_mod._vertex_client = None
    _si_mod._gemini_client = None


@dataclass
class ComponentBenchmark:
    component: str
    wave: int
    efficiency: float
    quality: float
    accuracy: float
    speed_ms: float
    value_score: float
    jit_source: str
    suggestions: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AggregateBenchmark:
    component_count: int
    avg_efficiency: float
    avg_quality: float
    avg_accuracy: float
    avg_speed_ms: float
    executor_p50_ms: float
    executor_p90_ms: float
    refinement_p50_ms: float
    refinement_p90_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkReport:
    benchmark_id: str
    ts: str
    focus: str
    aggregate: AggregateBenchmark
    components: list[ComponentBenchmark]

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "ts": self.ts,
            "focus": self.focus,
            "aggregate": self.aggregate.to_dict(),
            "components": [component.to_dict() for component in self.components],
        }


def run_benchmark(focus: str = "balanced") -> BenchmarkReport:
    engine = SelfImprovementEngine(optimization_focus=focus)
    report = engine.run(run_regression_gate=False)
    scorer = DimensionScorer()
    wave_map = {entry["component"]: entry["wave"] for entry in _COMPONENTS}

    components: list[ComponentBenchmark] = []
    refinement_inputs: list[ExecutionResult] = []
    for assessment in report.assessments:
        verdict = "pass" if assessment.execution_success and assessment.tribunal_passed else "fail"
        dimensions = scorer.score(
            original_conf=assessment.original_confidence,
            boosted_conf=assessment.boosted_confidence,
            tribunal_passed=assessment.tribunal_passed,
            refinement_verdict=verdict,
            exec_success_rate=1.0 if assessment.execution_success else 0.0,
        )
        dim_map = {dimension.name: dimension.score for dimension in dimensions}
        components.append(ComponentBenchmark(
            component=assessment.component,
            wave=wave_map.get(assessment.component, 0),
            efficiency=dim_map.get("efficiency", 0.0),
            quality=dim_map.get("quality", 0.0),
            accuracy=dim_map.get("accuracy", 0.0),
            speed_ms=round(assessment.execution_latency_ms, 2),
            value_score=assessment.value_score,
            jit_source=assessment.jit_source,
            suggestions=len(assessment.suggestions),
        ))
        refinement_inputs.append(ExecutionResult(
            mandate_id=assessment.component,
            success=assessment.execution_success,
            output=assessment.component,
            latency_ms=assessment.execution_latency_ms,
        ))

    aggregate_refinement = RefinementLoop().evaluate(refinement_inputs)
    component_count = len(components) or 1
    aggregate = AggregateBenchmark(
        component_count=len(components),
        avg_efficiency=round(sum(component.efficiency for component in components) / component_count, 3),
        avg_quality=round(sum(component.quality for component in components) / component_count, 3),
        avg_accuracy=round(sum(component.accuracy for component in components) / component_count, 3),
        avg_speed_ms=round(sum(component.speed_ms for component in components) / component_count, 2),
        executor_p50_ms=round(engine._executor.latency_p50() or 0.0, 2),
        executor_p90_ms=round(engine._executor.latency_p90() or 0.0, 2),
        refinement_p50_ms=round(aggregate_refinement.p50_latency_ms, 2),
        refinement_p90_ms=round(aggregate_refinement.p90_latency_ms, 2),
    )
    return BenchmarkReport(
        benchmark_id=f"bm-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        ts=datetime.now(UTC).isoformat(),
        focus=focus,
        aggregate=aggregate,
        components=sorted(components, key=lambda component: (component.wave, component.component)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark TooLoo V2 engine metrics")
    parser.add_argument("--focus", default="balanced", help="Optimization focus string")
    parser.add_argument(
        "--output",
        default="benchmark_metrics_report.json",
        help="Path to write the JSON benchmark report",
    )
    args = parser.parse_args()

    benchmark = run_benchmark(args.focus)
    output_path = (_ROOT / args.output).resolve()
    output_path.write_text(json.dumps(benchmark.to_dict(), indent=2), encoding="utf-8")

    print(f"Benchmark: {benchmark.benchmark_id}")
    print(f"Focus    : {benchmark.focus}")
    print(f"Components: {benchmark.aggregate.component_count}")
    print(
        "Averages  : "
        f"eff={benchmark.aggregate.avg_efficiency:.3f}  "
        f"qual={benchmark.aggregate.avg_quality:.3f}  "
        f"acc={benchmark.aggregate.avg_accuracy:.3f}  "
        f"speed={benchmark.aggregate.avg_speed_ms:.2f}ms"
    )
    print(
        "Latency   : "
        f"executor p50={benchmark.aggregate.executor_p50_ms:.2f}ms  "
        f"executor p90={benchmark.aggregate.executor_p90_ms:.2f}ms  "
        f"refine p50={benchmark.aggregate.refinement_p50_ms:.2f}ms  "
        f"refine p90={benchmark.aggregate.refinement_p90_ms:.2f}ms"
    )
    print(f"Report    : {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())