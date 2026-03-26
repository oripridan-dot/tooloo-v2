#!/usr/bin/env python3
"""
scripts/benchmark_runner.py — Runtime Performance Benchmark for TooLoo V2.

Measures actual runtime performance of engine components:
  - Import latency
  - Initialization time
  - Function execution latency
  - Throughput (ops/sec)
  - Memory footprint

Results feed back into the calibration engine to drive real 16D score
movement during the SOTA training loop.

Usage:
    python scripts/benchmark_runner.py           # full benchmark
    python scripts/benchmark_runner.py --quick   # fast smoke test
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ── Project root ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Patch LLM for offline benchmarking ────────────────────────────────────────
os.environ.setdefault("TOOLOO_BENCHMARK_MODE", "1")


@dataclass
class ComponentBenchmark:
    """Benchmark results for a single component."""
    component: str
    import_ms: float = 0.0
    init_ms: float = 0.0
    exec_ms: float = 0.0
    memory_kb: float = 0.0
    ops_per_sec: float = 0.0
    latency_score: float = 0.0   # 0-1, lower latency = higher
    throughput_score: float = 0.0  # 0-1, higher throughput = higher
    memory_score: float = 0.0     # 0-1, lower memory = higher
    composite_perf: float = 0.0   # weighted composite
    error: str | None = None
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "import_ms": round(self.import_ms, 2),
            "init_ms": round(self.init_ms, 2),
            "exec_ms": round(self.exec_ms, 2),
            "memory_kb": round(self.memory_kb, 2),
            "ops_per_sec": round(self.ops_per_sec, 2),
            "latency_score": round(self.latency_score, 4),
            "throughput_score": round(self.throughput_score, 4),
            "memory_score": round(self.memory_score, 4),
            "composite_perf": round(self.composite_perf, 4),
            "error": self.error,
            "timestamp": self.timestamp,
        }


# ── Component → module + benchmark target mapping ────────────────────────────
BENCHMARKS: dict[str, dict[str, str]] = {
    "router":                {"module": "engine.router",                "class": "Router"},
    "tribunal":              {"module": "engine.tribunal",              "class": "Tribunal"},
    "psyche_bank":           {"module": "engine.psyche_bank",           "class": "PsycheBank"},
    "jit_booster":           {"module": "engine.jit_booster",           "class": "JITBooster"},
    "executor":              {"module": "engine.executor",              "class": "Executor"},
    "graph":                 {"module": "engine.graph",                 "class": "DependencyGraph"},
    "scope_evaluator":       {"module": "engine.scope_evaluator",       "class": "ScopeEvaluator"},
    "refinement":            {"module": "engine.refinement",            "class": "RefinementEngine"},
    "n_stroke":              {"module": "engine.n_stroke",              "class": "NStrokeEngine"},
    "meta_architect":        {"module": "engine.meta_architect",        "class": "MetaArchitect"},
    "model_selector":        {"module": "engine.model_selector",        "class": "ModelSelector"},
    "model_garden":          {"module": "engine.model_garden",          "class": "ModelGarden"},
    "validator_16d":         {"module": "engine.validator_16d",         "class": "Validator16D"},
    "conversation":          {"module": "engine.conversation",          "class": "ConversationManager"},
    "buddy_cache":           {"module": "engine.buddy_cache",           "class": "BuddyCache"},
    "buddy_cognition":       {"module": "engine.buddy_cognition",       "class": "BuddyCognition"},
    "branch_executor":       {"module": "engine.branch_executor",       "class": "BranchExecutor"},
    "mandate_executor":      {"module": "engine.mandate_executor",      "class": "MandateExecutor"},
    "mcp_manager":           {"module": "engine.mcp_manager",           "class": "MCPManager"},
    "self_improvement":      {"module": "engine.self_improvement",      "class": "SelfImprovementEngine"},
    "sandbox":               {"module": "engine.sandbox",               "class": "SandboxOrchestrator"},
    "vector_store":          {"module": "engine.vector_store",          "class": "VectorStore"},
    "sota_ingestion":        {"module": "engine.sota_benchmarks",       "class": None},
    "daemon":                {"module": "engine.daemon",                "class": None},
    "config":                {"module": "engine.config",                "class": None},
    "calibration":           {"module": "engine.calibration_engine",    "class": "CalibrationEngine"},
}


# ── Scoring functions ─────────────────────────────────────────────────────────

def _latency_score(ms: float) -> float:
    """Convert latency to 0-1 score (lower = better)."""
    # < 1ms = 1.0, 100ms = 0.5, 1000ms = 0.0
    if ms <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (ms / 1000.0)))


def _throughput_score(ops: float) -> float:
    """Convert ops/sec to 0-1 score (higher = better)."""
    # 10000 ops/s = 1.0, 100 ops/s = 0.5, 1 ops/s = 0.0
    if ops <= 0:
        return 0.0
    import math
    return max(0.0, min(1.0, math.log10(ops) / 4.0))


def _memory_score(kb: float) -> float:
    """Convert memory KB to 0-1 score (lower = better)."""
    # < 100KB = 1.0, 10MB = 0.5, 100MB = 0.0
    if kb <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (kb / 100_000.0)))


def benchmark_component(
    component: str,
    iterations: int = 100,
) -> ComponentBenchmark:
    """Run benchmarks for a single component."""
    info = BENCHMARKS.get(component)
    if not info:
        return ComponentBenchmark(
            component=component,
            error=f"No benchmark config for '{component}'",
            timestamp=datetime.now(UTC).isoformat(),
        )

    result = ComponentBenchmark(
        component=component,
        timestamp=datetime.now(UTC).isoformat(),
    )

    # ── Phase 1: Import latency ────────────────────────────────────────
    mod_name = info["module"]
    try:
        # Force reimport to measure cold import
        if mod_name in sys.modules:
            # Warm import — just measure module access
            t0 = time.perf_counter_ns()
            mod = sys.modules[mod_name]
            result.import_ms = (time.perf_counter_ns() - t0) / 1_000_000
        else:
            t0 = time.perf_counter_ns()
            mod = importlib.import_module(mod_name)
            result.import_ms = (time.perf_counter_ns() - t0) / 1_000_000
    except Exception as e:
        result.error = f"Import failed: {e}"
        result.import_ms = 9999.0
        _fill_scores(result)
        return result

    # ── Phase 2: Initialization latency ────────────────────────────────
    cls_name = info.get("class")
    instance = None
    if cls_name:
        cls = getattr(mod, cls_name, None)
        if cls:
            try:
                t0 = time.perf_counter_ns()
                instance = cls()
                result.init_ms = (time.perf_counter_ns() - t0) / 1_000_000
            except Exception:
                # Some classes need args — try without and record
                result.init_ms = 0.0
        else:
            result.init_ms = 0.0
    else:
        result.init_ms = 0.0

    # ── Phase 3: Execution latency (function call benchmark) ───────────
    # Find a callable to benchmark: prefer .run() or .execute() or .process()
    target_fn = None
    if instance:
        for method_name in ("calibrate", "score", "evaluate", "check", "validate"):
            fn = getattr(instance, method_name, None)
            if callable(fn):
                target_fn = fn
                break

    if target_fn is None:
        # Fall back to module-level functions
        for fn_name in ("compute_16d_alignment_vector", "weighted_alignment",
                        "get_config", "validate", "check"):
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                target_fn = fn
                break

    if target_fn:
        # Warm up
        try:
            target_fn()
        except Exception:
            pass

        # Measure
        times_ns: list[int] = []
        for _ in range(min(iterations, 50)):
            try:
                t0 = time.perf_counter_ns()
                target_fn()
                times_ns.append(time.perf_counter_ns() - t0)
            except Exception:
                break

        if times_ns:
            # Use median for stability
            times_ns.sort()
            median_ns = times_ns[len(times_ns) // 2]
            result.exec_ms = median_ns / 1_000_000
            result.ops_per_sec = 1_000_000_000 / max(median_ns, 1)
    else:
        # No callable found — benchmark module-level attribute access
        t0 = time.perf_counter_ns()
        for _ in range(iterations):
            _ = dir(mod)
        total_ns = time.perf_counter_ns() - t0
        result.exec_ms = (total_ns / iterations) / 1_000_000
        result.ops_per_sec = iterations / (total_ns / 1_000_000_000)

    # ── Phase 4: Memory footprint ──────────────────────────────────────
    tracemalloc.start()
    try:
        if cls_name and getattr(mod, cls_name, None):
            try:
                _ = getattr(mod, cls_name)()
            except Exception:
                pass
        snapshot = tracemalloc.take_snapshot()
        stats = snapshot.statistics("filename")
        # Filter to our module
        mod_file = getattr(mod, "__file__", "")
        mod_mem = sum(
            s.size for s in stats
            if mod_file and mod_file in str(s.traceback)
        )
        result.memory_kb = mod_mem / 1024
        if result.memory_kb == 0:
            # Fallback: estimate from total
            result.memory_kb = sum(s.size for s in stats[:5]) / 1024
    finally:
        tracemalloc.stop()

    _fill_scores(result)
    return result


def _fill_scores(result: ComponentBenchmark) -> None:
    """Compute normalized scores from raw measurements."""
    total_latency = result.import_ms + result.init_ms + result.exec_ms
    result.latency_score = _latency_score(total_latency)
    result.throughput_score = _throughput_score(result.ops_per_sec)
    result.memory_score = _memory_score(result.memory_kb)

    # Composite: weighted blend
    result.composite_perf = (
        0.40 * result.latency_score +
        0.35 * result.throughput_score +
        0.25 * result.memory_score
    )


def run_all_benchmarks(
    iterations: int = 50,
    quick: bool = False,
) -> dict[str, ComponentBenchmark]:
    """Run benchmarks for all components."""
    iters = 10 if quick else iterations
    results: dict[str, ComponentBenchmark] = {}

    for comp in BENCHMARKS:
        try:
            results[comp] = benchmark_component(comp, iterations=iters)
        except Exception as e:
            results[comp] = ComponentBenchmark(
                component=comp,
                error=str(e),
                timestamp=datetime.now(UTC).isoformat(),
            )

    return results


def compute_performance_confidence(
    benchmarks: dict[str, ComponentBenchmark] | None = None,
    static_base: dict[str, float] | None = None,
) -> dict[str, float]:
    """Compute performance-adjusted confidence scores.

    Blends static base confidence with live performance benchmarks.

    Returns:
        dict[component_name, confidence_score] in [0.0, 1.0]
    """
    if benchmarks is None:
        benchmarks = run_all_benchmarks(quick=True)

    if static_base is None:
        from engine.calibration_engine import _COMPONENT_BASE_CONFIDENCE
        static_base = dict(_COMPONENT_BASE_CONFIDENCE)

    # Blend: 50% static + 50% runtime performance
    STATIC_WEIGHT = 0.50
    PERF_WEIGHT = 0.50

    result: dict[str, float] = {}
    for comp, base in static_base.items():
        bench = benchmarks.get(comp)
        if bench and bench.composite_perf > 0:
            blended = STATIC_WEIGHT * base + PERF_WEIGHT * bench.composite_perf
            result[comp] = round(min(0.98, blended), 4)
        else:
            result[comp] = base

    return result


def benchmark_report(
    benchmarks: dict[str, ComponentBenchmark] | None = None,
) -> dict[str, Any]:
    """Generate a full benchmark report."""
    if benchmarks is None:
        benchmarks = run_all_benchmarks()

    avg_latency = sum(
        b.exec_ms for b in benchmarks.values() if not b.error
    ) / max(sum(1 for b in benchmarks.values() if not b.error), 1)

    avg_perf = sum(
        b.composite_perf for b in benchmarks.values() if not b.error
    ) / max(sum(1 for b in benchmarks.values() if not b.error), 1)

    errors = [b.component for b in benchmarks.values() if b.error]

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "components_benchmarked": len(benchmarks),
        "avg_exec_ms": round(avg_latency, 2),
        "avg_composite_perf": round(avg_perf, 4),
        "errors": errors,
        "component_benchmarks": {
            comp: b.to_dict() for comp, b in benchmarks.items()
        },
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="TooLoo V2 Performance Benchmark")
    parser.add_argument("--quick", action="store_true", help="Fast smoke test (10 iterations)")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    print(f"\n{'═' * 60}")
    print(f"  TooLoo V2 — Performance Benchmark")
    print(f"  Mode: {'Quick' if args.quick else 'Full'}")
    print(f"{'═' * 60}\n")

    results = run_all_benchmarks(quick=args.quick)

    # Print results
    for comp, bench in sorted(results.items()):
        status = "✓" if not bench.error else "✗"
        print(f"  [{comp:28s}] {status}  "
              f"import={bench.import_ms:7.2f}ms  "
              f"exec={bench.exec_ms:7.2f}ms  "
              f"mem={bench.memory_kb:7.1f}KB  "
              f"perf={bench.composite_perf:.4f}")

    # Summary
    report = benchmark_report(results)
    print(f"\n{'─' * 60}")
    print(f"  Avg exec latency:  {report['avg_exec_ms']:.2f}ms")
    print(f"  Avg composite:     {report['avg_composite_perf']:.4f}")
    print(f"  Errors:            {len(report['errors'])}")
    print(f"{'═' * 60}\n")

    if args.json:
        out_path = _ROOT / "psyche_bank" / "benchmark_report.json"
        out_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  Report saved to: {out_path}")

    # Save performance confidence
    perf_conf = compute_performance_confidence(results)
    conf_path = _ROOT / "psyche_bank" / "performance_confidence.json"
    conf_path.write_text(
        json.dumps(perf_conf, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Performance confidence saved to: {conf_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
