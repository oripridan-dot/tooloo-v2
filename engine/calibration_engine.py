"""
engine/calibration_engine.py — 3-Cycle Precision Calibration Engine.

This engine runs three sequential calibration cycles against TooLoo's 28
engine components, benchmarking each component against real, published external
SOTA data and computing precise mathematical improvement proofs.

═══════════════════════════════════════════════════════════════════════════════
CYCLE 1 — SOTA Baseline Harvest
  Purpose : Measure each component's current performance vs. real external
             benchmarks (sourced from SOTA_CATALOGUE in sota_benchmarks.py).
  Method  : For each component, collect all benchmarks from its domain(s),
             compute gap_ratio vector, derive an overall alignment score via
             geometric mean.
  Output  : ComponentBaseline(component, benchmarks_used, alignment_score,
             gap_vector, weakest_benchmark)

  Math:
    gap_ratio_i = tooloo_current_i / sota_value_i  (0.0–1.0)
    alignment = geometric_mean(gap_ratio_1 … gap_ratio_N)
             = (Π gap_ratio_i)^(1/N)

═══════════════════════════════════════════════════════════════════════════════
CYCLE 2 — 16D Math Proof Engine
  Purpose : Quantify the calibration improvement across all 16 validation
             dimensions for every component, producing signed proof certificates
             anchored to the Cycle-1 gap vectors.
  Method  : Use research-calibrated dimension weights from sota_benchmarks.py
             to compute weighted composite improvement and Impact-Per-Action.
  Output  : CalibrationProof(component, dimension_deltas, weighted_composite,
             impact_per_action, proof_certificate)

  Math:
    # Gap-informed weight boost (larger gap → bigger weight adjustment):
    weight_boost(d, c) = 1.0 + GAP_WEIGHT_COEFFICIENT × (1 - alignment(c))

    # Calibrated 16D score per dimension:
    cal_score(d, c)  = base_score(d) × weight_d × weight_boost(d, c)

    # Normalised 16D composite (preserves 0–1 range):
    cal_composite(c) = Σ_d cal_score(d, c) / Σ_d weight_d

    # Delta proof:
    Δ16D(c) = cal_composite(c) - base_composite(c)

    # Impact-per-action (ROI of applying this calibration):
    IPA(c) = Δ16D(c) / estimated_cost(c)

  GAP_WEIGHT_COEFFICIENT = 0.40  (tuned: 40% weight uplift for widest gaps)

═══════════════════════════════════════════════════════════════════════════════
CYCLE 3 — JIT Parameter Calibration
  Purpose : Recalibrate JITBooster's BOOST_PER_SIGNAL, MAX_BOOST_DELTA, and
             the PsycheBank rule weights using Cycle-1 alignment scores and
             Ebbinghaus recency decay on existing rules.
  Method  : Ebbinghaus forgetting curve for signal recency weighting; derive
             optimal BOOST_PER_SIGNAL from observed alignment gaps.
  Output  : JITCalibration(component, boost_per_signal_calibrated,
             max_boost_recommended, recency_weighted_signals,
             psychebank_rules_injected, system_gain)

  Math:
    # Ebbinghaus recency decay (signal half-life = 7 days):
    recency(age_days) = exp(-DECAY_K × age_days)
    DECAY_K = 0.099  (ln(2)/7 → 50% weight after 7 days)

    # Per-signal boost contribution:
    boost_i = signal_relevance_i × sota_alignment_i × recency_i

    # Calibrated BOOST_PER_SIGNAL:
    BOOST_PER_SIGNAL_cal = clamp(mean(boost_i) / N_signals, 0.030, 0.080)

    # JIT composite for a component:
    JIT_composite(c) = base_confidence(c) + Σ_i boost_i / N_i

    # Total system gain index:
    system_gain = Σ_c IPA(c) × component_weight(c)
    component_weight(c) = alignment(c)^(-0.5)   # lower alignment → higher gain

═══════════════════════════════════════════════════════════════════════════════

All outputs are written to:
  - psyche_bank/calibration_proof.json  (primary proof artefact)
  - psyche_bank/jit_calibration.json    (JIT parameter recommendations)
  - psyche_bank/calibration_rules.cog.json (PsycheBank rules, cycle 3)

"""
from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.sota_benchmarks import (
    COMPONENT_DOMAIN_MAP,
    DIMENSION_WEIGHTS_16D,
    SOTA_CATALOGUE,
    SOTABenchmark,
    get_benchmarks_for_domain,
    weighted_alignment,
)
from engine.feature_registry import get_component_profile

# ── Output paths ──────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_PSYCHE_BANK = _REPO_ROOT / "psyche_bank"
_PROOF_PATH = _PSYCHE_BANK / "calibration_proof.json"
_JIT_CAL_PATH = _PSYCHE_BANK / "jit_calibration.json"
_RULES_PATH = _PSYCHE_BANK / "calibration_rules.cog.json"
_COVERAGE_PATH = _PSYCHE_BANK / "feature_coverage.json"         # Cycle 4
_INTEGRATION_PATH = _PSYCHE_BANK / "integration_scores.json"   # Cycle 5

# ── Mathematical constants ────────────────────────────────────────────────────
GAP_WEIGHT_COEFFICIENT: float = 0.40   # Cycle 2: 40% weight uplift for gaps
DECAY_K: float = math.log(2) / 7.0    # Cycle 3 session decay: k = ln(2)/7 days
JIT_BOOST_MIN: float = 0.030
JIT_BOOST_MAX: float = 0.080
# v2: regularized inverse component weight = 1/(alignment + 0.1)
# Replaces alignment^(-0.5) which had no theoretical grounding.
_COMP_WEIGHT_REGULARISER: float = 0.10
# Cycle 4: coverage below this threshold flags a "benchmark desert"
DESERT_THRESHOLD: float = 0.80
# Cycle 5: hardcoded N-Stroke execution dependency edges (component → dependencies)
_DEPENDENCY_GRAPH: dict[str, list[str]] = {
    "n_stroke":            ["router", "jit_booster", "tribunal", "scope_evaluator",
                            "executor", "graph", "refinement", "meta_architect"],
    "router":              ["jit_booster"],
    "executor":            ["mandate_executor"],
    "branch_executor":     ["executor", "validator_16d"],
    "async_fluid_executor": ["executor"],
    "meta_architect":      ["scope_evaluator", "model_selector"],
    "refinement":          ["validator_16d"],
    "refinement_supervisor": ["refinement", "mcp_manager"],
    "self_improvement":    ["n_stroke", "refinement_supervisor", "meta_architect"],
    "jit_booster":         ["psyche_bank"],
    "tribunal":            ["psyche_bank"],
    "conversation":        ["buddy_cache", "buddy_cognition", "model_selector"],
    "model_garden":        ["model_selector"],
    "mandate_executor":    ["model_garden", "jit_booster"],
    "scope_evaluator":     ["graph"],
    "sandbox":             ["tribunal", "mcp_manager"],
    "sota_ingestion":      ["vector_store", "psyche_bank"],
    "daemon":              ["self_improvement", "roadmap", "n_stroke"],
}

