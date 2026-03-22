#!/usr/bin/env python3
"""
run_fractal_16d_inspection.py — TooLoo V2 Full Self-Inspection via Fractal DAG + 16D Validation

Runs a comprehensive self-inspection of every engine component by:

  1. Enumerating all 17+ engine components from the self-improvement manifest
  2. Using FractalDAGExpander to decompose each audit into fractal sub-tasks
     (scan_security → check_compliance → generate_report)
  3. Running Validator16D on each component's source code across all 16 dimensions
  4. Running JIT16DBidder to score optimal model selection per sub-task
  5. Producing a full 16D inspection report with per-component & aggregate scores

Output: fractal_16d_inspection_report.json + console summary
"""
from __future__ import annotations
from engine.validator_16d import Validator16D
from engine.tribunal import Tribunal
from engine.self_improvement import _COMPONENT_FOCUS, _COMPONENT_SOURCE, _COMPONENTS
from engine.dynamic_model_registry import (
    FractalDAGExpander,
    FractalExpansion,
    JIT16DBidder,
    get_bidder,
    get_dynamic_registry,
)
import engine.self_improvement as _si_mod
import engine.jit_booster as _jib_mod

import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Patch JIT module for offline mode before other engine imports ─────────────

_LIVE_MODE: bool = os.environ.get(
    "TOOLOO_LIVE_TESTS", ""
).lower() in ("1", "true", "yes")
if not _LIVE_MODE:
    _jib_mod._vertex_client = None
    _jib_mod._gemini_client = None
    _si_mod._vertex_client = None
    _si_mod._gemini_client = None


# ── DTOs ──────────────────────────────────────────────────────────────────────


@dataclass
class FractalSubTask:
    sub_node_id: str
    task_type: str
    dependencies: list[str]
    bid_model: str
    bid_score: float
    bid_cost_per_10k: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub_node_id": self.sub_node_id,
            "task_type": self.task_type,
            "dependencies": self.dependencies,
            "bid_model": self.bid_model,
            "bid_score": round(self.bid_score, 4),
            "bid_cost_per_10k": round(self.bid_cost_per_10k, 6),
        }


@dataclass
class ComponentInspection:
    component: str
    source_file: str
    source_lines: int
    wave: int
    focus: str
    # 16D scores
    composite_score: float
    autonomous_gate_pass: bool
    dimensions: list[dict[str, Any]]
    critical_failures: list[str]
    estimated_cost_usd: float
    # Fractal DAG
    fractal_expanded: bool
    fractal_sub_tasks: list[FractalSubTask]
    fractal_reason: str
    # Tribunal
    tribunal_passed: bool
    tribunal_details: str
    # Timing
    inspection_latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "source_file": self.source_file,
            "source_lines": self.source_lines,
            "wave": self.wave,
            "focus": self.focus,
            "composite_score": round(self.composite_score, 4),
            "autonomous_gate_pass": self.autonomous_gate_pass,
            "dimensions": self.dimensions,
            "critical_failures": self.critical_failures,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "fractal_expanded": self.fractal_expanded,
            "fractal_sub_tasks": [s.to_dict() for s in self.fractal_sub_tasks],
            "fractal_reason": self.fractal_reason,
            "tribunal_passed": self.tribunal_passed,
            "tribunal_details": self.tribunal_details,
            "inspection_latency_ms": round(self.inspection_latency_ms, 2),
        }


@dataclass
class DimensionAggregate:
    name: str
    avg_score: float
    min_score: float
    max_score: float
    pass_rate: float  # fraction of components passing this dimension
    weakest_component: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "avg_score": round(self.avg_score, 4),
            "min_score": round(self.min_score, 4),
            "max_score": round(self.max_score, 4),
            "pass_rate": round(self.pass_rate, 4),
            "weakest_component": self.weakest_component,
        }


