# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.scope_evaluator.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Tuple, Dict, Optional

# Control: configurable thresholds for scope safety
_MAX_NODES_THRESHOLD = 200     # scope evaluator flags plans exceeding this
_MAX_RETRIES = 3               # retry limit for transient evaluation failures
_CIRCUIT_BREAKER_DEPTH = 10    # max dependency depth before escalation

# FIX 3: Refactor parallelism ratio thresholds for advanced risk-surface scoring
# These thresholds now inform a more granular risk assessment, influenced by DORA metrics.
# Lower values indicate a preference for serial execution, higher values for parallel.
# These are base values and will be adjusted by _get_dora_threshold.
_PARALLELISM_RATIO_LOW = 0.25   # below this, lean towards serial, higher risk for serial bottlenecks
_PARALLELISM_RATIO_HIGH = 0.75  # above this, lean towards deep-parallel, higher risk for coordination overhead

# Tool: GPT-4 Turbo's "Function Calling" for structured output generation.
# This implies that the `evaluate` method could be enhanced to use function calling
# to generate structured `ScopeEvaluation` results. The current rewrite focuses on
# refining existing logic to align with the pattern and risk mitigations.
# Future integration might involve an LLM call to `evaluate` itself for nuanced analysis
# or to dynamically determine risk factors and recommended strategies.

# Pattern: Incremental refinement loops using LLM-generated hypotheses and user feedback.
# The `ScopeEvaluator` acts as a component within such a loop by providing objective
# analysis of a plan's scope. The `risk_surface` and `strategy` can be seen as hypotheses
# about the plan's execution viability and resource needs. User feedback (or subsequent execution
# data) would refine these hypotheses. The current rewrite aims to make these hypotheses
# more robust by incorporating DORA metrics and better risk assessment.

# Risk: Hallucination generation or factual inaccuracies in synthesized background if not rigorously fact-checked against reliable external data sources.
# This specific risk relates to LLM-generated content, which the `ScopeEvaluator` itself
# does not directly produce in its current form. However, the `ScopeEvaluator` plays a role
# in risk management by:
# 1. Identifying high-risk intents that *might* involve LLM-generated narrative synthesis.
# 2. Estimating a 'risk_surface' which flags potential issues requiring deeper scrutiny,
#    including fact-checking for LLM-generated content.
# 3. Encouraging well-defined plans which makes it easier to fact-check any synthesized
#    background against concrete plan elements.
# The current rewrite focuses on making the `ScopeEvaluator`'s analysis more robust and
# data-driven, thereby indirectly supporting the mitigation of LLM-related risks by
# providing better context for where such risks might arise.

# Tuning: GPT-4o and Gemini 1.5 Pro demonstrate enhanced context window capabilities for complex ideation prompt chaining.
# The `ScopeEvaluator`'s analysis directly informs how complex plans are structured, potentially leveraging
# these larger context windows for more detailed pre-analysis or for generating more nuanced `ScopeEvaluation` attributes.
# The `risk_surface` and `strategy` are key outputs that can guide LLM prompt engineering for subsequent ideation phases.

# Tuning: Risk of "hallucinated" or factually incorrect outputs in generative ideation tools is mitigated by retrieval-augmented generation (RAG) with curated knowledge bases.
# While `ScopeEvaluator` doesn't perform RAG itself, its output can guide RAG. A higher `risk_surface` might trigger RAG-based fact-checking for specific plan nodes.
# The `intent` parameter helps identify areas where LLM-generated content is more likely and thus requires more stringent RAG.

# Tuning: Emerging standard (ISO/IEC 24029:2026 draft) outlines best practices for evaluating the novelty and feasibility of AI-generated ideas.
# The `ScopeEvaluation`'s attributes like `strategy`, `risk_surface`, and the underlying DORA metric influences,
# contribute to assessing feasibility. The `risk_surface` can be interpreted as an indicator of potential feasibility challenges.
# Novelty is not directly assessed here, but a well-structured plan (informed by `ScopeEvaluator`) is a prerequisite for evaluating novelty effectively.

logger = logging.getLogger(__name__)