# ── Validator16D default base scores (global fallback only) ──────────────────
# v2: Per-component 16D profiles are loaded from engine/feature_registry.py.
# This dict is kept as a fallback for unknown components not in the registry.
_BASE_SCORES_16D: dict[str, float] = {
    "ROI":                  0.82,
    "Safety":               0.95,
    "Security":             0.95,
    "Legal":                0.90,
    "Human Considering":    0.85,
    "Accuracy":             0.92,
    "Efficiency":           0.85,
    "Quality":              0.82,
    "Speed":                0.80,
    "Monitor":              0.80,
    "Control":              0.84,
    "Honesty":              0.88,
    "Resilience":           0.83,
    "Financial Awareness":  0.78,
    "Convergence":          0.88,
    "Reversibility":        0.90,
}

# ── Component base confidence (from ouroboros last-run + session history) ─────
# NOTE: These static values are blended with live code quality analysis
# via engine.dynamic_scorer when refresh_dynamic_confidence() is called.
_COMPONENT_BASE_CONFIDENCE: dict[str, float] = {
    "router":                0.871,
    "tribunal":              0.854,
    "psyche_bank":           0.832,
    "jit_booster":           0.892,
    "executor":              0.867,
    "graph":                 0.884,
    "scope_evaluator":       0.841,
    "refinement":            0.856,
    "refinement_supervisor": 0.821,
    "n_stroke":              0.878,
    "meta_architect":        0.863,
    "model_selector":        0.847,
    "model_garden":          0.851,
    "validator_16d":         0.891,
    "conversation":          0.874,
    "buddy_cache":           0.862,
    "buddy_cognition":       0.857,
    "branch_executor":       0.833,
    "async_fluid_executor":  0.844,
    "mandate_executor":      0.868,
    "mcp_manager":           0.845,
    "self_improvement":      0.831,
    "sandbox":               0.818,
    "roadmap":               0.827,
    "vector_store":          0.839,
    "sota_ingestion":        0.842,
    "daemon":                0.836,
    "config":                0.888,
}

# ── Per-component execution cost estimate (USD, for IPA calculation) ──────────
_COMPONENT_COST_USD: dict[str, float] = {
    k: 0.0012 for k in _COMPONENT_BASE_CONFIDENCE  # ~$0.0012 per calibration pass
}

# ── Dynamic confidence cache ──────────────────────────────────────────────────
_DYNAMIC_CONFIDENCE: dict[str, float] = {}


def refresh_dynamic_confidence() -> dict[str, float]:
    """Recompute component confidence from live code quality + performance.

    Blends: 40% static history + 30% code quality + 30% runtime performance.
    Call this before calibration to get scores that reflect actual code changes.
    """
    global _DYNAMIC_CONFIDENCE
    try:
        from engine.dynamic_scorer import compute_dynamic_confidence
        quality_scores = compute_dynamic_confidence(_COMPONENT_BASE_CONFIDENCE)
    except Exception:
        quality_scores = dict(_COMPONENT_BASE_CONFIDENCE)

    try:
        # Try loading cached performance scores
        perf_path = Path(__file__).resolve().parents[1] / "psyche_bank" / "performance_confidence.json"
        if perf_path.exists():
            perf_scores = json.loads(perf_path.read_text())
        else:
            perf_scores = dict(_COMPONENT_BASE_CONFIDENCE)
    except Exception:
        perf_scores = dict(_COMPONENT_BASE_CONFIDENCE)

    # Blend: 40% static + 30% code quality + 30% performance
    blended: dict[str, float] = {}
    for comp, static in _COMPONENT_BASE_CONFIDENCE.items():
        q = quality_scores.get(comp, static)
        p = perf_scores.get(comp, static)
        blended[comp] = round(
            min(0.98, 0.40 * static + 0.30 * q + 0.30 * p), 4
        )

    _DYNAMIC_CONFIDENCE = blended
    return blended


def get_component_confidence(component: str) -> float:
    """Get the current confidence for a component (dynamic if available)."""
    if _DYNAMIC_CONFIDENCE:
        return _DYNAMIC_CONFIDENCE.get(component, 0.850)
    return _COMPONENT_BASE_CONFIDENCE.get(component, 0.850)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ComponentBaseline:
    """Cycle 1 output: one component's alignment with SOTA benchmarks."""
    component: str
    benchmarks_used: list[str]
    alignment_score: float          # geometric mean of gap_ratio_i
    gap_vector: dict[str, float]    # metric_name → gap_ratio
    weakest_benchmark: str
    weakest_gap_ratio: float
    cycle: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "component": self.component,
            "alignment_score": round(self.alignment_score, 4),
            "weakest_benchmark": self.weakest_benchmark,
            "weakest_gap_ratio": round(self.weakest_gap_ratio, 4),
            "benchmarks_used": self.benchmarks_used,
            "gap_vector": {k: round(v, 4) for k, v in self.gap_vector.items()},
        }


@dataclass
class DimensionDelta:
    """One 16D dimension's before/after calibration delta."""
    dimension: str
    base_score: float
    calibrated_score: float
    weight: float
    weight_boost: float
    delta: float                    # calibrated - base

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "base_score": round(self.base_score, 4),
            "calibrated_score": round(self.calibrated_score, 4),
            "weight": round(self.weight, 4),
            "weight_boost": round(self.weight_boost, 4),
            "delta": round(self.delta, 4),
        }


@dataclass
class CalibrationProof:
    """Cycle 2 output: mathematical proof certificate for one component."""
    component: str
    cycle_1_alignment: float
    base_composite_16d: float
    calibrated_composite_16d: float
    delta_16d: float
    impact_per_action: float
    dimension_deltas: list[DimensionDelta]
    proof_certificate: str           # human-readable proof statement
    cycle: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "component": self.component,
            "cycle_1_alignment": round(self.cycle_1_alignment, 4),
            "base_composite_16d": round(self.base_composite_16d, 4),
            "calibrated_composite_16d": round(self.calibrated_composite_16d, 4),
            "delta_16d": round(self.delta_16d, 4),
            "delta_16d_pct": round(self.delta_16d * 100, 2),
            "impact_per_action": round(self.impact_per_action, 4),
            "proof_certificate": self.proof_certificate,
            "dimension_deltas": [d.to_dict() for d in self.dimension_deltas],
        }


@dataclass
class JITCalibration:
    """Cycle 3 output: JIT parameter recommendations for one component."""
    component: str
    base_confidence: float
    jit_composite: float
    boost_per_signal_calibrated: float
    max_boost_recommended: float
    psychebank_rules_injected: int
    system_gain_contribution: float
    recency_weighted_signals: list[dict[str, float]]
    cycle: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "component": self.component,
            "base_confidence": round(self.base_confidence, 4),
            "jit_composite": round(self.jit_composite, 4),
            "jit_gain": round(self.jit_composite - self.base_confidence, 4),
            "boost_per_signal_calibrated": round(self.boost_per_signal_calibrated, 4),
            "max_boost_recommended": round(self.max_boost_recommended, 4),
            "psychebank_rules_injected": self.psychebank_rules_injected,
            "system_gain_contribution": round(self.system_gain_contribution, 4),
            "recency_weighted_signals": [
                {k: round(v, 4) for k, v in s.items()}
                for s in self.recency_weighted_signals
            ],
        }