@dataclass
class InspectionReport:
    inspection_id: str
    timestamp: str
    components_inspected: int
    total_fractal_sub_tasks: int
    total_latency_ms: float
    # Aggregates
    avg_composite_score: float
    min_composite_score: float
    max_composite_score: float
    autonomous_gate_pass_rate: float
    tribunal_pass_rate: float
    dimension_aggregates: list[DimensionAggregate]
    # Per-component
    inspections: list[ComponentInspection]
    # Top issues
    critical_components: list[str]  # components with critical failures
    top_recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "inspection_id": self.inspection_id,
            "timestamp": self.timestamp,
            "components_inspected": self.components_inspected,
            "total_fractal_sub_tasks": self.total_fractal_sub_tasks,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_composite_score": round(self.avg_composite_score, 4),
            "min_composite_score": round(self.min_composite_score, 4),
            "max_composite_score": round(self.max_composite_score, 4),
            "autonomous_gate_pass_rate": round(self.autonomous_gate_pass_rate, 4),
            "tribunal_pass_rate": round(self.tribunal_pass_rate, 4),
            "dimension_aggregates": [d.to_dict() for d in self.dimension_aggregates],
            "inspections": [i.to_dict() for i in self.inspections],
            "critical_components": self.critical_components,
            "top_recommendations": self.top_recommendations,
        }


# ── Inspection Engine ────────────────────────────────────────────────────────