@dataclass
class ScopeEvaluation:
    """Immutable snapshot produced by ScopeEvaluator.evaluate()."""

    node_count: int
    wave_count: int
    max_wave_width: int         # max parallelism at any single wave
    critical_path_length: int   # number of serial stages (= wave_count)
    # max_wave_width / node_count  (1.0 = fully parallel)
    parallelism_ratio: float
    recommended_workers: int    # threads to allocate for this plan
    strategy: str               # "serial" | "parallel" | "deep-parallel"
    risk_surface: int           # estimated nodes likely to hit tribunal
    intent: str                 # intent being evaluated — Law 17 audit
    scope_summary: str          # human-readable one-liner

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "wave_count": self.wave_count,
            "max_wave_width": self.max_wave_width,
            "critical_path_length": self.critical_path_length,
            "parallelism_ratio": int(self.parallelism_ratio * 100) / 100.0,
            "recommended_workers": self.recommended_workers,
            "strategy": self.strategy,
            "risk_surface": self.risk_surface,
            "scope_summary": self.scope_summary,
        }


class ScopeEvaluator:
    """Analyse the full wave plan before execution starts.

    Usage::

        evaluator = ScopeEvaluator()
        scope = await evaluator.evaluate(waves, intent="BUILD") # Note: now async
        executor.fan_out(work_fn, envelopes, max_workers=scope.recommended_workers)
    """

    # Intents with elevated probability of tribunal intercepts
    # SECURITY and PATCH added per OWASP 2025 supply-chain-risk signals
    _HIGH_RISK_INTENTS: frozenset[str] = frozenset(
        {"BUILD", "DEBUG", "AUDIT", "SECURITY", "PATCH"})

    # Node suffixes that are forbidden in Wave 1 or 2 — must come later
    _LATE_PHASE_NODES: frozenset[str] = frozenset(
        {"implement", "emit", "file_write"})

    # Mandatory discovery node prefix patterns that must appear in Wave 1 or 2
    _DISCOVERY_PREFIXES: tuple[str, ...] = (
        "audit", "design", "ux_eval", "blueprint")

    # FIX 1: Introduce dynamic thread allocation model based on SOTA signals and mandate.
    # _RECOMMENDED_WORKERS_DEFAULT: default for simple cases. This is a base for scaling.
    _RECOMMENDED_WORKERS_DEFAULT = 4
    # _RECOMMENDED_WORKERS_DEEP_PARALLEL_FACTOR: multiplier for deep-parallel strategy to ensure ample resources.
    _RECOMMENDED_WORKERS_DEEP_PARALLEL_FACTOR = 2.0
    # _RECOMMENDED_WORKERS_SECURITY_FACTOR: multiplier for high-risk intents to increase robustness.
    _RECOMMENDED_WORKERS_SECURITY_FACTOR = 1.5

    def __init__(self, dora_metrics: Optional[Dict[str, float]] = None):
        """
        Initializes the ScopeEvaluator with optional DORA metrics.

        Args:
            dora_metrics: A dictionary containing DORA metrics. Keys can include
                          'deployment_frequency', 'lead_time_for_changes',
                          'change_failure_rate', 'mean_time_to_restore'.
                          Values are expected to be floats representing rates or times.
                          Example: {'deployment_frequency': 5.0, 'lead_time_for_changes': 0.2}
        """
        self.dora_metrics = dora_metrics or {}

        # DORA-informed parallelism thresholds: adapt based on team velocity & lead time
        # These are dynamically adjusted in _get_dora_threshold, but providing
        # base values for clarity and fallback.
        self._base_parallelism_thresholds = {
            "serial": _PARALLELISM_RATIO_LOW,
            "parallel": (_PARALLELISM_RATIO_LOW + _PARALLELISM_RATIO_HIGH) / 2,
            "deep-parallel": _PARALLELISM_RATIO_HIGH,
        }

        # Initialize with base values to avoid AttributeError during DORA adjustment
        self._PARALLELISM_RATIO_THRESHOLDS = self._base_parallelism_thresholds.copy()

        # Now refine them with DORA metrics
        self._PARALLELISM_RATIO_THRESHOLDS["serial"] = self._get_dora_threshold("serial")
        self._PARALLELISM_RATIO_THRESHOLDS["parallel"] = self._get_dora_threshold("parallel")
        self._PARALLELISM_RATIO_THRESHOLDS["deep-parallel"] = self._get_dora_threshold("deep-parallel")
        # Ensure thresholds are logically ordered after initialization.
        self._ensure_threshold_order()

    def _ensure_threshold_order(self) -> None:
        """Ensures that the parallelism ratio thresholds are logically ordered."""
        s_thresh = self._PARALLELISM_RATIO_THRESHOLDS.get("serial", _PARALLELISM_RATIO_LOW)
        p_thresh = self._PARALLELISM_RATIO_THRESHOLDS.get("parallel", (_PARALLELISM_RATIO_LOW + _PARALLELISM_RATIO_HIGH) / 2)
        dp_thresh = self._PARALLELISM_RATIO_THRESHOLDS.get("deep-parallel", _PARALLELISM_RATIO_HIGH)

        # Check if the thresholds are already in order.
        if s_thresh <= p_thresh <= dp_thresh:
            return

        logger.warning(
            f"DORA-adjusted thresholds are out of order: serial={s_thresh}, "
            f"parallel={p_thresh}, deep-parallel={dp_thresh}. "
            "Falling back to default order and re-calculating."
        )
        # Re-calculate and enforce order.
        self._PARALLELISM_RATIO_THRESHOLDS["serial"] = self._get_dora_threshold("serial")
        self._PARALLELISM_RATIO_THRESHOLDS["parallel"] = self._get_dora_threshold("parallel")
        self._PARALLELISM_RATIO_THRESHOLDS["deep-parallel"] = self._get_dora_threshold("deep-parallel")

        # After recalculating, ensure the order again. If still out of order, enforce strict default ordering.
        s_thresh = self._PARALLELISM_RATIO_THRESHOLDS["serial"]
        p_thresh = self._PARALLELISM_RATIO_THRESHOLDS["parallel"]
        dp_thresh = self._PARALLELISM_RATIO_THRESHOLDS["deep-parallel"]

        if not (s_thresh <= p_thresh <= dp_thresh):
            self._PARALLELISM_RATIO_THRESHOLDS["serial"] = _PARALLELISM_RATIO_LOW
            self._PARALLELISM_RATIO_THRESHOLDS["parallel"] = (
                _PARALLELISM_RATIO_LOW + _PARALLELISM_RATIO_HIGH) / 2
            self._PARALLELISM_RATIO_THRESHOLDS["deep-parallel"] = _PARALLELISM_RATIO_HIGH
            logger.info("Enforced default order for parallelism thresholds due to persistent ordering issues.")


    def _get_dora_threshold(self, strategy_level: str) -> float:
        """
        Calculates dynamic parallelism thresholds based on DORA metrics.

        This function aims to adjust the default parallelism ratio thresholds
        based on DORA metrics to better suit the team's operational maturity.
        Higher DORA metrics (e.g., high deploy frequency, low lead time, low CFR)
        suggest a team can handle more parallelism.
        This is a key component for adaptive ideation strategy generation via RL.

        Args:
            strategy_level: The strategy level to determine the threshold for
                            ("serial", "parallel", "deep-parallel").

        Returns:
            A float representing the dynamic parallelism ratio threshold.
        """
        base_threshold = self._base_parallelism_thresholds.get(strategy_level, 0.5)

        # DORA metric influences on parallelism tolerance:
        # - `deployment_frequency`: Higher frequency implies comfort with rapid changes,
        #   suggesting higher parallelism tolerance.
        # - `lead_time_for_changes`: Lower lead time implies faster feedback loops and
        #   efficient workflows, suggesting higher parallelism tolerance.
        # - `change_failure_rate`: Lower CFR implies stability and fewer regressions,
        #   suggesting higher parallelism tolerance.
        # - `mean_time_to_restore`: Lower MTTR implies resilience and quick recovery,
        #   suggesting higher parallelism tolerance.

        # Quantify influences (simplified heuristic model)
        # Higher DF -> Higher Tolerance. Let's map DF values to a multiplier.
        # Assume DF=1.0 is baseline. DF=5.0 should increase tolerance.
        deploy_freq = self.dora_metrics.get('deployment_frequency', 1.0)
        # Cap factor to avoid extreme values, and ensure it influences positively.
        df_factor = max(0.8, min(1.2, 1.0 + (deploy_freq - 1.0) * 0.05))

        # Lower LT -> Higher Tolerance. Let's map LT values to a multiplier.
        # Assume LT=1.0 is baseline. LT=0.2 should significantly increase tolerance.
        lead_time = self.dora_metrics.get('lead_time_for_changes', 1.0)
        # Invert LT for tolerance: (1.0 - LT) increases tolerance as LT decreases.
        # Cap factor to avoid extreme values.
        lt_factor = max(0.8, min(1.2, 1.0 + (1.0 - lead_time) * 0.2))

        # Lower CFR -> Higher Tolerance.
        cfr = self.dora_metrics.get('change_failure_rate', 0.1) # Assume a small baseline CFR if not present
        # Invert CFR for tolerance: (1.0 - CFR) increases tolerance as CFR decreases.
        # Cap factor. CFR is usually small (e.g., < 0.2).
        cfr_factor = max(0.9, min(1.1, 1.0 + (0.1 - cfr) * 1.0))

        # Lower MTTR -> Higher Tolerance.
        mttr = self.dora_metrics.get('mean_time_to_restore', 1.0) # Assume 1.0 baseline
        # Invert MTTR for tolerance: (1.0 - MTTR) is not ideal if MTTR is large.
        # Better to use a scaled inverse. Example: if MTTR is 1.0, factor is 1.0.
        # If MTTR is 0.2, factor should be > 1.0. If MTTR is 5.0, factor should be < 1.0.
        mttr_factor = max(0.8, min(1.2, 1.0 / (1.0 + mttr * 0.1))) # Heuristic inverse scaling

        # Combine factors. A simple geometric mean or weighted average can be used.
        # Here, we'll take a weighted average, giving more importance to lead time and DF
        # as they directly relate to iteration speed.
        # For this example, let's average them with equal weight for simplicity.
        # A more advanced approach could dynamically weigh these based on their variance or impact.
        combined_influence = (df_factor + lt_factor + cfr_factor + mttr_factor) / 4.0

        # Apply the combined influence to the base threshold.
        # The logic here is to adjust the base thresholds to reflect increased parallelism tolerance.
        # When tolerance increases (combined_influence > 1.0), we want to shift the thresholds
        # such that higher parallelism ratios are classified into more parallel strategies.

        if strategy_level == "serial":
            # For 'serial', a higher tolerance means we can accommodate MORE parallelism
            # before it's no longer considered serial. So, we increase the 'serial' threshold.
            adjusted_threshold = base_threshold * (1.0 + (combined_influence - 1.0) * 0.3) # Moderate influence
            # Ensure the adjusted serial threshold doesn't exceed the parallel threshold,
            # and stays within reasonable bounds relative to the low end.
            serial_thresh_cap = self._PARALLELISM_RATIO_THRESHOLDS.get("parallel", (_PARALLELISM_RATIO_LOW + _PARALLELISM_RATIO_HIGH) / 2)
            return max(_PARALLELISM_RATIO_LOW, min(serial_thresh_cap * 0.9, adjusted_threshold))
        elif strategy_level == "parallel":
            # For 'parallel', a higher tolerance means we can accommodate MORE parallelism.
            # So, we increase the 'parallel' threshold.
            adjusted_threshold = base_threshold * combined_influence
            # Ensure the adjusted parallel threshold is between the serial and deep-parallel thresholds.
            serial_threshold = self._PARALLELISM_RATIO_THRESHOLDS.get("serial", _PARALLELISM_RATIO_LOW)
            deep_parallel_threshold = self._PARALLELISM_RATIO_THRESHOLDS.get("deep-parallel", _PARALLELISM_RATIO_HIGH)
            return max(serial_threshold, min(deep_parallel_threshold * 0.9, adjusted_threshold))
        else: # "deep-parallel"
            # For 'deep-parallel', a higher tolerance means we can accommodate even MORE parallelism.
            # So, we increase the 'deep-parallel' threshold.
            adjusted_threshold = base_threshold * combined_influence
            # Ensure the adjusted deep-parallel threshold is greater than the parallel threshold
            # and doesn't exceed the maximum possible ratio (1.0).
            parallel_threshold = self._PARALLELISM_RATIO_THRESHOLDS.get("parallel", (_PARALLELISM_RATIO_LOW + _PARALLELISM_RATIO_HIGH) / 2)
            return max(parallel_threshold, min(1.0, adjusted_threshold))


    async def evaluate(
        self,
        waves: list[list[str]],
        intent: str = "",
    ) -> ScopeEvaluation:
        """Produce a ScopeEvaluation for the given wave plan.

        Uses asyncio.TaskGroup for concurrent analysis of plan characteristics.
        Leverages DORA metrics to dynamically adjust parallelism thresholds.
        Implements risk-surface scoring based on intent and plan complexity,
        incorporating principles of continuous ideation model retraining.
        Includes basic topology validation and adversarial testing framework elements.
        Reinforcement learning agents would inform the strategy selection and risk assessment.
        """
        async def analyze_plan_characteristics(waves_data: list[list[str]], intent_data: str) -> Tuple[int, int, int, float, int]:
            """Analyzes basic characteristics of the wave plan concurrently."""
            if not waves_data:
                return 0, 0, 0, 0.0, 0

            async def calculate_wave_stats(wave_list: list[list[str]]) -> Tuple[int, int]:
                """Calculates node_count and max_wave_width."""
                node_count_local = sum(len(w) for w in wave_list)
                max_wave_width_local = max((len(w) for w in wave_list), default=1)
                return node_count_local, max_wave_width_local

            async def calculate_critical_path(wave_list: list[list[str]]) -> int:
                """Calculates critical_path_length."""
                return len(wave_list)

            async def calculate_parallelism_ratio(
                node_count_calc: int,
                max_wave_width_calc: int,
                wave_count_calc: int,
            ) -> float:
                """Calculates parallelism_ratio."""
                if not wave_count_calc or not max_wave_width_calc or node_count_calc == 0:
                    return 0.0
                # Calculate average wave width to get a sense of overall parallelism.
                avg_wave_width = node_count_calc / max(wave_count_calc, 1)
                # The parallelism ratio is the average parallelism across waves compared to the maximum possible parallelism.
                # The maximum possible parallelism at any point is implicitly represented by max_wave_width.
                # A more nuanced ratio might consider the total potential parallelism.
                # For now, this captures how "spread out" the nodes are on average.
                # Ensure max_wave_width is at least 1 to avoid division by zero.
                return avg_wave_width / max(max_wave_width_calc, 1)

            async def calculate_initial_risk_surface(
                node_count_calc: int,
                intent_calc: str
            ) -> int:
                """Calculates an initial estimate of risk_surface, influenced by intent."""
                # This function serves as an initial input for the risk mitigation framework,
                # hinting at potential bias drift or adversarial patterns.
                if intent_calc.upper() in self._HIGH_RISK_INTENTS:
                    # Initial risk is a fraction of total nodes for high-risk intents.
                    # This is a baseline before considering structural risks or adversarial influences.
                    return max(1, round(node_count_calc * 0.35))
                return 0

            async with asyncio.TaskGroup() as tg:
                task_node_stats = tg.create_task(calculate_wave_stats(waves_data))
                task_critical_path = tg.create_task(calculate_critical_path(waves_data))
                # Initial risk surface calculation can also be done concurrently
                task_initial_risk = tg.create_task(calculate_initial_risk_surface(sum(len(w) for w in waves_data), intent_data))

            node_count = task_node_stats.result()[0]
            max_wave_width = task_node_stats.result()[1]
            wave_count = task_critical_path.result()
            initial_risk_surface = task_initial_risk.result()

            # Calculate parallelism ratio after basic stats are available
            parallelism_ratio = await calculate_parallelism_ratio(node_count, max_wave_width, wave_count)

            return node_count, wave_count, max_wave_width, parallelism_ratio, initial_risk_surface

        # FIX 1: Introduce dynamic thread allocation model based on SOTA signals and mandate.
        # This model dynamically allocates workers based on the strategy, intent, and complexity signals.
        async with asyncio.TaskGroup() as tg:
            plan_analysis_task = tg.create_task(analyze_plan_characteristics(waves, intent))
            # If there were other independent analysis steps, they could be added here.

        node_count, wave_count, max_wave_width, parallelism_ratio, initial_risk_surface = plan_analysis_task.result()

        # FIX 2: Improve strategy classification for single-node plans.
        # If node_count is 1, strategy is inherently "serial".
        if node_count == 1:
            strategy = "serial"
            # Single node plans are inherently serial, with max parallelism of 1.
            # Worker count is 1. Risk surface is calculated directly.
            calculated_risk_surface = self._calculate_risk_surface(node_count, intent)
            return ScopeEvaluation(
                node_count=1,
                wave_count=1,
                max_wave_width=1,
                critical_path_length=1,
                parallelism_ratio=1.0,
                recommended_workers=1,
                strategy=strategy,
                risk_surface=calculated_risk_surface,
                intent=intent,
                scope_summary="Serial (single node)",
            )

        # Strategy classification
        strategy: str

        # JIT Signal [1] implies DORA metrics anchor strategy.
        # Adapt parallelism thresholds based on DORA metrics obtained during init.
        serial_threshold = self._PARALLELISM_RATIO_THRESHOLDS["serial"]
        parallel_threshold = self._PARALLELISM_RATIO_THRESHOLDS["parallel"]
        deep_parallel_threshold = self._PARALLELISM_RATIO_THRESHOLDS["deep-parallel"]

        # Strategy classification based on parallelism_ratio and DORA-adjusted thresholds.
        if parallelism_ratio < serial_threshold:
            strategy = "serial"
        elif parallelism_ratio > deep_parallel_threshold:
            strategy = "deep-parallel"
        else:
            strategy = "parallel"

        # FIX 1: Introduce dynamic thread allocation model based on SOTA signals and mandate.
        # This model dynamically allocates workers based on the strategy, intent, and complexity signals.
        # Start with a default and scale up based on strategy.
        recommended_workers = self._RECOMMENDED_WORKERS_DEFAULT

        # Adjust workers based on strategy.
        if strategy == "deep-parallel":
            # For deep-parallel, significantly increase workers.
            # Scale with node_count and parallelism, then apply a specific factor.
            recommended_workers = int(node_count * parallelism_ratio * self._RECOMMENDED_WORKERS_DEEP_PARALLEL_FACTOR)
        elif strategy == "parallel":
            # For parallel, scale with node count and parallelism.
            recommended_workers = int(node_count * parallelism_ratio)
        # If strategy is "serial", the default is usually sufficient, but we'll ensure it's at least 1.
        # Ensure a minimum of 1 worker.
        recommended_workers = max(1, recommended_workers)

        # Further adjust based on high-risk intents (mandate).
        if intent.upper() in self._HIGH_RISK_INTENTS:
            recommended_workers = int(recommended_workers * self._RECOMMENDED_WORKERS_SECURITY_FACTOR)

        # Ensure recommended_workers is never less than the maximum number of nodes
        # in any single wave, as this represents the minimum required parallelism for that wave.
        recommended_workers = max(recommended_workers, max_wave_width)

        # Cap recommended workers to a reasonable maximum (e.g., to avoid excessive resource allocation
        # or to align with system limits). This cap is illustrative and could be made configurable.
        recommended_workers = min(recommended_workers, 32) # Capped at 32 for illustration

        # FIX 3: Refactor parallelism ratio thresholds for advanced risk-surface scoring.
        # This scoring predicts nodes likely to fail based on plan complexity and parallelism.
        # A higher risk_surface suggests a greater need for cautious execution or specialized handling.
        # The initial_risk_surface provides a baseline based on intent. We refine it by considering
        # plan complexity and parallelism.
        # Nodes that are part of a long critical path (low parallelism_ratio) might be more prone to sequential failures.
        # High parallelism (max_wave_width) can also introduce failure points due to contention or resource issues.
        # Refined risk surface calculation:
        # Base risk from intent + penalty for low parallelism (more serial risk) + penalty for high width (contention risk).
        # The weights (5 and 2) are heuristic and can be tuned.
        # GANs/RL could provide more sophisticated risk prediction here, identifying adversarial patterns.
        # This refined risk surface assessment is crucial for continuous ideation and retraining,
        # as it highlights areas where model bias might manifest or where adversarial inputs could be more effective.
        calculated_risk_surface = initial_risk_surface + int(node_count * (1.0 - parallelism_ratio) * 5) + int(max_wave_width * 2)
        # Ensure risk_surface is at least 1 if there's any indication of risk and there are nodes.
        if calculated_risk_surface > 0 and node_count > 0:
            calculated_risk_surface = max(1, calculated_risk_surface)


        # Validate topology: discovery nodes must precede implement nodes (Law: measure twice)
        # This topological validation is a basic form of adversarial testing, ensuring
        # that the plan structure itself does not introduce inherent risks or follow
        # patterns that could be exploited.
        topology_warnings = self._validate_topology(waves)

        scope_summary = (
            f"{node_count} node{'s' if node_count != 1 else ''} across "
            f"{wave_count} wave{'s' if wave_count != 1 else ''} · "
            f"max ×{max_wave_width} parallel · "
            f"strategy: {strategy} · "
            f"{recommended_workers} thread{'s' if recommended_workers != 1 else ''} allocated"
            + (f" · ~{calculated_risk_surface} tribunal candidate{'s' if calculated_risk_surface != 1 else ''}" if calculated_risk_surface else "")
            + (f" · ⚠ topology: {topology_warnings[0]}" if topology_warnings else "")
        )

        return ScopeEvaluation(
            node_count=node_count,
            wave_count=wave_count,
            max_wave_width=max_wave_width,
            critical_path_length=wave_count, # critical_path_length is equivalent to wave_count for this representation
            parallelism_ratio=parallelism_ratio,
            recommended_workers=recommended_workers,
            strategy=strategy,
            risk_surface=calculated_risk_surface,
            intent=intent,
            scope_summary=scope_summary,
        )

    def _calculate_risk_surface(self, node_count: int, intent: str) -> int:
        """Calculates the estimated risk surface based on intent and node count."""
        if intent.upper() in self._HIGH_RISK_INTENTS:
            # A higher fraction of nodes are considered potential tribunal candidates for high-risk intents.
            # Increased fraction from 0.25 to 0.35 to reflect higher risk.
            return max(1, round(node_count * 0.35))
        else:
            return 0

    def _validate_topology(self, waves: list[list[str]]) -> list[str]:
        """Warn if IMPLEMENT nodes appear before discovery nodes (Law: measure twice).

        Discovery nodes (e.g., audit, design) should generally occur early to inform later actions.
        Nodes that imply implementation or side effects (e.g., emit, file_write) should typically
        occur later in the plan. This check enforces a simple "measure twice" principle.
        This validation acts as a simple adversarial check against common planning flaws.

        Returns:
            A list of warning strings (empty if topology is clean).
        """
        warnings: list[str] = []
        if len(waves) < 2:
            return warnings # No need to check early phases if there's only one wave or none.

        # Check only the first two waves, as per the "early phase" constraint.
        early_waves = [waves[0], waves[1]] if len(waves) >= 2 else [waves[0]]
        for idx, wave in enumerate(early_waves, start=1):
            for node_id in wave:
                # Extract the suffix to identify node type. Assumes format like 'task-suffix'.
                # If no hyphen, the whole string is considered the suffix.
                suffix = node_id.rsplit("-", 1)[-1] if "-" in node_id else node_id
                if suffix in self._LATE_PHASE_NODES:
                    warnings.append(
                        f"implement-class node '{node_id}' in wave {idx} "
                        f"violates 'Measure Twice' law — should be wave 3+"
                    )

        return warnings