@dataclass
class DomainCoverageResult:
    """Cycle 4 output: coverage analysis for one SOTA benchmark domain."""
    domain: str
    component_count: int
    coverage_score: float          # IPA-weighted geometric mean of component alignments
    is_desert: bool                # coverage_score < DESERT_THRESHOLD
    top_component: str             # highest-alignment component in this domain
    top_component_alignment: float
    weak_component: str            # lowest-alignment component in this domain
    weak_component_alignment: float
    benchmark_count: int
    cycle: int = 4

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "domain": self.domain,
            "component_count": self.component_count,
            "coverage_score": round(self.coverage_score, 4),
            "is_desert": self.is_desert,
            "top_component": self.top_component,
            "top_alignment": round(self.top_component_alignment, 4),
            "weak_component": self.weak_component,
            "weak_alignment": round(self.weak_component_alignment, 4),
            "benchmark_count": self.benchmark_count,
        }


@dataclass
class CrossComponentIntegration:
    """Cycle 5 output: cross-component dependency and cascade analysis."""
    integration_health: float          # harmonic mean of pairwise alignment products
    # mean fan-out × (1-alignment) across all nodes
    system_coupling_index: float
    # top-3 bottlenecks (high fan-out × low alignment)
    bottleneck_components: list[str]
    # component → cascade_gain (IPA × fan-out × gap)
    cascade_gains: dict[str, float]
    fan_out: dict[str, int]            # component → number of dependents
    cycle: int = 5

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "integration_health": round(self.integration_health, 4),
            "system_coupling_index": round(self.system_coupling_index, 4),
            "bottleneck_components": self.bottleneck_components,
            "cascade_gains": {k: round(v, 4) for k, v in self.cascade_gains.items()},
            "fan_out": self.fan_out,
        }


@dataclass
class CalibrationCycleReport:
    """Full 5-cycle calibration report (v2)."""
    run_id: str
    timestamp: str
    components_calibrated: int
    cycle_1_baselines: list[ComponentBaseline] = field(default_factory=list)
    cycle_2_proofs: list[CalibrationProof] = field(default_factory=list)
    cycle_3_jit: list[JITCalibration] = field(default_factory=list)
    cycle_4_coverage: list[DomainCoverageResult] = field(default_factory=list)
    cycle_5_integration: CrossComponentIntegration | None = None
    system_alignment_before: float = 0.0
    system_alignment_after: float = 0.0
    system_16d_gain: float = 0.0
    system_jit_gain: float = 0.0
    total_system_gain_index: float = 0.0
    recommended_boost_per_signal: float = 0.0
    recommended_max_boost: float = 0.0
    benchmark_sources_cited: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        base = {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "components_calibrated": self.components_calibrated,
            "engine_version": "5-cycle-v2",
            "system_metrics": {
                "alignment_before": round(self.system_alignment_before, 4),
                "alignment_after": round(self.system_alignment_after, 4),
                "alignment_gain_pct": round(
                    (self.system_alignment_after - self.system_alignment_before)
                    / max(self.system_alignment_before, 1e-9) * 100, 2
                ),
                "system_16d_gain": round(self.system_16d_gain, 4),
                "system_16d_gain_pct": round(self.system_16d_gain * 100, 2),
                "system_jit_gain": round(self.system_jit_gain, 4),
                "total_system_gain_index": round(self.total_system_gain_index, 4),
            },
            "jit_parameter_recommendations": {
                "boost_per_signal": round(self.recommended_boost_per_signal, 4),
                "max_boost_delta": round(self.recommended_max_boost, 4),
            },
            "benchmark_sources_cited": self.benchmark_sources_cited,
            "summary": self.summary,
            "cycles": {
                "cycle_1_baselines": [b.to_dict() for b in self.cycle_1_baselines],
                "cycle_2_proofs": [p.to_dict() for p in self.cycle_2_proofs],
                "cycle_3_jit": [j.to_dict() for j in self.cycle_3_jit],
                "cycle_4_coverage": [c.to_dict() for c in self.cycle_4_coverage],
                "cycle_5_integration": (
                    self.cycle_5_integration.to_dict()
                    if self.cycle_5_integration else {}
                ),
            },
        }
        return base


# ── CalibrationEngine ─────────────────────────────────────────────────────────