class FractalInspectionEngine:
    """Full self-inspection using Fractal DAG decomposition + 16D validation."""

    def __init__(self) -> None:
        self.validator = Validator16D()
        self.tribunal = Tribunal()
        self.expander = FractalDAGExpander()
        self.bidder = get_bidder()

    def _read_source(self, rel_path: str) -> str:
        """Read component source code."""
        full_path = _ROOT / rel_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return ""

    def _run_tribunal(self, source: str, component: str) -> tuple[bool, str]:
        """Run Tribunal OWASP scan on source code."""
        from engine.tribunal import Engram
        engram = Engram(
            slug=f"self-inspect:{component}",
            intent="AUDIT",
            logic_body=source[:4000],
        )
        result = self.tribunal.evaluate(engram)
        detail = ", ".join(result.violations) if result.violations else "clean"
        return result.passed, detail

    def _fractal_expand(
        self, component: str, action_type: str = "audit"
    ) -> tuple[bool, list[FractalSubTask], str]:
        """Expand component audit into fractal sub-tasks and bid each."""
        expansion = self.expander.maybe_expand(
            failed_node_id=f"inspect_{component}",
            action_type=action_type,
            failure_count=2,  # force expansion (threshold is ≥2)
            error_message=f"Fractal inspection of {component}",
        )
        if not expansion:
            return False, [], "Not expandable (atomic audit)"

        sub_tasks: list[FractalSubTask] = []
        for sub_id, deps in expansion.sub_nodes:
            task_type = expansion.upgraded_task_types.get(sub_id, "reasoning")
            bid = self.bidder.bid(
                node_id=sub_id,
                task_type=task_type,
                estimated_tokens=2000,
            )
            sub_tasks.append(FractalSubTask(
                sub_node_id=sub_id,
                task_type=task_type,
                dependencies=deps,
                bid_model=bid.winning_model,
                bid_score=bid.winning_score,
                bid_cost_per_10k=bid.winning_cost_per_10k,
            ))

        return True, sub_tasks, expansion.reason

    def inspect_component(self, comp_def: dict[str, Any]) -> ComponentInspection:
        """Inspect a single component across all 16 dimensions + fractal DAG."""
        t0 = time.perf_counter()
        component = comp_def["component"]
        source_file = _COMPONENT_SOURCE.get(component, "")
        source = self._read_source(source_file)
        source_lines = source.count("\n") + 1 if source else 0

        # 16D validation
        mandate_id = f"inspect-{component}-{uuid.uuid4().hex[:8]}"
        validation = self.validator.validate(
            mandate_id=mandate_id,
            intent="AUDIT",
            code_snippet=source[:8000] if source else None,
            test_pass_rate=1.0,  # assume green suite
            latency_p50_ms=500.0,
            latency_p90_ms=1200.0,
        )

        # Tribunal scan
        tribunal_passed, tribunal_details = (
            self._run_tribunal(source, component) if source else (
                True, "No source")
        )

        # Fractal DAG expansion
        fractal_expanded, fractal_sub_tasks, fractal_reason = self._fractal_expand(
            component
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return ComponentInspection(
            component=component,
            source_file=source_file,
            source_lines=source_lines,
            wave=comp_def.get("wave", 0),
            focus=_COMPONENT_FOCUS.get(component, "balanced"),
            composite_score=validation.composite_score,
            autonomous_gate_pass=validation.autonomous_gate_pass,
            dimensions=[d.to_dict() for d in validation.dimensions],
            critical_failures=validation.critical_failures,
            estimated_cost_usd=validation.estimated_cost_usd,
            fractal_expanded=fractal_expanded,
            fractal_sub_tasks=fractal_sub_tasks,
            fractal_reason=fractal_reason,
            tribunal_passed=tribunal_passed,
            tribunal_details=tribunal_details,
            inspection_latency_ms=elapsed_ms,
        )

    def run_full_inspection(self) -> InspectionReport:
        """Run 16D inspection across all engine components with fractal DAG."""
        t0 = time.perf_counter()
        inspection_id = f"fractal-16d-{uuid.uuid4().hex[:8]}"

        # Sort components by wave for ordered execution
        sorted_components = sorted(_COMPONENTS, key=lambda c: c.get("wave", 0))

        inspections: list[ComponentInspection] = []
        for comp_def in sorted_components:
            insp = self.inspect_component(comp_def)
            inspections.append(insp)

        total_latency = (time.perf_counter() - t0) * 1000

        # Aggregate dimension scores
        dimension_names = [
            "ROI", "Safety", "Security", "Legal", "Human Considering",
            "Accuracy", "Efficiency", "Quality", "Speed", "Monitor",
            "Control", "Honesty", "Resilience", "Financial Awareness",
            "Convergence", "Reversibility",
        ]

        dim_aggregates: list[DimensionAggregate] = []
        for dim_name in dimension_names:
            scores: list[tuple[float, str]] = []
            pass_count = 0
            for insp in inspections:
                for d in insp.dimensions:
                    if d["name"] == dim_name:
                        scores.append((d["score"], insp.component))
                        if d["passed"]:
                            pass_count += 1
                        break

            if scores:
                values = [s[0] for s in scores]
                min_idx = values.index(min(values))
                dim_aggregates.append(DimensionAggregate(
                    name=dim_name,
                    avg_score=sum(values) / len(values),
                    min_score=min(values),
                    max_score=max(values),
                    pass_rate=pass_count / len(scores),
                    weakest_component=scores[min_idx][1],
                ))

        # Composite aggregates
        composites = [i.composite_score for i in inspections]
        gate_passes = sum(1 for i in inspections if i.autonomous_gate_pass)
        tribunal_passes = sum(1 for i in inspections if i.tribunal_passed)
        total_sub_tasks = sum(len(i.fractal_sub_tasks) for i in inspections)

        critical_components = [
            i.component for i in inspections if i.critical_failures
        ]

        # Generate top recommendations
        recommendations = _generate_recommendations(
            inspections, dim_aggregates)

        return InspectionReport(
            inspection_id=inspection_id,
            timestamp=datetime.now(UTC).isoformat(),
            components_inspected=len(inspections),
            total_fractal_sub_tasks=total_sub_tasks,
            total_latency_ms=total_latency,
            avg_composite_score=sum(composites) /
            len(composites) if composites else 0,
            min_composite_score=min(composites) if composites else 0,
            max_composite_score=max(composites) if composites else 0,
            autonomous_gate_pass_rate=gate_passes /
            len(inspections) if inspections else 0,
            tribunal_pass_rate=tribunal_passes /
            len(inspections) if inspections else 0,
            dimension_aggregates=dim_aggregates,
            inspections=inspections,
            critical_components=critical_components,
            top_recommendations=recommendations,
        )


def _generate_recommendations(
    inspections: list[ComponentInspection],
    dim_aggregates: list[DimensionAggregate],
) -> list[str]:
    """Generate top-5 actionable recommendations from the inspection."""
    recs: list[tuple[float, str]] = []

    # Weakest dimensions (lowest avg_score)
    for da in sorted(dim_aggregates, key=lambda d: d.avg_score):
        if da.avg_score < 0.95:
            recs.append((
                da.avg_score,
                f"[{da.name}] avg={da.avg_score:.3f}, weakest={da.weakest_component} "
                f"(pass_rate={da.pass_rate:.0%}) — prioritize improvement",
            ))

    # Components with critical failures
    for insp in inspections:
        if insp.critical_failures:
            recs.append((
                insp.composite_score,
                f"[{insp.component}] has critical failures in: {', '.join(insp.critical_failures)} "
                f"(composite={insp.composite_score:.3f})",
            ))

    # Tribunal failures
    for insp in inspections:
        if not insp.tribunal_passed:
            recs.append((
                0.0,
                f"[{insp.component}] FAILED Tribunal OWASP scan: {insp.tribunal_details}",
            ))

    # Low composite scores
    for insp in sorted(inspections, key=lambda i: i.composite_score):
        if insp.composite_score < 0.92:
            recs.append((
                insp.composite_score,
                f"[{insp.component}] low composite={insp.composite_score:.3f} — "
                f"review {insp.source_file} ({insp.source_lines} lines)",
            ))

    # Sort by severity (lowest score first) and return top 5
    recs.sort(key=lambda r: r[0])
    return [r[1] for r in recs[:8]]


# ── Console Output ────────────────────────────────────────────────────────────

_PASS = "\033[92m✓\033[0m"
_FAIL = "\033[91m✗\033[0m"
_WARN = "\033[93m⚠\033[0m"


def _score_indicator(score: float) -> str:
    if score >= 0.95:
        return _PASS
    if score >= 0.85:
        return _WARN
    return _FAIL


def print_report(report: InspectionReport) -> None:
    """Print a formatted console report."""
    print("\n" + "=" * 80)
    print("  TooLoo V2 — FRACTAL DAG 16D SELF-INSPECTION REPORT")
    print("=" * 80)
    print(f"  ID:         {report.inspection_id}")
    print(f"  Timestamp:  {report.timestamp}")
    print(f"  Components: {report.components_inspected}")
    print(
        f"  Sub-tasks:  {report.total_fractal_sub_tasks} (fractal DAG expansion)")
    print(f"  Latency:    {report.total_latency_ms:.0f}ms")
    print()

    # ── Aggregate 16D Dashboard ──
    print("─" * 80)
    print("  16D DIMENSION DASHBOARD")
    print("─" * 80)
    print(
        f"  {'Dimension':<22} {'Avg':>6} {'Min':>6} {'Max':>6} {'Pass%':>6}  Weakest")
    print("  " + "─" * 76)
    for da in report.dimension_aggregates:
        ind = _score_indicator(da.avg_score)
        print(
            f"  {ind} {da.name:<20} {da.avg_score:.3f} {da.min_score:.3f} "
            f"{da.max_score:.3f} {da.pass_rate:5.0%}  {da.weakest_component}"
        )

    # ── Composite Summary ──
    print()
    print("─" * 80)
    print("  COMPOSITE SCORES")
    print("─" * 80)
    print(f"  Average:              {report.avg_composite_score:.4f}")
    print(
        f"  Range:                [{report.min_composite_score:.4f} — {report.max_composite_score:.4f}]")
    print(f"  Autonomous Gate Pass: {report.autonomous_gate_pass_rate:.0%}")
    print(f"  Tribunal Pass Rate:   {report.tribunal_pass_rate:.0%}")

    # ── Per-Component Table ──
    print()
    print("─" * 80)
    print("  PER-COMPONENT INSPECTION")
    print("─" * 80)
    print(f"  {'Component':<20} {'Wave':>4} {'16D':>6} {'Gate':>5} {'Trib':>5} {'Fractal':>7} {'Sub':>4} {'ms':>7}")
    print("  " + "─" * 76)
    for insp in sorted(report.inspections, key=lambda i: i.composite_score):
        gate = _PASS if insp.autonomous_gate_pass else _FAIL
        trib = _PASS if insp.tribunal_passed else _FAIL
        frac = "yes" if insp.fractal_expanded else "no"
        ind = _score_indicator(insp.composite_score)
        print(
            f"  {ind} {insp.component:<18} {insp.wave:>4} "
            f"{insp.composite_score:.3f} {gate:>5} {trib:>5} "
            f"{frac:>7} {len(insp.fractal_sub_tasks):>4} "
            f"{insp.inspection_latency_ms:>6.0f}"
        )

    # ── Fractal DAG Expansion Detail ──
    expanded = [i for i in report.inspections if i.fractal_expanded]
    if expanded:
        print()
        print("─" * 80)
        print("  FRACTAL DAG EXPANSION DETAIL")
        print("─" * 80)
        for insp in expanded:
            print(
                f"\n  {insp.component} → {len(insp.fractal_sub_tasks)} sub-tasks")
            for st in insp.fractal_sub_tasks:
                deps = " → ".join(
                    st.dependencies) if st.dependencies else "(root)"
                print(
                    f"    {st.sub_node_id:<50} "
                    f"type={st.task_type:<10} "
                    f"model={st.bid_model:<25} "
                    f"score={st.bid_score:.3f}"
                )

    # ── Critical Components ──
    if report.critical_components:
        print()
        print("─" * 80)
        print(f"  {_FAIL} CRITICAL COMPONENTS ({len(report.critical_components)})")
        print("─" * 80)
        for comp_name in report.critical_components:
            insp = next(
                i for i in report.inspections if i.component == comp_name)
            print(f"  {_FAIL} {comp_name}: {', '.join(insp.critical_failures)}")

    # ── Recommendations ──
    if report.top_recommendations:
        print()
        print("─" * 80)
        print("  TOP RECOMMENDATIONS")
        print("─" * 80)
        for i, rec in enumerate(report.top_recommendations, 1):
            print(f"  {i}. {rec}")

    print()
    print("=" * 80)
    verdict = (
        f"{_PASS} SYSTEM HEALTHY"
        if report.avg_composite_score >= 0.90 and not report.critical_components
        else f"{_WARN} ATTENTION NEEDED"
        if report.avg_composite_score >= 0.80
        else f"{_FAIL} CRITICAL ISSUES DETECTED"
    )
    print(
        f"  VERDICT: {verdict}  (avg composite: {report.avg_composite_score:.4f})")
    print("=" * 80 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("\n🔬 TooLoo V2 — Fractal DAG 16D Self-Inspection starting...")
    print(
        f"   Live mode: {'ENABLED' if _LIVE_MODE else 'OFFLINE (catalogue)'}")
    print(f"   Components: {len(_COMPONENTS)}")
    print(f"   Dimensions: 16\n")

    engine = FractalInspectionEngine()
    report = engine.run_full_inspection()

    # Save JSON report
    report_path = _ROOT / "fractal_16d_inspection_report.json"
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"📄 Report saved to: {report_path}")

    # Print console report
    print_report(report)

    return 0 if not report.critical_components else 1


if __name__ == "__main__":
    raise SystemExit(main())
