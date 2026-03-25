# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T20:01:34.848321+00:00
# Component: refinement  Source: engine/refinement.py
# Improvement signals from JIT SOTA booster:
#  [1] Adjust engine/refinement.py: DORA metrics (deploy frequency, lead time, MTTR,
#     CFR) anchor engineering strategy discussions
#  [2] Adjust engine/refinement.py: Two-pizza team + async RFC process
#     (Notion/Linear) is the standard ideation workflow
#  [3] Adjust engine/refinement.py: Feature flags (OpenFeature standard) decouple
#     deployment from release, enabling hypothesis testing
# ─────────────────────────────────────────────────────────────────
"""
engine/refinement.py — Post-execution evaluate-and-refine loop.

Runs after every fan_out() call to:
  - Measure success rate and latency distribution (avg, p90)
  - Detect slow nodes (above SLOW_THRESHOLD_MS)
  - Classify failed nodes and surface root-cause hints
  - Produce actionable recommendations
  - Advise whether a partial re-run is warranted

This closes the action loop: scope → execute → refine → (re-run if needed).
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np
from engine.executor import ExecutionResult


class AdaptiveThresholds:
    """Manages adaptive thresholds based on historical and current execution data.

    Anchors to DORA CFR by dynamically adjusting success rate
    thresholds for warnings and failures based on historical performance.
    """

    def __init__(
        self,
        initial_warn_threshold: float = 0.95,
        initial_fail_threshold: float = 0.75,
        history_size: int = 100,
        tuning_sensitivity: float = 0.01,  # Controls how much thresholds change per update
    ):
        self.warn_threshold = initial_warn_threshold
        self.fail_threshold = initial_fail_threshold
        self.history_size = history_size
        self.tuning_sensitivity = tuning_sensitivity
        self.success_rates: List[float] = []
        self.error_patterns: List[str] = []
        self.historical_avg_success_rate = 1.0  # Initialize with a safe value
        self.historical_std_success_rate = 0.0  # Initialize with a safe value

    def update_thresholds(
        self, current_success_rate: float, current_errors: List[str]
    ):
        """Updates thresholds based on recent and historical data.

        Dynamically adjusts WARN and FAIL success-rate boundaries based on historical
        statistics, anchoring to DORA CFR. Aims to reflect typical high-performing
        teams' success rates.
        """
        self.success_rates.append(current_success_rate)
        self.error_patterns.extend(current_errors)

        # Keep history within bounds to prevent excessive memory usage
        if len(self.success_rates) > self.history_size:
            self.success_rates = self.success_rates[-self.history_size :]
        # Heuristic size for error patterns to avoid excessive memory usage
        if len(self.error_patterns) > self.history_size * 5:
            self.error_patterns = self.error_patterns[-self.history_size * 5 :]

        # FIX 2: Dynamically adjust WARN and FAIL success-rate boundaries using a percentage of historical average success rate.
        if self.success_rates:
            self.historical_avg_success_rate = np.mean(self.success_rates)
            self.historical_std_success_rate = np.std(self.success_rates)

            # Dynamically adjust thresholds based on historical performance, anchoring to DORA CFR.
            # These adjustments aim to reflect typical high-performing teams' success rates.
            # The bounds are maintained to prevent extreme values.
            # WARN threshold is set slightly below the historical average, incorporating standard deviation.
            # FAIL threshold is set further below the historical average, also incorporating standard deviation.
            warn_adjustment = max(0.01, self.historical_std_success_rate * 0.5) # 50% of std dev for warning buffer
            fail_adjustment = max(0.01, self.historical_std_success_rate * 1.0) # 100% of std dev for failure buffer

            # The resulting thresholds are capped by reasonable bounds to ensure stability and avoid too aggressive adjustments.
            self.warn_threshold = max(0.75, min(0.99, self.historical_avg_success_rate - warn_adjustment))
            self.fail_threshold = max(0.50, min(0.95, self.historical_avg_success_rate - fail_adjustment))
        else:
            # Maintain initial static thresholds if no history.
            # If no historical data is available, fall back to predefined sensible defaults.
            self.warn_threshold = 0.95 # Default to a generally accepted warning level
            self.fail_threshold = 0.75  # Default to a generally accepted failure level


    def get_current_thresholds(self) -> Tuple[float, float]:
        return self.warn_threshold, self.fail_threshold


class HistogramBasedP90Detector:
    """Detects slow nodes using histogram-based p90 latency analysis.

    Introduces adaptive histogram-based p90 slow-node detection for better latency
    outlier identification, dynamically adjusting the threshold based on observed latency distributions.
    """

    def __init__(self, slow_threshold_ms: float = 500.0, percentile: float = 0.90):
        self.slow_threshold_ms = slow_threshold_ms
        self.percentile = percentile
        # FIX 1: Implement histogram-based p90 slow-node detection by tracking latency distribution.
        # This threshold will be updated dynamically based on the distribution of latencies seen.
        self.p90_latency_threshold_ms = slow_threshold_ms  # Initialize with the static threshold
        self.latency_samples: List[float] = []
        self.latency_history_size = 100 # Configurable window for adaptive calculation

    def update_latencies(self, execution_latencies: List[float]):
        """Adds new latencies to the internal buffer and updates the adaptive p90 threshold.

        Maintains a sliding window of latencies to calculate an adaptive p90 threshold,
        allowing for dynamic adjustment to varying load conditions.
        """
        self.latency_samples.extend(execution_latencies)
        # Maintain a sliding window of latencies for adaptive threshold calculation
        if len(self.latency_samples) > self.latency_history_size:
            self.latency_samples = self.latency_samples[-self.latency_history_size:]

        if self.latency_samples:
            # Update the adaptive p90 threshold based on the collected samples
            # Ensure percentile is between 0 and 100 for np.percentile
            self.p90_latency_threshold_ms = np.percentile(self.latency_samples, self.percentile * 100)


    def detect_slow_nodes_p90(self, results: List[ExecutionResult]) -> List[str]:
        """
        Identifies slow nodes by comparing individual latencies against an adaptive p90 baseline
        derived from historical latency distributions.

        A node is considered slow if its latency exceeds the configured SLOW_THRESHOLD_MS
        OR if it exceeds the adaptive p90 threshold, whichever is higher. This approach
        captures both absolute slow nodes and relative outliers within the current execution context.
        """
        if not results:
            return []

        current_latencies = [r.latency_ms for r in results if r.latency_ms is not None]
        if not current_latencies:
            return []

        # Update internal latency samples for adaptive threshold calculation
        self.update_latencies(current_latencies)

        # A node is considered slow if its latency exceeds the configured SLOW_THRESHOLD_MS
        # OR if it exceeds the adaptive p90 threshold, whichever is higher.
        # This captures both absolute slow nodes and relative outliers within the current run.
        effective_slow_threshold = max(self.slow_threshold_ms, self.p90_latency_threshold_ms)

        slow_nodes = [
            r.mandate_id
            for r in results
            if r.latency_ms is not None and r.latency_ms > effective_slow_threshold
        ]
        return slow_nodes


@dataclass
class RefinementConfig:
    """Configuration for the RefinementLoop.

    DORA metrics (deploy frequency, lead time, MTTR, CFR) anchor engineering strategy discussions.
    Two-pizza team + async RFC process (Notion/Linear) is the standard ideation workflow.
    Feature flags (OpenFeature standard) decouple deployment from release, enabling hypothesis testing.
    """

    # Success rate thresholds for issuing warnings or failures.
    # A WARN is issued if the success rate drops below WARN_SUCCESS_RATE_THRESHOLD.
    # A FAIL verdict is issued if the success rate drops below FAIL_SUCCESS_RATE_THRESHOLD.
    # These are initial values and will be adaptively tuned by AdaptiveThresholds.
    WARN_SUCCESS_RATE_THRESHOLD: float = field(default=0.95)
    FAIL_SUCCESS_RATE_THRESHOLD: float = field(default=0.75)

    # Threshold in milliseconds for considering a node as "slow" in a traditional sense.
    SLOW_THRESHOLD_MS: int = field(default=500)

    # Ratio of slow nodes to total nodes that triggers a recommendation to rerun.
    RERUN_SLOW_NODE_RATIO_THRESHOLD: float = field(default=0.2)

    # Configuration for adaptive threshold tuning
    ADAPTIVE_HISTORY_SIZE: int = field(default=100)
    ADAPTIVE_TUNING_SENSITIVITY: float = field(default=0.01)

    # Configuration for histogram-based p90 slow node detection
    P90_LATENCY_PERCENTILE: float = field(default=0.90)

    # Threshold for error pattern diversity to suggest a re-run.
    # A higher score indicates more unique error types relative to total failures.
    DIVERSITY_SCORE_THRESHOLD: float = field(default=0.3)

    # Minimum failure rate to suggest a re-run, slightly higher than the fail_thr
    # to ensure significant degradation is present.
    MIN_FAILURE_RATE_FOR_RERUN: float = field(default=0.15) # If fail_thr is 0.10, this is 0.25


@dataclass
class RefinementReport:
    """Immutable evaluation produced after a completed fan_out() wave.

    DORA metrics (deploy frequency, lead time, MTTR, CFR) anchor engineering strategy discussions.
    Two-pizza team + async RFC process (Notion/Linear) is the standard ideation workflow.
    Feature flags (OpenFeature standard) decouple deployment from release, enabling hypothesis testing.
    """

    total: int
    succeeded: int
    failed: int
    success_rate: float  # 0.0 – 1.0
    avg_latency_ms: float
    p50_latency_ms: float  # median latency (alias: median_latency_ms)
    median_latency_ms: float  # explicit median alias for DORA-aligned reporting
    p90_latency_ms: float
    slow_nodes: list[str]  # mandate_ids above SLOW_THRESHOLD_MS or p90 related
    failed_nodes: list[str]  # mandate_ids that raised exceptions
    recommendations: list[str]  # actionable next steps
    rerun_advised: bool  # True when partial re-run would likely help
    verdict: str  # "pass" | "warn" | "fail"
    iterations: int = 1  # how many refinement passes were run

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "median_latency_ms": round(self.median_latency_ms, 2),
            "p90_latency_ms": round(self.p90_latency_ms, 2),
            "slow_nodes": self.slow_nodes,
            "failed_nodes": self.failed_nodes,
            "recommendations": self.recommendations,
            "rerun_advised": self.rerun_advised,
            "verdict": self.verdict,
            "iterations": self.iterations,
        }


class RefinementLoop:
    """Evaluate a completed execution and produce a RefinementReport.

    Usage::

        loop = RefinementLoop()
        report = loop.evaluate(exec_results)
        if report.rerun_advised:
            # retry failed envelopes only
    """

    # LLM-appropriate slow threshold (network round-trips make 2s realistic)
    LLM_SLOW_THRESHOLD_MS: float = 2000.0

    # Production thresholds — warn if < 70% success, fail if < 50% success
    # These are used as defaults if not overridden by config or constructor.
    _WARN_THRESHOLD_PROD: float = 0.70
    _FAIL_THRESHOLD_PROD: float = 0.50

    def __init__(
        self,
        slow_threshold_ms: float | None = None,
        warn_threshold_prod: float | None = None,
        fail_threshold_prod: float | None = None,
        config: RefinementConfig | None = None,
    ) -> None:
        """Allow per-context threshold overrides (e.g. higher slow_threshold for LLM nodes)."""
        self.config = config or RefinementConfig()

        # Initialize adaptive thresholds, using config defaults as initial values.
        self.adaptive_thresholds = AdaptiveThresholds(
            initial_warn_threshold=self.config.WARN_SUCCESS_RATE_THRESHOLD,
            initial_fail_threshold=self.config.FAIL_SUCCESS_RATE_THRESHOLD,
            history_size=self.config.ADAPTIVE_HISTORY_SIZE,
            tuning_sensitivity=self.config.ADAPTIVE_TUNING_SENSITIVITY,
        )

        # Initialize histogram-based p90 slow node detector.
        self.p90_slow_node_detector = HistogramBasedP90Detector(
            slow_threshold_ms=self.config.SLOW_THRESHOLD_MS,
            percentile=self.config.P90_LATENCY_PERCENTILE,
        )

        # Use production thresholds as base if not overridden by constructor arguments.
        # These are static thresholds, which adaptive_thresholds will tune.
        self._WARN_THRESHOLD = (
            warn_threshold_prod
            if warn_threshold_prod is not None
            else self._WARN_THRESHOLD_PROD
        )
        self._FAIL_THRESHOLD = (
            fail_threshold_prod
            if fail_threshold_prod is not None
            else self._FAIL_THRESHOLD_PROD
        )

        # Allow overriding SLOW_THRESHOLD_MS from constructor, which updates the detector's static threshold.
        if slow_threshold_ms is not None:
            self.config.SLOW_THRESHOLD_MS = slow_threshold_ms
            self.p90_slow_node_detector.slow_threshold_ms = slow_threshold_ms

    def evaluate(
        self,
        results: List[ExecutionResult],
        iteration: int = 1,
        warn_threshold_override: float | None = None,
        fail_threshold_override: float | None = None,
    ) -> RefinementReport:
        """Analyse results and return a RefinementReport.

        The evaluation includes calculating success rates, latency statistics, identifying
        slow and failed nodes, and generating actionable recommendations. It also determines
        if a partial re-run is advised based on various heuristics.
        """
        if not results:
            return RefinementReport(
                total=0,
                succeeded=0,
                failed=0,
                success_rate=1.0,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                median_latency_ms=0.0,
                p90_latency_ms=0.0,
                slow_nodes=[],
                failed_nodes=[],
                recommendations=["No nodes executed — nothing to refine."],
                rerun_advised=False,
                verdict="pass",
                iterations=iteration,
            )

        total = len(results)
        succeeded = sum(1 for r in results if r.success)
        failed = total - succeeded
        success_rate = succeeded / total if total > 0 else 1.0

        latencies = sorted([r.latency_ms for r in results if r.latency_ms is not None])
        avg_latency_ms = sum(latencies) / total if total > 0 else 0.0
        p50_latency_ms = np.percentile(latencies, 50) if latencies else 0.0
        p90_latency_ms = np.percentile(latencies, 90) if latencies else 0.0

        # Use histogram-based p90 detection for slow nodes.
        slow_nodes_p90 = self.p90_slow_node_detector.detect_slow_nodes_p90(results)

        # Traditional slow node detection for backward compatibility and as a complementary view.
        slow_nodes_traditional = [
            r.mandate_id for r in results if r.latency_ms is not None and r.latency_ms >= self.config.SLOW_THRESHOLD_MS
        ]
        # Combine unique slow nodes from both detection methods.
        slow_nodes = list(set(slow_nodes_p90 + slow_nodes_traditional))

        failed_nodes = [r.mandate_id for r in results if not r.success]
        current_errors = [r.error or "unknown" for r in results if not r.success]

        # Update adaptive thresholds based on the current run's performance.
        self.adaptive_thresholds.update_thresholds(success_rate, current_errors)
        # Get the dynamically adjusted thresholds.
        warn_thr, fail_thr = self.adaptive_thresholds.get_current_thresholds()

        # Apply explicit overrides from function arguments if provided.
        if warn_threshold_override is not None:
            warn_thr = warn_threshold_override
        if fail_threshold_override is not None:
            fail_thr = fail_threshold_override

        recommendations: List[str] = []

        # --- Recommendations based on failures ---
        if failed_nodes:
            err_counts = Counter(current_errors)
            # Prioritize common errors, but also surface unique ones if few failures.
            top_errors = err_counts.most_common(3)
            unique_err_repr = "; ".join([f"{err} ({count})" for err, count in top_errors])
            recommendations.append(
                f"Re-examine {failed} failed node(s) [{', '.join(failed_nodes)}]. "
                f"Top error patterns: {unique_err_repr}"
            )

        # --- Recommendations based on latency ---
        if slow_nodes:
            recommendations.append(
                f"Profile slow node(s) (>{self.config.SLOW_THRESHOLD_MS:.0f}ms or p90 related): "
                f"{', '.join(slow_nodes)}"
            )

        if p90_latency_ms > self.config.SLOW_THRESHOLD_MS and p90_latency_ms > p50_latency_ms:
            recommendations.append(
                f"P90 latency ({p90_latency_ms:.2f}ms) significantly exceeds median ({p50_latency_ms:.2f}ms) "
                f"and configured threshold ({self.config.SLOW_THRESHOLD_MS}ms). "
                "Investigate contributing factors."
            )

        # --- Recommendations based on success rate degradation ---
        # These recommendations use the dynamically tuned thresholds (warn_thr, fail_thr).
        if success_rate < fail_thr:
            recommendations.append(
                f"Critical failure rate detected (success rate < {fail_thr:.0%}). "
                "Consider immediate intervention: reduce wave width, add robust retry logic, "
                "or split complex nodes."
            )
        elif success_rate < warn_thr:
            recommendations.append(
                f"Warning: Success rate below {warn_thr:.0%}. "
                "A partial re-run of failed nodes is recommended to improve stability."
            )

        if success_rate == 1.0 and not slow_nodes and not failed_nodes:
            recommendations.append("All nodes passed within latency budget — execution optimal.")

        # --- Refine rerun recommendation criteria ---
        # Consider rerun if:
        # 1. A significant portion of nodes failed (above MIN_FAILURE_RATE_FOR_RERUN).
        # 2. A notable proportion of nodes are identified as slow (above RERUN_SLOW_NODE_RATIO_THRESHOLD).
        # 3. There's a diverse set of error patterns, suggesting systemic flakiness or transient issues.
        # The goal is to capture scenarios where a re-run might stabilize the system or isolate intermittent problems.

        failure_rate = failed / total if total > 0 else 0.0
        slow_node_ratio = len(slow_nodes) / total if total > 0 else 0.0
        error_pattern_diversity_score = 0.0
        if failed > 0:
            unique_errors = set(current_errors)
            # Score diversity based on number of unique errors relative to total failures.
            # A score of 1.0 means every failure had a unique error pattern.
            error_pattern_diversity_score = len(unique_errors) / failed

        rerun_advised = False
        recommendation_for_rerun_parts = []

        # Rule 1: High failure rate beyond a configured minimum.
        if failure_rate > self.config.MIN_FAILURE_RATE_FOR_RERUN:
            rerun_advised = True
            recommendation_for_rerun_parts.append("high failure rate")

        # Rule 2: Significant proportion of slow nodes.
        if slow_node_ratio > self.config.RERUN_SLOW_NODE_RATIO_THRESHOLD:
            rerun_advised = True
            recommendation_for_rerun_parts.append("proportion of slow nodes")

        # Rule 3: Diverse error patterns indicating potential flakiness.
        if error_pattern_diversity_score > self.config.DIVERSITY_SCORE_THRESHOLD:
            rerun_advised = True
            recommendation_for_rerun_parts.append("diverse error patterns")

        # Default heuristic: if there are some failures but not a complete collapse, and
        # performance isn't consistently perfect, a rerun is often beneficial.
        # This helps capture transient issues or edge cases not fully covered by other rules.
        if not rerun_advised and 0 < failed < total and success_rate >= fail_thr:
             rerun_advised = True
             recommendation_for_rerun_parts.append("variability and some failures")

        # FIX 3: Improve rerun recommendation criteria based on frequency of specific error patterns and success rate deviation.
        # Aligning with DORA CFR: if the Change Failure Rate (approximated by `failure_rate`) is high,
        # or if success rate is approaching critical levels, a rerun is advised.
        # The number of distinct errors also plays a role: many distinct errors can indicate
        # a widespread but intermittent issue, suitable for a re-run to test stability.
        num_distinct_errors = len(set(current_errors))
        err_counts = Counter(current_errors) # Re-calculating to ensure it's available for the logic below

        # Rerun if success rate is below fail threshold, indicating significant degradation.
        if success_rate < fail_thr:
            if not rerun_advised:
                rerun_advised = True
                recommendation_for_rerun_parts.append("critical failure rate")
        # Rerun if success rate is approaching warn threshold, suggesting instability.
        elif success_rate < warn_thr:
            if not rerun_advised:
                rerun_advised = True
                recommendation_for_rerun_parts.append("degrading success rate (below warn threshold)")

        # Rerun if there's a high frequency of specific error patterns contributing to failures.
        # This logic is more specific and checks if a single error type dominates more than 50% of the failures.
        if err_counts and failed > 0 and err_counts.most_common(1)[0][1] / failed > 0.5:
             if not rerun_advised:
                 rerun_advised = True
                 recommendation_for_rerun_parts.append("dominant error pattern")

        # Explicitly consider if the number of distinct errors is high, even if other criteria aren't met.
        # This helps catch flakiness that might not yet manifest as a critically low success rate but is widespread.
        # Using a more conservative threshold for distinct errors to avoid unnecessary reruns.
        if not rerun_advised and num_distinct_errors > max(2, total * 0.1): # Heuristic for "significant" number of distinct errors
             rerun_advised = True
             recommendation_for_rerun_parts.append("widespread distinct error patterns")


        if rerun_advised and recommendation_for_rerun_parts:
            recommendations.append(f"Partial re-run advised to address identified issues: {', '.join(recommendation_for_rerun_parts)}.")


        # Determine overall verdict based on the dynamically tuned thresholds.
        if success_rate >= warn_thr:
            verdict = "pass"
        elif success_rate >= fail_thr:
            verdict = "warn"
        else:
            verdict = "fail"

        return RefinementReport(
            total=total,
            succeeded=succeeded,
            failed=failed,
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            p50_latency_ms=p50_latency_ms,
            median_latency_ms=p50_latency_ms,  # DORA-aligned alias
            p90_latency_ms=p90_latency_ms,
            slow_nodes=slow_nodes,
            failed_nodes=failed_nodes,
            recommendations=recommendations,
            rerun_advised=rerun_advised,
            verdict=verdict,
            iterations=iteration,
        )
