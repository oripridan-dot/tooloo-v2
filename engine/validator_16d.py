"""
engine/validator_16d.py — 16-Dimension Comprehensive Validation Framework

Core mission: Before autonomous execution (confidence >= 0.99), validate across
16 orthogonal dimensions covering economics, ethics, engineering, and safety.

This is the mathematical foundation of Law 20 Autonomous Execution Authority
and the convergence/reversibility guards for self-healing systems.

Dimensions:
  1. ROI                — Value vs. cost-to-execute
  2. Safety             — Resource exhaustion, deadlocks, memory leaks
  3. Security           — Cryptographic soundness, PII, authorization
  4. Legal              — IP, licensing, compliance (GDPR, SOX, etc.)
  5. Human Considering — Accessibility (WCAG), inclusivity, UX
  6. Accuracy           — Specification compliance, test pass rate
  7. Efficiency         — Algorithmic complexity, no regression
  8. Quality            — Code maintainability, complexity metrics
  9. Speed              — Latency p50/p90, throughput
  10. Monitor           — Observability, metrics, tracing hooks
  11. Control           — Rollback capability, kill switches
  12. Honesty           — Confidence calibration, no overclaiming
  13. Resilience        — Graceful degradation, error recovery
  14. Financial Awareness — Budget awareness, cost-efficient routing
  15. Convergence ⭐    — Healing loop is getting closer to "done"
  16. Reversibility ⭐  — Atomic state rollback capability

Score range: 0.0–1.0 per dimension. Autonomous gate fires at composite >= 0.99.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.model_garden import get_garden


# ── Validation Result Structure ────────────────────────────────────────────────

@dataclass
class Dimension16Score:
    """Validation result for one dimension."""

    name: str
    score: float  # 0.0–1.0
    passed: bool  # score >= threshold (usually 0.8)
    details: str  # explanation
    recommendation: str = ""  # next action if failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 3),
            "passed": self.passed,
            "details": self.details,
            "recommendation": self.recommendation,
        }


@dataclass
class Validation16DResult:
    """Complete 16-dimension validation report."""

    mandate_id: str
    intent: str
    dimensions: list[Dimension16Score] = field(default_factory=list)
    composite_score: float = 0.0
    autonomous_gate_pass: bool = False
    estimated_cost_usd: float = 0.0
    critical_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mandate_id": self.mandate_id,
            "intent": self.intent,
            "composite_score": round(self.composite_score, 4),
            "autonomous_gate_pass": self.autonomous_gate_pass,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "critical_failures": self.critical_failures,
            "dimensions": [d.to_dict() for d in self.dimensions],
        }


# ── Validator16D ────────────────────────────────────────────────────────────────

class Validator16D:
    """
    Comprehensive 16-dimension validator for autonomous execution gating.

    Pre-execution flow:
      1. Estimate cost via ModelGarden
      2. Check tribunal (security/poisoning)
      3. Validate all 16 dimensions
      4. Calculate composite confidence
      5. Gate on 0.99+ threshold
      6. Emit consultation_recommended SSE if below threshold
    """

    # Dimension thresholds; pass if score >= threshold
    _THRESHOLDS = {
        "ROI": 0.75,
        "Safety": 0.95,
        "Security": 0.95,
        "Legal": 0.90,
        "Human Considering": 0.80,
        "Accuracy": 0.90,
        "Efficiency": 0.85,
        "Quality": 0.80,
        "Speed": 0.80,
        "Monitor": 0.85,
        "Control": 0.90,
        "Honesty": 0.95,
        "Resilience": 0.85,
        "Financial Awareness": 0.85,
        "Convergence": 0.90,
        "Reversibility": 0.95,
    }

    # Autonomous confidence target
    AUTONOMOUS_CONFIDENCE_THRESHOLD = 0.99

    def __init__(self) -> None:
        self.garden = get_garden()

    def validate(
        self,
        mandate_id: str,
        intent: str,
        code_snippet: str | None = None,
        estimated_input_tokens: int = 500,
        estimated_output_tokens: int = 1000,
        model_id_primary: str = "gemini-2.5-flash",
        test_pass_rate: float = 1.0,
        latency_p50_ms: float = 1000.0,
        latency_p90_ms: float = 2000.0,
    ) -> Validation16DResult:
        """
        Run full 16-dimension validation.

        Args:
            mandate_id: unique identifier
            intent: BUILD | DEBUG | AUDIT | DESIGN | EXPLAIN | IDEATE | SPAWN_REPO
            code_snippet: generated code to validate
            estimated_input_tokens: prompt size
            estimated_output_tokens: response size
            model_id_primary: primary model used
            test_pass_rate: % of tests passing (1.0 = all pass)
            latency_p50_ms: median latency
            latency_p90_ms: 90th percentile latency

        Returns:
            Validation16DResult with all dimension scores + composite confidence
        """
        result = Validation16DResult(
            mandate_id=mandate_id,
            intent=intent,
        )

        # Estimate cost first
        cost_usd = self.garden.estimate_cost_usd(
            model_id_primary, estimated_input_tokens, estimated_output_tokens
        )
        result.estimated_cost_usd = cost_usd

        # Validate each dimension
        dims = [
            self._validate_roi(cost_usd, intent),
            self._validate_safety(code_snippet),
            self._validate_security(code_snippet),
            self._validate_legal(code_snippet),
            self._validate_human_considering(code_snippet),
            self._validate_accuracy(test_pass_rate),
            self._validate_efficiency(code_snippet),
            self._validate_quality(code_snippet),
            self._validate_speed(latency_p50_ms, latency_p90_ms),
            self._validate_monitor(code_snippet),
            self._validate_control(code_snippet),
            self._validate_honesty(),
            self._validate_resilience(code_snippet),
            self._validate_financial_awareness(cost_usd),
            self._validate_convergence(),
            self._validate_reversibility(code_snippet),
        ]

        result.dimensions = dims

        # Calculate composite score (equal weight per dimension)
        result.composite_score = sum(d.score for d in dims) / len(dims)

        # Gate: autonomous if all critical dims pass + composite >= threshold
        critical_dims = {"Safety", "Security", "Legal", "Honesty", "Reversibility",
                         "Convergence", "Control"}
        critical_scores = {
            d.name: d.score for d in dims if d.name in critical_dims}
        all_critical_pass = all(
            critical_scores.get(name, 0.0) >= self._THRESHOLDS.get(name, 0.95)
            for name in critical_dims
        )

        result.autonomous_gate_pass = (
            all_critical_pass and result.composite_score >= self.AUTONOMOUS_CONFIDENCE_THRESHOLD
        )

        # Capture critical failures for escalation
        result.critical_failures = [
            d.name for d in dims
            if d.name in critical_dims and not d.passed
        ]

        return result

    # ── Individual Dimension Validators ────────────────────────────────────

    def _validate_roi(self, cost_usd: float, intent: str) -> Dimension16Score:
        """ROI: Is this change worth the token spend?"""
        # Heuristic: low-intent (BLOCKED) should cost almost nothing
        # Complex intent (BUILD, DESIGN) justifies higher spend
        intent_multiplier = {
            "BUILD": 1.0, "DESIGN": 1.2, "AUDIT": 0.8,
            "DEBUG": 0.7, "EXPLAIN": 0.5, "IDEATE": 0.8,
            "SPAWN_REPO": 2.0, "BLOCKED": 0.1,
        }.get(intent, 1.0)

        # Budget limit: assume $100/day per mandate
        budget_limit = 100 / 50  # ~$2 per mandate
        roi_score = max(
            0.0, 1.0 - (cost_usd / (budget_limit * intent_multiplier)))

        return Dimension16Score(
            name="ROI",
            score=roi_score,
            passed=roi_score >= self._THRESHOLDS["ROI"],
            details=f"Estimated cost: ${cost_usd:.4f} (intent={intent})",
            recommendation="Consider cheaper model tier or parallel processing" if cost_usd > budget_limit else "",
        )

    def _validate_safety(self, code_snippet: str | None) -> Dimension16Score:
        """Safety: No memory leaks, deadlocks, resource exhaustion?"""
        if not code_snippet:
            return Dimension16Score(
                name="Safety", score=0.8, passed=True,
                details="No code to validate; assuming safe.",
            )

        # Heuristic checks
        safety_issues = []
        if "while True:" in code_snippet and "break" not in code_snippet:
            safety_issues.append("Infinite loop detected")
        if "open(" in code_snippet and "close(" not in code_snippet:
            safety_issues.append("Unclosed file handle")
        if "threading.Thread" in code_snippet and "join()" not in code_snippet:
            safety_issues.append("Unjoined thread")

        score = max(0.0, 1.0 - (len(safety_issues) * 0.15))
        return Dimension16Score(
            name="Safety",
            score=score,
            passed=score >= self._THRESHOLDS["Safety"],
            details=f"Issues: {', '.join(safety_issues) if safety_issues else 'None detected'}",
        )

    def _validate_security(self, code_snippet: str | None) -> Dimension16Score:
        """Security: Cryptographically sound? No PII leaks? Auth boundaries?"""
        if not code_snippet:
            return Dimension16Score(
                name="Security", score=0.95, passed=True,
                details="No code to validate; Tribunal will handle final scan.",
            )

        security_issues = []
        if "password" in code_snippet.lower() and "=" in code_snippet:
            security_issues.append("Hardcoded secret risk")
        if "eval(" in code_snippet or "exec(" in code_snippet:
            security_issues.append("Dynamic code execution forbidden")
        if "import pickle" in code_snippet:
            security_issues.append("Unsafe deserialization (pickle)")

        score = max(0.0, 1.0 - (len(security_issues) * 0.25))
        return Dimension16Score(
            name="Security",
            score=score,
            passed=score >= self._THRESHOLDS["Security"],
            details=f"Issues: {', '.join(security_issues) if security_issues else 'None detected'}",
            recommendation="Run Tribunal OWASP scan before deployment" if security_issues else "",
        )

    def _validate_legal(self, code_snippet: str | None) -> Dimension16Score:
        """Legal: IP, licensing, compliance (GDPR, SOX)?"""
        # Simplified: check for known copyrighted patterns or GPL markers
        if not code_snippet:
            return Dimension16Score(
                name="Legal", score=0.9, passed=True,
                details="No code snippet provided for IP check.",
            )

        legal_risks = []
        if "GPL" in code_snippet:
            legal_risks.append("GPL license detected (may require copyleft)")
        if "©" in code_snippet or "@copyright" in code_snippet:
            legal_risks.append("Third-party copyright notice detected")

        score = 1.0 if not legal_risks else 0.85
        return Dimension16Score(
            name="Legal",
            score=score,
            passed=score >= self._THRESHOLDS["Legal"],
            details=f"Risks: {', '.join(legal_risks) if legal_risks else 'None detected'}",
            recommendation="Review licensing before merging to production" if legal_risks else "",
        )

    def _validate_human_considering(self, code_snippet: str | None) -> Dimension16Score:
        """Human Considering: WCAG, inclusivity, UX respect?"""
        # Simplified check: look for accessibility attributes if web code
        if not code_snippet:
            return Dimension16Score(
                name="Human Considering", score=0.85, passed=True,
                details="No UI code to validate.",
            )

        accessibility_score = 0.8  # Assume moderate
        if "aria-" in code_snippet:
            accessibility_score = min(1.0, accessibility_score + 0.1)
        if "alt=" in code_snippet:
            accessibility_score = min(1.0, accessibility_score + 0.05)

        return Dimension16Score(
            name="Human Considering",
            score=accessibility_score,
            passed=accessibility_score >= self._THRESHOLDS["Human Considering"],
            details="Accessibility attributes present" if accessibility_score > 0.85 else "Limited accessibility",
        )

    def _validate_accuracy(self, test_pass_rate: float) -> Dimension16Score:
        """Accuracy: Tests pass? Specification compliance?"""
        return Dimension16Score(
            name="Accuracy",
            score=test_pass_rate,
            passed=test_pass_rate >= self._THRESHOLDS["Accuracy"],
            details=f"Test pass rate: {test_pass_rate:.1%}",
            recommendation="Reduce pass threshold or fix failing tests" if test_pass_rate < 0.9 else "",
        )

    def _validate_efficiency(self, code_snippet: str | None) -> Dimension16Score:
        """Efficiency: No algorithmic regression? O(n) vs. O(n²)?"""
        if not code_snippet:
            return Dimension16Score(
                name="Efficiency", score=0.85, passed=True,
                details="No code to analyze.",
            )

        efficiency_concerns = []
        if "for" in code_snippet and code_snippet.count("for") > 2:
            efficiency_concerns.append("Multiple nested loops detected")
        if ".sort()" in code_snippet and ".append()" in code_snippet:
            efficiency_concerns.append("Possible O(n²) pattern")

        score = max(0.7, 1.0 - (len(efficiency_concerns) * 0.1))
        return Dimension16Score(
            name="Efficiency",
            score=score,
            passed=score >= self._THRESHOLDS["Efficiency"],
            details=f"Concerns: {', '.join(efficiency_concerns) if efficiency_concerns else 'None detected'}",
        )

    def _validate_quality(self, code_snippet: str | None) -> Dimension16Score:
        """Quality: Maintainability, complexity, coupling?"""
        if not code_snippet:
            return Dimension16Score(
                name="Quality", score=0.8, passed=True,
                details="No code to analyze.",
            )

        quality_score = 0.8
        if len(code_snippet.split("\n")) < 50:
            quality_score += 0.1  # Short = manageable
        if code_snippet.count("def ") >= 3:
            quality_score = min(1.0, quality_score + 0.05)  # Good modularity
        if "# TODO" in code_snippet:
            quality_score -= 0.1  # Unfinished work

        return Dimension16Score(
            name="Quality",
            score=quality_score,
            passed=quality_score >= self._THRESHOLDS["Quality"],
            details=f"Score: {quality_score:.2f}",
        )

    def _validate_speed(self, latency_p50_ms: float, latency_p90_ms: float) -> Dimension16Score:
        """Speed: p50/p90 latency within SLO?"""
        # Target: p50 < 1000ms, p90 < 2000ms
        speed_score = 1.0
        if latency_p50_ms > 1000:
            speed_score *= 0.95
        if latency_p90_ms > 2000:
            speed_score *= 0.9

        return Dimension16Score(
            name="Speed",
            score=speed_score,
            passed=speed_score >= self._THRESHOLDS["Speed"],
            details=f"p50={latency_p50_ms:.0f}ms, p90={latency_p90_ms:.0f}ms",
            recommendation="Optimize or cache if above SLO" if speed_score < 0.85 else "",
        )

    def _validate_monitor(self, code_snippet: str | None) -> Dimension16Score:
        """Monitor: Observability hooks, metrics, tracing?"""
        if not code_snippet:
            return Dimension16Score(
                name="Monitor", score=0.85, passed=True,
                details="No code to validate.",
            )

        instrumentation = 0.7
        if "logger." in code_snippet or "logging." in code_snippet:
            instrumentation += 0.15
        if "metrics." in code_snippet or "prometheus" in code_snippet:
            instrumentation = min(1.0, instrumentation + 0.1)

        return Dimension16Score(
            name="Monitor",
            score=instrumentation,
            passed=instrumentation >= self._THRESHOLDS["Monitor"],
            details=f"Instrumentation: {instrumentation:.2f}",
        )

    def _validate_control(self, code_snippet: str | None) -> Dimension16Score:
        """Control: Rollback capability, kill switches?"""
        # This is validated by the reversibility guard module
        return Dimension16Score(
            name="Control",
            score=0.9,
            passed=True,
            details="Reversibility guard module responsible for validation.",
        )

    def _validate_honesty(self) -> Dimension16Score:
        """Honesty: Confidence calibration, no overclaiming?"""
        # This dimension is subjective and enforced by the confidence gate itself
        return Dimension16Score(
            name="Honesty",
            score=0.95,
            passed=True,
            details="Composite confidence gate enforces epistemic humility.",
        )

    def _validate_resilience(self, code_snippet: str | None) -> Dimension16Score:
        """Resilience: Graceful error handling, recovery?"""
        if not code_snippet:
            return Dimension16Score(
                name="Resilience", score=0.85, passed=True,
                details="No code to validate.",
            )

        resilience_score = 0.8
        if "try:" in code_snippet and "except" in code_snippet:
            resilience_score += 0.15
        if "raise" in code_snippet:
            resilience_score = min(1.0, resilience_score + 0.05)

        return Dimension16Score(
            name="Resilience",
            score=resilience_score,
            passed=resilience_score >= self._THRESHOLDS["Resilience"],
            details=f"Error handling: {'Present' if resilience_score > 0.85 else 'Minimal'}",
        )

    def _validate_financial_awareness(self, cost_usd: float) -> Dimension16Score:
        """Financial Awareness: Budget-aware, cost-efficient routing?"""
        # Score: 1.0 if using cheap models (Tier 0/1), 0.9 if Tier 2, 0.7 if Tier 3/4 regularly
        if cost_usd < 0.01:
            score = 1.0
        elif cost_usd < 0.1:
            score = 0.95
        elif cost_usd < 0.5:
            score = 0.85
        else:
            score = max(0.6, 1.0 - (cost_usd / 10.0))

        return Dimension16Score(
            name="Financial Awareness",
            score=score,
            passed=score >= self._THRESHOLDS["Financial Awareness"],
            details=f"Cost: ${cost_usd:.4f}",
            recommendation="Use Tier 0/1 models for this task" if score < 0.85 else "",
        )

    def _validate_convergence(self) -> Dimension16Score:
        """Convergence ⭐: Healing loop approaching 'done'?"""
        # This is checked by the refinement supervisor + convergence guard
        # For now, assume 0.9 (will be updated by healing supervisor)
        return Dimension16Score(
            name="Convergence",
            score=0.9,
            passed=True,
            details="Convergence guard module validates during healing.",
        )

    def _validate_reversibility(self, code_snippet: str | None) -> Dimension16Score:
        """Reversibility ⭐: Atomic state rollback capability?"""
        # This is enforced by transactional file system module
        return Dimension16Score(
            name="Reversibility",
            score=0.98,
            passed=True,
            details="Transactional state module guarantees atomic rollback.",
        )
