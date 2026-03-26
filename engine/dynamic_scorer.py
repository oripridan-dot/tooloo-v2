"""
engine/dynamic_scorer.py — Dynamic Code Quality Scorer for TooLoo V2.

Analyzes actual source files to produce per-component quality metrics that
feed into the 16D calibration engine.  Scores update dynamically as the
self-improvement engine modifies code.

Metrics captured per component:
  - docstring_coverage:  fraction of public functions/classes with docstrings
  - type_hint_coverage:  fraction of function signatures with type hints
  - complexity_score:    inverse cyclomatic complexity (lower complexity = higher score)
  - test_coverage_proxy: whether a corresponding test file exists + its line count
  - error_handling:      fraction of functions with try/except or explicit raises
  - modularity:          ratio of functions per LOC (higher = more modular)
  - code_freshness:      recency of last modification (more recent = higher)
  - loc_efficiency:      inverse of excessive line count (smaller files score higher)

Each metric maps to 0.0–1.0 and is combined into a composite quality score
that updates `_COMPONENT_BASE_CONFIDENCE` in the calibration engine.
"""
from __future__ import annotations

import ast
import os
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ── Project root ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
_ENGINE_DIR = _ROOT / "engine"
_TESTS_DIR = _ROOT / "tests"

# ── Component → file mapping ─────────────────────────────────────────────────
COMPONENT_FILES: dict[str, str] = {
    "router":                "engine/router.py",
    "tribunal":              "engine/tribunal.py",
    "psyche_bank":           "engine/psyche_bank.py",
    "jit_booster":           "engine/jit_booster.py",
    "executor":              "engine/executor.py",
    "graph":                 "engine/graph.py",
    "scope_evaluator":       "engine/scope_evaluator.py",
    "refinement":            "engine/refinement.py",
    "refinement_supervisor": "engine/refinement_supervisor.py",
    "n_stroke":              "engine/n_stroke.py",
    "meta_architect":        "engine/meta_architect.py",
    "model_selector":        "engine/model_selector.py",
    "model_garden":          "engine/model_garden.py",
    "validator_16d":         "engine/validator_16d.py",
    "conversation":          "engine/conversation.py",
    "buddy_cache":           "engine/buddy_cache.py",
    "buddy_cognition":       "engine/buddy_cognition.py",
    "branch_executor":       "engine/branch_executor.py",
    "async_fluid_executor":  "engine/async_fluid_executor.py",
    "mandate_executor":      "engine/mandate_executor.py",
    "mcp_manager":           "engine/mcp_manager.py",
    "self_improvement":      "engine/self_improvement.py",
    "sandbox":               "engine/sandbox.py",
    "roadmap":               "engine/roadmap.py",
    "vector_store":          "engine/vector_store.py",
    "sota_ingestion":        "engine/sota_benchmarks.py",
    "daemon":                "engine/daemon.py",
    "config":                "engine/config.py",
}


@dataclass
class CodeMetrics:
    """Quality metrics for a single component source file."""
    component: str
    file_path: str
    loc: int = 0
    functions: int = 0
    classes: int = 0
    docstring_coverage: float = 0.0
    type_hint_coverage: float = 0.0
    complexity_score: float = 0.0
    error_handling_score: float = 0.0
    modularity_score: float = 0.0
    test_exists: bool = False
    test_loc: int = 0
    test_coverage_proxy: float = 0.0
    code_freshness: float = 0.0
    loc_efficiency: float = 0.0
    composite_quality: float = 0.0
    analysis_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "file_path": self.file_path,
            "loc": self.loc,
            "functions": self.functions,
            "classes": self.classes,
            "docstring_coverage": round(self.docstring_coverage, 4),
            "type_hint_coverage": round(self.type_hint_coverage, 4),
            "complexity_score": round(self.complexity_score, 4),
            "error_handling_score": round(self.error_handling_score, 4),
            "modularity_score": round(self.modularity_score, 4),
            "test_coverage_proxy": round(self.test_coverage_proxy, 4),
            "code_freshness": round(self.code_freshness, 4),
            "loc_efficiency": round(self.loc_efficiency, 4),
            "composite_quality": round(self.composite_quality, 4),
            "analysis_time": self.analysis_time,
        }


# ── Metric weights for composite score ────────────────────────────────────────
_METRIC_WEIGHTS = {
    "docstring_coverage":    0.15,
    "type_hint_coverage":    0.15,
    "complexity_score":      0.15,
    "error_handling_score":  0.10,
    "modularity_score":      0.10,
    "test_coverage_proxy":   0.15,
    "code_freshness":        0.10,
    "loc_efficiency":        0.10,
}