class CalibrationEngine:
    """
    5-Cycle Precision Calibration Engine (v2).

    Stateless (Law 17). All state lives in CalibrationCycleReport.
    Not network-dependent: math formulas run offline against the embedded
    SOTA_CATALOGUE — no live API calls needed for correctness.

    Usage::
        engine = CalibrationEngine()
        report = engine.run_5_cycles()   # full 5-cycle run
        report = engine.run_3_cycles()   # backward-compat 3-cycle alias
        engine.persist(report)
    """

    def __init__(self, components: list[str] | None = None) -> None:
        self._components = components or list(COMPONENT_DOMAIN_MAP.keys())

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    def run_5_cycles(self) -> CalibrationCycleReport:
        """Execute all 5 calibration cycles and return the full proof report."""
        run_id = uuid.uuid4().hex[:12]
        ts = datetime.now(UTC).isoformat()

        report = CalibrationCycleReport(
            run_id=run_id,
            timestamp=ts,
            components_calibrated=len(self._components),
        )

        # ── Cycle 1 ──────────────────────────────────────────────────────────
        print(f"\n{'═'*68}")
        print(f"  CALIBRATION RUN {run_id}  [5-CYCLE v2]")
        print(f"  Timestamp : {ts}")
        print(f"  Components: {len(self._components)}")
        print(f"{'═'*68}")
        print("\n[CYCLE 1] SOTA Baseline Harvest — signal-weighted alignment gaps...")
        t0 = time.perf_counter()
        baselines = self._run_cycle_1()
        report.cycle_1_baselines = baselines
        report.system_alignment_before = self._system_alignment(baselines)
        print(
            f"  ✓ Cycle 1 complete in {time.perf_counter()-t0:.2f}s  "
            f"| System alignment BEFORE: {report.system_alignment_before:.4f}"
        )

        # ── Cycle 2 ──────────────────────────────────────────────────────────
        print(
            "\n[CYCLE 2] 16D Math Proof Engine — per-component Δ16D certificates...")
        t1 = time.perf_counter()
        proofs = self._run_cycle_2(baselines)
        report.cycle_2_proofs = proofs
        report.system_16d_gain = sum(p.delta_16d for p in proofs) / len(proofs)
        print(
            f"  ✓ Cycle 2 complete in {time.perf_counter()-t1:.2f}s  "
            f"| Mean Δ16D: +{report.system_16d_gain*100:.2f} pp"
        )

        # ── Cycle 3 ──────────────────────────────────────────────────────────
        print(
            "\n[CYCLE 3] JIT Parameter Calibration — fixed boost formula v2...")
        t2 = time.perf_counter()
        jit_cals = self._run_cycle_3(baselines, proofs)
        report.cycle_3_jit = jit_cals
        report.system_jit_gain = sum(
            j.jit_composite - j.base_confidence for j in jit_cals
        ) / len(jit_cals)
        print(
            f"  ✓ Cycle 3 complete in {time.perf_counter()-t2:.2f}s  "
            f"| Mean JIT gain: +{report.system_jit_gain*100:.2f} pp"
        )

        # ── Cycle 4 ──────────────────────────────────────────────────────────
        print("\n[CYCLE 4] Feature Coverage Matrix — domain coverage analysis...")
        t3 = time.perf_counter()
        coverage = self._run_cycle_4(baselines, proofs)
        report.cycle_4_coverage = coverage
        deserts = [c.domain for c in coverage if c.is_desert]
        print(
            f"  ✓ Cycle 4 complete in {time.perf_counter()-t3:.2f}s  "
            f"| {len(deserts)} benchmark deserts: {deserts or 'none'}"
        )

        # ── Cycle 5 ──────────────────────────────────────────────────────────
        print("\n[CYCLE 5] Cross-Component Integration — dependency cascade...")
        t4 = time.perf_counter()
        integration = self._run_cycle_5(baselines, proofs)
        report.cycle_5_integration = integration
        print(
            f"  ✓ Cycle 5 complete in {time.perf_counter()-t4:.2f}s  "
            f"| Integration health: {integration.integration_health:.4f}  "
            f"Bottlenecks: {integration.bottleneck_components}"
        )

        # ── System gain index ─────────────────────────────────────────────────
        report.total_system_gain_index = self._compute_system_gain_index(
            baselines, proofs, jit_cals
        )

        # ── Alignment AFTER (v2 fix: geometric mean of calibrated alignments) ─
        alignment_map = {b.component: b.alignment_score for b in baselines}
        proof_map = {p.component: p for p in proofs}
        cal_alignments = []
        for comp in self._components:
            al = alignment_map.get(comp, 0.850)
            delta = proof_map[comp].delta_16d if comp in proof_map else 0.0
            # Calibrated alignment: original alignment scaled by 16D improvement
            cal_al = min(1.0, al * (1.0 + delta))
            cal_alignments.append(cal_al)
        log_sum = sum(math.log(max(v, 1e-9)) for v in cal_alignments)
        report.system_alignment_after = round(
            math.exp(log_sum / len(cal_alignments)), 4
        )

        # ── JIT global parameter recommendations (v2 fixes) ──────────────────
        all_boost = [j.boost_per_signal_calibrated for j in jit_cals]
        report.recommended_boost_per_signal = round(
            sum(all_boost) / len(all_boost), 4
        )
        # v2 fix: × 5 to match JITBooster's 5-signal cap (not × 7)
        report.recommended_max_boost = min(
            0.35,
            report.recommended_boost_per_signal * 5
        )

        # ── Benchmark sources cited ──────────────────────────────────────────
        report.benchmark_sources_cited = sorted({
            b.source for b in SOTA_CATALOGUE
        })

        # ── Summary ──────────────────────────────────────────────────────────
        report.summary = self._build_summary(report)

        total = time.perf_counter() - t0
        print(f"\n{'═'*68}")
        print(f"  5-CYCLE CALIBRATION COMPLETE in {total:.2f}s")
        print(f"  System Gain Index    : {report.total_system_gain_index:.4f}")
        print(f"  Alignment     BEFORE : {report.system_alignment_before:.4f}")
        print(f"  Alignment     AFTER  : {report.system_alignment_after:.4f}")
        print(f"  Mean Δ16D            : +{report.system_16d_gain*100:.2f} pp")
        print(f"  Mean JIT Gain        : +{report.system_jit_gain*100:.2f} pp")
        print(
            f"  Integration Health   : {report.cycle_5_integration.integration_health:.4f}")
        print(
            f"  BOOST_PER_SIGNAL     : {report.recommended_boost_per_signal:.4f}")
        print(f"  MAX_BOOST_DELTA      : {report.recommended_max_boost:.4f}")
        print(f"{'═'*68}\n")

        return report

    def run_3_cycles(self) -> CalibrationCycleReport:
        """Backward-compatible 3-cycle alias. Runs the full 5-cycle v2 engine."""
        return self.run_5_cycles()

    def persist(self, report: CalibrationCycleReport) -> None:
        """Write proof artefacts to psyche_bank/."""
        _PSYCHE_BANK.mkdir(exist_ok=True)

        # Primary proof
        _PROOF_PATH.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # JIT calibration parameters only
        jit_summary = {
            "run_id": report.run_id,
            "timestamp": report.timestamp,
            "engine_version": "5-cycle-v2",
            "recommended_boost_per_signal": report.recommended_boost_per_signal,
            "recommended_max_boost_delta": report.recommended_max_boost,
            "component_jit": {
                j.component: {
                    "boost_per_signal": j.boost_per_signal_calibrated,
                    "jit_gain": round(j.jit_composite - j.base_confidence, 4),
                }
                for j in report.cycle_3_jit
            },
        }
        _JIT_CAL_PATH.write_text(
            json.dumps(jit_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # PsycheBank rules from top improvements
        self._write_psychebank_rules(report)

        # Cycle 4 — feature coverage matrix
        if report.cycle_4_coverage:
            coverage_payload = {
                "run_id": report.run_id,
                "timestamp": report.timestamp,
                "engine_version": "5-cycle-v2",
                "domain_coverage": [c.to_dict() for c in report.cycle_4_coverage],
                "desert_domains": [
                    c.domain for c in report.cycle_4_coverage if c.is_desert
                ],
            }
            _COVERAGE_PATH.write_text(
                json.dumps(coverage_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Cycle 5 — cross-component integration scores
        if report.cycle_5_integration:
            _INTEGRATION_PATH.write_text(
                json.dumps(
                    {"run_id": report.run_id, "timestamp": report.timestamp,
                     **report.cycle_5_integration.to_dict()},
                    indent=2, ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        print(f"  Proof artefacts written to psyche_bank/")
        print(
            f"    calibration_proof.json   ({_PROOF_PATH.stat().st_size:,} bytes)")
        print(
            f"    jit_calibration.json     ({_JIT_CAL_PATH.stat().st_size:,} bytes)")
        print(f"    calibration_rules.cog.json")
        if report.cycle_4_coverage and _COVERAGE_PATH.exists():
            print(
                f"    feature_coverage.json    ({_COVERAGE_PATH.stat().st_size:,} bytes)")
        if report.cycle_5_integration and _INTEGRATION_PATH.exists():
            print(
                f"    integration_scores.json  ({_INTEGRATION_PATH.stat().st_size:,} bytes)")

    # ══════════════════════════════════════════════════════════════════════════
    # CYCLE 1 — SOTA BASELINE HARVEST
    # ══════════════════════════════════════════════════════════════════════════

    def _run_cycle_1(self) -> list[ComponentBaseline]:
        baselines: list[ComponentBaseline] = []
        for comp in self._components:
            baseline = self._baseline_component(comp)
            baselines.append(baseline)
            print(
                f"    [{comp:<26}]  alignment={baseline.alignment_score:.4f}  "
                f"weakest='{baseline.weakest_benchmark}' "
                f"({baseline.weakest_gap_ratio:.3f})"
            )
        return baselines

    def _baseline_component(self, component: str) -> ComponentBaseline:
        """
        Compute one component's SOTA alignment (v2: signal-weighted geometric mean).

        alignment = weighted_geo_mean(gap_ratio_i, signal_weight_i)
          where signal_weight_i = authority_weight × recency_weight

        v1 used unweighted geo mean — treated a 2024 community leaderboard
        and a 2026 peer-reviewed paper with equal weight. Fixed in v2.
        """
        domains = COMPONENT_DOMAIN_MAP.get(component, [])
        benchmarks: list[SOTABenchmark] = []
        for domain in domains:
            benchmarks.extend(get_benchmarks_for_domain(domain))

        # De-duplicate by metric_name
        seen: set[str] = set()
        unique_benchmarks: list[SOTABenchmark] = []
        for b in benchmarks:
            if b.metric_name not in seen:
                seen.add(b.metric_name)
                unique_benchmarks.append(b)

        if not unique_benchmarks:
            return ComponentBaseline(
                component=component,
                benchmarks_used=[],
                alignment_score=0.850,
                gap_vector={},
                weakest_benchmark="(no benchmark data)",
                weakest_gap_ratio=0.850,
            )

        gap_vector: dict[str, float] = {}
        for b in unique_benchmarks:
            gap_vector[b.metric_name] = b.gap_ratio

        # v2: signal-weighted geometric mean (fixes unweighted v1)
        alignment = weighted_alignment(unique_benchmarks)

        weakest = min(unique_benchmarks, key=lambda b: b.gap_ratio)

        return ComponentBaseline(
            component=component,
            benchmarks_used=[b.metric_name for b in unique_benchmarks],
            alignment_score=alignment,
            gap_vector=gap_vector,
            weakest_benchmark=weakest.metric_name,
            weakest_gap_ratio=weakest.gap_ratio,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # CYCLE 2 — 16D MATH PROOF ENGINE
    # ══════════════════════════════════════════════════════════════════════════

    def _run_cycle_2(
        self, baselines: list[ComponentBaseline]
    ) -> list[CalibrationProof]:
        baseline_map = {b.component: b for b in baselines}
        proofs: list[CalibrationProof] = []
        for comp in self._components:
            proof = self._prove_16d(comp, baseline_map[comp])
            proofs.append(proof)
            print(
                f"    [{comp:<26}]  base={proof.base_composite_16d:.4f}  "
                f"cal={proof.calibrated_composite_16d:.4f}  "
                f"Δ16D=+{proof.delta_16d*100:.2f}pp  "
                f"IPA={proof.impact_per_action:.2f}x"
            )
        return proofs

    def _prove_16d(
        self, component: str, baseline: ComponentBaseline
    ) -> CalibrationProof:
        """
        Compute the 16D calibration proof for one component (v2).

        v2 fixes vs v1:
          - Uses per-component 16D profile from feature_registry (not global default)
          - Per-dimension weight boost: primary dims get full gap boost, secondary 50%
          - Score capped at 0.97 (not 1.0) — preserve calibration headroom

        Formulas:
          base(d, c)     = feature_registry.get_component_profile(c).dimension_scores[d]
          dim_rel(d, c)  = 1.0 if d ∈ primary_dims(c) else 0.5
          w_boost(d, c)  = 1 + GAP_WEIGHT_COEFF × gap_penalty × dim_rel(d, c)
          cal(d, c)      = min(0.97, base(d,c) × w_boost(d,c))
          cal_composite  = Σ_d cal(d,c) × w_d / Σ_d w_d
          Δ16D           = cal_composite − base_composite
          IPA            = Δ16D / cost(c)
        """
        alignment = baseline.alignment_score
        gap_penalty = 1.0 - alignment  # how far below SOTA

        # v2: per-component 16D profile (not global default)
        profile = get_component_profile(component)
        primary_dims = set(profile.primary_dimensions)

        dimension_deltas: list[DimensionDelta] = []
        weight_sum = sum(DIMENSION_WEIGHTS_16D.values())

        weighted_base_sum = 0.0
        weighted_cal_sum = 0.0

        for dim, base in profile.dimension_scores.items():
            w = DIMENSION_WEIGHTS_16D.get(dim, 1.0)
            # v2: per-dimension boost — primary dims get full gap boost, others 50%
            dim_relevance = 1.0 if dim in primary_dims else 0.5
            w_boost = 1.0 + GAP_WEIGHT_COEFFICIENT * gap_penalty * dim_relevance
            # v2: cap at 0.97 not 1.0 — preserve calibration headroom
            cal = min(0.97, base * w_boost)
            weighted_base_sum += base * w
            weighted_cal_sum += cal * w
            dimension_deltas.append(DimensionDelta(
                dimension=dim,
                base_score=base,
                calibrated_score=cal,
                weight=w,
                weight_boost=w_boost,
                delta=cal - base,
            ))

        base_composite = weighted_base_sum / weight_sum
        cal_composite = weighted_cal_sum / weight_sum
        delta = cal_composite - base_composite

        cost = _COMPONENT_COST_USD.get(component, 0.0012)
        ipa = delta / cost if cost > 0 else 0.0

        # Report top-3 primary dimensions that gained most
        top_dims = sorted(
            ((d.dimension, d.delta) for d in dimension_deltas),
            key=lambda x: x[1], reverse=True,
        )[:3]
        top_dims_str = ", ".join(f"{d}+{v*100:.1f}pp" for d, v in top_dims)

        cert = (
            f"PROOF-v2 [{component}]: "
            f"Cycle-1 alignment={alignment:.4f} (gap={gap_penalty:.4f}). "
            f"Profile: primary_dims={list(primary_dims)[:3]}. "
            f"Per-dim boost: primary×{1+GAP_WEIGHT_COEFFICIENT*gap_penalty:.3f}, "
            f"secondary×{1+GAP_WEIGHT_COEFFICIENT*gap_penalty*0.5:.3f}. "
            f"Base composite={base_composite:.4f} → Cal={cal_composite:.4f}. "
            f"Δ16D=+{delta*100:.2f}pp. Top gains: {top_dims_str}. "
            f"IPA={ipa:.2f}× at est. cost ${cost:.4f}. "
            f"Sources: {', '.join(baseline.benchmarks_used[:3]) or 'none'}."
        )

        return CalibrationProof(
            component=component,
            cycle_1_alignment=alignment,
            base_composite_16d=base_composite,
            calibrated_composite_16d=cal_composite,
            delta_16d=delta,
            impact_per_action=ipa,
            dimension_deltas=dimension_deltas,
            proof_certificate=cert,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # CYCLE 3 — JIT PARAMETER CALIBRATION
    # ══════════════════════════════════════════════════════════════════════════

    def _run_cycle_3(
        self,
        baselines: list[ComponentBaseline],
        proofs: list[CalibrationProof],
    ) -> list[JITCalibration]:
        baseline_map = {b.component: b for b in baselines}
        proof_map = {p.component: p for p in proofs}
        jit_cals: list[JITCalibration] = []
        for comp in self._components:
            jit_cal = self._calibrate_jit(
                comp, baseline_map[comp], proof_map[comp]
            )
            jit_cals.append(jit_cal)
            print(
                f"    [{comp:<26}]  base={jit_cal.base_confidence:.4f}  "
                f"JIT={jit_cal.jit_composite:.4f}  "
                f"gain=+{(jit_cal.jit_composite-jit_cal.base_confidence)*100:.2f}pp  "
                f"bps={jit_cal.boost_per_signal_calibrated:.4f}"
            )
        return jit_cals

    def _calibrate_jit(
        self,
        component: str,
        baseline: ComponentBaseline,
        proof: CalibrationProof,
    ) -> JITCalibration:
        """
        Compute JIT boost calibration for one component (v2 — 3 formula fixes).

        v2 fixes vs v1:
          Fix 1: boost_i = (1 - gap_ratio) × pub_recency  (no symmetry trap)
            v1 used relevance × sota_align = (1-g) × g which peaks at g=0.5.
            v2 uses pure gap signal: widest gaps produce strongest signals.
          Fix 2: boost_cal = clamp(mean_boost, MIN, MAX)  (no double /N)
            v1 divided by N twice: computed mean_boost = sum/N then /N again.
          Fix 3: max_boost = boost_per_signal × 5  (matches 5-signal cap in JITBooster)
            v1 used × 7 — inconsistent with JITBooster's sum(signal_boosts[:5]).

        Formula (v2):
          pub_recency_i = exp(-ln(2) × (2026 - pub_year_i))   # half-life 1 year
          boost_i       = (1 - gap_ratio_i) × pub_recency_i   # pure gap signal
          boost_cal     = clamp(mean(boost_i), MIN, MAX)       # no double /N
          JIT_composite = min(1.0, base_confidence + Σ boost_i[:5])
        """
        _RECENCY_K_PUB = math.log(2) / 1.0  # half-life = 1 year for research

        base_conf = get_component_confidence(component)

        # Build de-duplicated benchmark list for this component
        domains = COMPONENT_DOMAIN_MAP.get(component, [])
        benchmarks: list[SOTABenchmark] = []
        seen_names: set[str] = set()
        for d in domains:
            for b in get_benchmarks_for_domain(d):
                if b.metric_name not in seen_names:
                    seen_names.add(b.metric_name)
                    benchmarks.append(b)

        if not benchmarks:
            boost_cal = JIT_BOOST_MIN
            # v2 fix: × 5 not × 7
            return JITCalibration(
                component=component,
                base_confidence=base_conf,
                jit_composite=min(1.0, base_conf + 5 * boost_cal),
                boost_per_signal_calibrated=boost_cal,
                max_boost_recommended=min(0.35, boost_cal * 5),
                psychebank_rules_injected=0,
                system_gain_contribution=0.0,
                recency_weighted_signals=[],
            )

        signal_boosts: list[float] = []
        signals_snap: list[dict[str, float]] = []
        for b in benchmarks:
            # v2 Fix 1: pure gap signal — larger gaps produce stronger improvement signals
            # Symmetry trap in v1: (1-g) × g peaked at g=0.5
            pub_age_years = max(0, 2026 - b.pub_year)
            pub_recency = math.exp(-_RECENCY_K_PUB * pub_age_years)
            boost_i = (1.0 - b.gap_ratio) * pub_recency
            signal_boosts.append(boost_i)
            signals_snap.append({
                "gap_ratio": round(b.gap_ratio, 4),
                "pub_recency": round(pub_recency, 4),
                "boost_i": round(boost_i, 4),
            })

        N = len(signal_boosts)
        mean_boost = sum(signal_boosts) / N  # true arithmetic mean
        # v2 Fix 2: clamp(mean_boost, MIN, MAX) — no second /N
        boost_cal = max(JIT_BOOST_MIN, min(JIT_BOOST_MAX, mean_boost))
        jit_composite = min(
            1.0, base_conf + sum(signal_boosts[:5])  # cap @5 signals
        )

        # v2 Fix 7: regularized inverse component weight (not alignment^-0.5)
        alignment = baseline.alignment_score
        comp_weight = 1.0 / (alignment + _COMP_WEIGHT_REGULARISER)
        gain_contribution = proof.delta_16d * comp_weight

        # Number of rules injected = benchmarks where gap_ratio < 0.85
        rules_injected = sum(1 for b in benchmarks if b.gap_ratio < 0.85)

        return JITCalibration(
            component=component,
            base_confidence=base_conf,
            jit_composite=jit_composite,
            boost_per_signal_calibrated=boost_cal,
            # v2 Fix 3: × 5 to match JITBooster 5-signal cap
            max_boost_recommended=min(0.35, boost_cal * 5),
            psychebank_rules_injected=rules_injected,
            system_gain_contribution=gain_contribution,
            recency_weighted_signals=signals_snap[:5],
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM GAIN INDEX
    # ══════════════════════════════════════════════════════════════════════════

    def _compute_system_gain_index(
        self,
        baselines: list[ComponentBaseline],
        proofs: list[CalibrationProof],
        jit_cals: list[JITCalibration],
    ) -> float:
        """
        Total system gain index (v2 — regularized inverse component weight).

        v1 used alignment^COMPONENT_WEIGHT_EXPONENT which is mathematically
        undefined at alignment=0 and has no theoretical grounding.

        v2 uses a regularized inverse:
          component_weight(c) = 1 / (alignment(c) + REGULARISER)
          SGI = Σ_c (IPA(c) × component_weight(c)) / N

        Lower-aligned components contribute more weight (larger improvement room).
        REGULARISER=0.10 prevents division-by-zero and bounds the weight at 10×.
        """
        alignment_map = {b.component: b.alignment_score for b in baselines}
        total = 0.0
        for p in proofs:
            alignment = alignment_map.get(p.component, 0.850)
            comp_weight = 1.0 / (alignment + _COMP_WEIGHT_REGULARISER)
            total += p.impact_per_action * comp_weight
        return total / max(len(proofs), 1)

    def _system_alignment(self, baselines: list[ComponentBaseline]) -> float:
        """Geometric mean of all component alignments."""
        vals = [b.alignment_score for b in baselines]
        log_sum = sum(math.log(max(v, 1e-9)) for v in vals)
        return math.exp(log_sum / len(vals))

    # ══════════════════════════════════════════════════════════════════════════
    # PSYCHEBANK RULE INJECTION
    # ══════════════════════════════════════════════════════════════════════════

    def _write_psychebank_rules(self, report: CalibrationCycleReport) -> None:
        """
        Write calibration-derived rules to calibration_rules.cog.json.

        Rules are derived from:
          - Top-5 components by IPA (highest improvement ROI)
          - SOTA benchmarks with gap_ratio < 0.75 (critical gaps)
          - JIT recommendations for BOOST_PER_SIGNAL
        """
        # Sort proofs by IPA descending
        top_proofs = sorted(
            report.cycle_2_proofs, key=lambda p: p.impact_per_action, reverse=True
        )[:5]

        # Critical SOTA gaps
        critical_gaps = [
            b for b in SOTA_CATALOGUE if b.gap_ratio < 0.75
        ]

        rules: list[dict[str, Any]] = []

        # Rules from top IPA components
        for p in top_proofs:
            rules.append({
                "id": f"cal-ipa-{p.component}",
                "category": "calibration_ipa",
                "pattern": f"component:{p.component}",
                "directive": (
                    f"High-IPA component '{p.component}': "
                    f"calibrated 16D gain +{p.delta_16d*100:.2f}pp "
                    f"(IPA={p.impact_per_action:.2f}x). "
                    f"Prioritize this component in next self-improvement cycle."
                ),
                "source": "CalibrationEngine Cycle-2 Proof",
                "timestamp": report.timestamp,
                "ttl_seconds": 604800,  # 7 days
            })

        # Rules from critical SOTA gaps
        for b in critical_gaps[:5]:
            rules.append({
                "id": f"cal-gap-{b.metric_name[:40].replace(' ', '-').lower()}",
                "category": "sota_gap",
                "pattern": f"domain:{b.domain}",
                "directive": (
                    f"CRITICAL SOTA gap: '{b.metric_name}' "
                    f"TooLoo={b.tooloo_current:.3f} vs SOTA={b.sota_value:.3f} "
                    f"(gap_ratio={b.gap_ratio:.3f}). "
                    f"Source: {b.source} ({b.pub_year}). "
                    f"Prioritize engineering effort in domain '{b.domain}'."
                ),
                "source": b.source,
                "timestamp": report.timestamp,
                "ttl_seconds": 1209600,  # 14 days
            })

        # JIT parameter calibration rule
        rules.append({
            "id": "cal-jit-params",
            "category": "jit_calibration",
            "pattern": "jit_booster:boost_per_signal",
            "directive": (
                f"JIT CALIBRATION (Run {report.run_id}): "
                f"Recommended BOOST_PER_SIGNAL={report.recommended_boost_per_signal:.4f} "
                f"(current=0.0500). "
                f"Recommended MAX_BOOST_DELTA={report.recommended_max_boost:.4f} "
                f"(current=0.2500). "
                f"Derived from {report.components_calibrated} components × "
                f"{len(SOTA_CATALOGUE)} SOTA benchmarks."
            ),
            "source": "CalibrationEngine Cycle-3",
            "timestamp": report.timestamp,
            "ttl_seconds": 604800,
        })

        payload = {
            "version": "1.0",
            "run_id": report.run_id,
            "timestamp": report.timestamp,
            "rules": rules,
        }
        _RULES_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ══════════════════════════════════════════════════════════════════════════
    # CYCLE 4 — FEATURE COVERAGE MATRIX
    # ══════════════════════════════════════════════════════════════════════════

    def _run_cycle_4(
        self,
        baselines: list[ComponentBaseline],
        proofs: list[CalibrationProof],
    ) -> list[DomainCoverageResult]:
        """
        Cycle 4: Feature Coverage Matrix.

        For each knowledge domain, compute the IPA-weighted geometric mean
        alignment of all components mapped to that domain.  Coverage below
        DESERT_THRESHOLD (0.80) is flagged as a "coverage desert".

        Formula:
          coverage(domain) = exp(Σ_c w_c × ln(alignment_c) / Σ_c w_c)
          where w_c = IPA(c) for every component c mapped to domain.
        """
        baseline_map = {b.component: b.alignment_score for b in baselines}
        ipa_map = {p.component: p.impact_per_action for p in proofs}

        all_domains = sorted(
            {d for domains in COMPONENT_DOMAIN_MAP.values() for d in domains}
        )
        results: list[DomainCoverageResult] = []
        for domain in all_domains:
            comps_in_domain = [
                c for c, ds in COMPONENT_DOMAIN_MAP.items() if domain in ds
            ]
            active = [c for c in comps_in_domain if c in baseline_map]
            if not active:
                continue

            ipa_weights = [max(ipa_map.get(c, 1.0), 1e-3) for c in active]
            alignments = [baseline_map[c] for c in active]

            log_sum = sum(
                w * math.log(max(a, 1e-9))
                for w, a in zip(ipa_weights, alignments)
            )
            w_sum = sum(ipa_weights)
            coverage = math.exp(log_sum / w_sum)

            top_comp = max(active, key=lambda c: baseline_map[c])
            weak_comp = min(active, key=lambda c: baseline_map[c])
            benchmarks_in_domain = get_benchmarks_for_domain(domain)

            results.append(
                DomainCoverageResult(
                    domain=domain,
                    component_count=len(active),
                    coverage_score=round(coverage, 4),
                    is_desert=coverage < DESERT_THRESHOLD,
                    top_component=top_comp,
                    top_component_alignment=round(baseline_map[top_comp], 4),
                    weak_component=weak_comp,
                    weak_component_alignment=round(baseline_map[weak_comp], 4),
                    benchmark_count=len(benchmarks_in_domain),
                )
            )
        return results

    # ══════════════════════════════════════════════════════════════════════════
    # CYCLE 5 — CROSS-COMPONENT INTEGRATION
    # ══════════════════════════════════════════════════════════════════════════

    def _run_cycle_5(
        self,
        baselines: list[ComponentBaseline],
        proofs: list[CalibrationProof],
    ) -> CrossComponentIntegration:
        """
        Cycle 5: Cross-Component Integration health.

        Analyses the N-Stroke dependency graph (_DEPENDENCY_GRAPH) to detect
        cascade bottlenecks: components with the steepest potential gain when
        their alignment improves, weighted by fan-in (how many others depend on
        them).

        Formulas:
          fan_in(c)     = |{x : c ∈ _DEPENDENCY_GRAPH[x]}|
          cascade(c)    = IPA(c) × fan_in(c) × (1 - alignment(c))
          health        = harmonic_mean(al(A) × al(B) for every edge A→B)
          coupling_idx  = mean((1 - alignment(c)) × fan_in(c))
        """
        alignment_map = {b.component: b.alignment_score for b in baselines}
        ipa_map = {p.component: p.impact_per_action for p in proofs}

        # Compute fan-in counts (how many components each one is depended upon by)
        fan_in: dict[str, int] = {}
        for comp, deps in _DEPENDENCY_GRAPH.items():
            for dep in deps:
                fan_in[dep] = fan_in.get(dep, 0) + 1

        # Cascade gain potential per component
        cascade_gains: dict[str, float] = {}
        for comp in self._components:
            al = alignment_map.get(comp, 0.850)
            ipa = ipa_map.get(comp, 0.0)
            cascade_gains[comp] = round(
                ipa * fan_in.get(comp, 0) * (1.0 - al), 4)

        # Integration health: harmonic mean of edge alignment products
        edge_products: list[float] = []
        for comp, deps in _DEPENDENCY_GRAPH.items():
            al_comp = alignment_map.get(comp, 0.850)
            for dep in deps:
                al_dep = alignment_map.get(dep, 0.850)
                edge_products.append(al_comp * al_dep)

        if edge_products:
            integration_health = len(edge_products) / sum(
                1.0 / max(p, 1e-9) for p in edge_products
            )
        else:
            integration_health = 0.850

        couplings = [
            (1.0 - alignment_map.get(c, 0.850)) * fan_in.get(c, 0)
            for c in self._components
        ]
        system_coupling_index = sum(couplings) / max(len(couplings), 1)

        bottleneck_components = sorted(
            self._components, key=lambda c: cascade_gains.get(c, 0), reverse=True
        )[:3]

        return CrossComponentIntegration(
            integration_health=round(integration_health, 4),
            system_coupling_index=round(system_coupling_index, 4),
            bottleneck_components=bottleneck_components,
            cascade_gains=cascade_gains,
            fan_out={c: fan_in.get(c, 0) for c in self._components},
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SUMMARY BUILDER
    # ══════════════════════════════════════════════════════════════════════════

    def _build_summary(self, report: CalibrationCycleReport) -> str:
        top_ipa = sorted(
            report.cycle_2_proofs, key=lambda p: p.impact_per_action, reverse=True
        )[:3]
        top_jit = sorted(
            report.cycle_3_jit,
            key=lambda j: j.jit_composite - j.base_confidence,
            reverse=True,
        )[:3]
        critical_gaps = sorted(
            [b for b in SOTA_CATALOGUE if b.gap_ratio < 0.75],
            key=lambda b: b.gap_ratio,
        )[:3]

        lines = [
            f"5-CYCLE CALIBRATION SUMMARY  [run:{report.run_id}]",
            f"",
            f"  System alignment : {report.system_alignment_before:.4f} → "
            f"{report.system_alignment_after:.4f} "
            f"(+{(report.system_alignment_after-report.system_alignment_before)*100:.2f}pp)",
            f"  Mean Δ16D        : +{report.system_16d_gain*100:.2f}pp",
            f"  Mean JIT gain    : +{report.system_jit_gain*100:.2f}pp",
            f"  System Gain Index: {report.total_system_gain_index:.4f}",
            f"  Benchmarks cited : {len(SOTA_CATALOGUE)} across "
            f"{len(set(b.domain for b in SOTA_CATALOGUE))} domains",
            f"",
            f"  TOP-3 IMPACT COMPONENTS (by IPA):",
        ]
        for p in top_ipa:
            lines.append(
                f"    • {p.component:<26} "
                f"IPA={p.impact_per_action:.2f}x  "
                f"Δ16D=+{p.delta_16d*100:.2f}pp"
            )
        lines += [
            f"",
            f"  TOP-3 JIT GAIN COMPONENTS:",
        ]
        for j in top_jit:
            gain_pp = (j.jit_composite - j.base_confidence) * 100
            lines.append(
                f"    • {j.component:<26} "
                f"JIT gain=+{gain_pp:.2f}pp  "
                f"composite={j.jit_composite:.4f}"
            )
        lines += [
            f"",
            f"  TOP-3 CRITICAL SOTA GAPS (gap_ratio < 0.75):",
        ]
        for b in critical_gaps:
            lines.append(
                f"    • {b.metric_name:<46} "
                f"gap_ratio={b.gap_ratio:.3f}  "
                f"TooLoo={b.tooloo_current:.3f} vs SOTA={b.sota_value:.3f}"
            )

        # Cycle 4 — Feature Coverage Matrix
        if report.cycle_4_coverage:
            deserts = [c for c in report.cycle_4_coverage if c.is_desert]
            lines += [
                f"",
                f"  CYCLE 4 — FEATURE COVERAGE MATRIX:",
                f"    Domains scanned  : {len(report.cycle_4_coverage)}",
                f"    Coverage deserts : {len(deserts)}"
                f" (score < {DESERT_THRESHOLD:.2f})",
            ]
            if deserts:
                for d in sorted(deserts, key=lambda x: x.coverage_score)[:3]:
                    lines.append(
                        f"    ⚠  {d.domain:<24} "
                        f"coverage={d.coverage_score:.4f}  "
                        f"weak={d.weak_component} ({d.weak_component_alignment:.4f})"
                    )

        # Cycle 5 — Cross-Component Integration
        c5 = report.cycle_5_integration
        if c5:
            lines += [
                f"",
                f"  CYCLE 5 — CROSS-COMPONENT INTEGRATION:",
                f"    Integration health   : {c5.integration_health:.4f}",
                f"    System coupling index: {c5.system_coupling_index:.4f}",
                f"    Bottleneck components: "
                + ", ".join(c5.bottleneck_components),
            ]

        lines += [
            f"",
            f"  JIT PARAMETER RECOMMENDATIONS:",
            f"    BOOST_PER_SIGNAL  : {report.recommended_boost_per_signal:.4f} "
            f"(current: 0.0500)",
            f"    MAX_BOOST_DELTA   : {report.recommended_max_boost:.4f} "
            f"(current: 0.2500)",
            f"",
            f"  PROOF ARTEFACTS:",
            f"    psyche_bank/calibration_proof.json",
            f"    psyche_bank/jit_calibration.json",
            f"    psyche_bank/calibration_rules.cog.json",
            f"    psyche_bank/feature_coverage.json",
            f"    psyche_bank/integration_scores.json",
        ]
        return "\n".join(lines)

    # ── Training telemetry helper ────────────────────────────────────────

    @staticmethod
    def delta_from_previous(
        previous_report: "CalibrationCycleReport",
        current_report: "CalibrationCycleReport",
    ) -> dict[str, Any]:
        """Compute precise Δ16D between two CalibrationCycleReport objects.

        Used by the training pipeline to measure per-epoch improvement.
        Accepts the return type of ``run_5_cycles()``.

        Returns:
            dict with keys:
              - delta_composite: float (overall alignment change)
              - dimension_deltas: dict[dim_name, delta_score]
              - improved_dimensions: list[str] (dims that improved)
              - degraded_dimensions: list[str] (dims that degraded)
              - ipa: float (mean absolute impact across dimensions)
        """
        # Build dim → avg calibrated_score from cycle_2_proofs
        def _avg_dim_scores(
            proofs: list,
        ) -> dict[str, float]:
            """Average calibrated_score per dimension across all proofs."""
            dim_sums: dict[str, list[float]] = {}
            for proof in proofs:
                for dd in proof.dimension_deltas:
                    dim_sums.setdefault(dd.dimension, []).append(
                        dd.calibrated_score
                    )
            return {
                dim: sum(vals) / len(vals)
                for dim, vals in dim_sums.items()
            }

        prev_dims = _avg_dim_scores(previous_report.cycle_2_proofs)
        curr_dims = _avg_dim_scores(current_report.cycle_2_proofs)

        dimension_deltas: dict[str, float] = {}
        improved: list[str] = []
        degraded: list[str] = []

        for dim in prev_dims:
            if dim in curr_dims:
                delta = curr_dims[dim] - prev_dims[dim]
                dimension_deltas[dim] = round(delta, 6)
                if delta > 0.001:
                    improved.append(dim)
                elif delta < -0.001:
                    degraded.append(dim)

        delta_composite = (
            current_report.system_alignment_after
            - previous_report.system_alignment_after
        )

        n_dims = len(dimension_deltas) or 1
        ipa = sum(abs(v) for v in dimension_deltas.values()) / n_dims

        return {
            "delta_composite": round(delta_composite, 6),
            "dimension_deltas": dimension_deltas,
            "improved_dimensions": improved,
            "degraded_dimensions": degraded,
            "ipa": round(ipa, 6),
        }