def _analyze_ast(source: str) -> dict[str, Any]:
    """Parse Python source and extract quality metrics via AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {
            "functions": 0, "classes": 0,
            "docstring_coverage": 0.0,
            "type_hint_coverage": 0.0,
            "complexity_score": 0.5,
            "error_handling_score": 0.0,
        }

    functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    classes: list[ast.ClassDef] = []
    has_try: int = 0
    has_raise: int = 0
    branch_count: int = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node)
        elif isinstance(node, ast.ClassDef):
            classes.append(node)
        elif isinstance(node, ast.Try):
            has_try += 1
        elif isinstance(node, ast.Raise):
            has_raise += 1
        elif isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
            branch_count += 1

    # Docstring coverage
    documentable = functions + classes
    with_docs = 0
    for item in documentable:
        if (item.body and isinstance(item.body[0], ast.Expr)
                and isinstance(item.body[0].value, ast.Constant)
                and isinstance(item.body[0].value.value, str)):
            with_docs += 1
    doc_cov = with_docs / max(len(documentable), 1)

    # Type hint coverage
    typed_funcs = 0
    for fn in functions:
        has_return = fn.returns is not None
        has_args = any(
            arg.annotation is not None
            for arg in fn.args.args
            if arg.arg != "self"
        )
        if has_return or has_args:
            typed_funcs += 1
    type_cov = typed_funcs / max(len(functions), 1)

    # Complexity (inverse — lower branch count per function = higher score)
    avg_branches = branch_count / max(len(functions), 1)
    complexity = max(0.0, min(1.0, 1.0 - (avg_branches / 10.0)))

    # Error handling
    error_fns = has_try + has_raise
    error_score = min(1.0, error_fns / max(len(functions) * 0.3, 1))

    return {
        "functions": len(functions),
        "classes": len(classes),
        "docstring_coverage": doc_cov,
        "type_hint_coverage": type_cov,
        "complexity_score": complexity,
        "error_handling_score": error_score,
    }


def score_component(component: str) -> CodeMetrics:
    """Analyze a single component's source file and compute quality metrics."""
    rel_path = COMPONENT_FILES.get(component)
    if not rel_path:
        return CodeMetrics(component=component, file_path="<not found>")

    full_path = _ROOT / rel_path
    if not full_path.exists():
        return CodeMetrics(component=component, file_path=str(full_path))

    source = full_path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()
    loc = len(lines)

    # AST analysis
    ast_metrics = _analyze_ast(source)

    # Modularity: functions per 100 LOC
    funcs = ast_metrics["functions"]
    modularity = min(1.0, (funcs / max(loc, 1)) * 100 / 8.0)

    # Test coverage proxy
    test_file = _TESTS_DIR / f"test_{component}.py"
    test_exists = test_file.exists()
    test_loc = 0
    test_proxy = 0.0
    if test_exists:
        test_loc = len(test_file.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines())
        # Ratio of test LOC to source LOC (ideal ~0.5-1.0)
        test_proxy = min(1.0, test_loc / max(loc * 0.5, 1))

    # Code freshness (based on mtime)
    mtime = full_path.stat().st_mtime
    age_hours = (time.time() - mtime) / 3600
    freshness = max(0.0, min(1.0, 1.0 - (age_hours / (24 * 30))))  # 30-day decay

    # LOC efficiency (penalize very large files)
    loc_eff = max(0.0, min(1.0, 1.0 - max(0, loc - 500) / 2000))

    metrics = CodeMetrics(
        component=component,
        file_path=rel_path,
        loc=loc,
        functions=funcs,
        classes=ast_metrics["classes"],
        docstring_coverage=ast_metrics["docstring_coverage"],
        type_hint_coverage=ast_metrics["type_hint_coverage"],
        complexity_score=ast_metrics["complexity_score"],
        error_handling_score=ast_metrics["error_handling_score"],
        modularity_score=modularity,
        test_exists=test_exists,
        test_loc=test_loc,
        test_coverage_proxy=test_proxy,
        code_freshness=freshness,
        loc_efficiency=loc_eff,
        analysis_time=datetime.now(UTC).isoformat(),
    )

    # Composite quality
    composite = sum(
        getattr(metrics, k) * w
        for k, w in _METRIC_WEIGHTS.items()
    )
    metrics.composite_quality = composite

    return metrics


def score_all_components() -> dict[str, CodeMetrics]:
    """Score all engine components and return a dict of metrics."""
    return {comp: score_component(comp) for comp in COMPONENT_FILES}


def compute_dynamic_confidence(
    static_base: dict[str, float] | None = None,
) -> dict[str, float]:
    """Compute dynamic confidence scores for all components.

    Blends the static base confidence (from calibration history) with
    live code quality analysis.  The result is a per-component score
    that updates as code changes are made.

    Args:
        static_base: Optional static base confidence dict. If None,
            uses the default from calibration_engine.

    Returns:
        dict[component_name, confidence_score] in [0.0, 1.0]
    """
    if static_base is None:
        from engine.calibration_engine import _COMPONENT_BASE_CONFIDENCE
        static_base = dict(_COMPONENT_BASE_CONFIDENCE)

    all_metrics = score_all_components()

    # Blend: 60% static history + 40% live code quality
    STATIC_WEIGHT = 0.60
    DYNAMIC_WEIGHT = 0.40

    result: dict[str, float] = {}
    for comp, base in static_base.items():
        metrics = all_metrics.get(comp)
        if metrics and metrics.composite_quality > 0:
            dynamic = metrics.composite_quality
            blended = STATIC_WEIGHT * base + DYNAMIC_WEIGHT * dynamic
            result[comp] = round(min(0.98, blended), 4)
        else:
            result[comp] = base

    return result


def quality_report() -> dict[str, Any]:
    """Generate a full quality report across all components."""
    all_metrics = score_all_components()

    total_loc = sum(m.loc for m in all_metrics.values())
    avg_quality = sum(
        m.composite_quality for m in all_metrics.values()
    ) / max(len(all_metrics), 1)
    tested = sum(1 for m in all_metrics.values() if m.test_exists)

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "components_analyzed": len(all_metrics),
        "total_loc": total_loc,
        "avg_composite_quality": round(avg_quality, 4),
        "tested_components": tested,
        "untested_components": len(all_metrics) - tested,
        "avg_docstring_coverage": round(
            sum(m.docstring_coverage for m in all_metrics.values())
            / max(len(all_metrics), 1), 4
        ),
        "avg_type_hint_coverage": round(
            sum(m.type_hint_coverage for m in all_metrics.values())
            / max(len(all_metrics), 1), 4
        ),
        "component_scores": {
            comp: m.to_dict() for comp, m in all_metrics.items()
        },
    }
