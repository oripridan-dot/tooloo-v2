# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining roi_feedback.py
# WHERE: engine/calibration
# WHEN: 2026-03-28T15:54:38.946568
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/calibration/roi_feedback.py — 16D ROI Self-Calibration Loop

This component analyzes the ROI history in PsycheBank and suggests 'Calibration Strokes'
to optimize model selection, thinking budgets, and tool usage across the 16D spectrum.
"""

import logging
from typing import Any
from engine.psyche_bank import PsycheBank

logger = logging.getLogger(__name__)

class ROIFeedbackLoop:
    def __init__(self, psyche_bank: PsycheBank | None = None) -> None:
        self.pb = psyche_bank or PsycheBank()

    async def analyze_and_calibrate(self) -> list[dict[str, Any]]:
        """
        Analyze ROI history and return a list of recommended calibration actions.
        """
        history = await self.pb.get_roi_history()
        if not history:
            return []

        recommendations = []
        
        # Group by intent
        intent_stats = {}
        for event in history:
            intent = event.get("intent", "UNKNOWN")
            score = event.get("composite_score", 0.0)
            cost = event.get("estimated_cost_usd", 0.0)
            
            if intent not in intent_stats:
                intent_stats[intent] = {"sum_score": 0.0, "sum_cost": 0.0, "count": 0}
            
            intent_stats[intent]["sum_score"] += score
            intent_stats[intent]["sum_cost"] += cost
            intent_stats[intent]["count"] += 1

        for intent, stats in intent_stats.items():
            avg_score = stats["sum_score"] / stats["count"]
            avg_cost = stats["sum_cost"] / stats["count"]
            
            # Calibration logic: 
            # If avg_score is high (>0.95) but cost is also high, suggest a cheaper model.
            if avg_score > 0.95 and avg_cost > 0.5:
                recommendations.append({
                    "target": f"intent:{intent}",
                    "action": "DOWNGRADE_MODEL",
                    "reason": f"High ROI ({avg_score:.2f}) at high cost (${avg_cost:.2f}). Efficiency gain secondary.",
                    "dimension": "Financial Awareness"
                })
            
            # If avg_score is low (<0.85), suggest increasing thinking budget.
            if avg_score < 0.85:
                recommendations.append({
                    "target": f"intent:{intent}",
                    "action": "INCREASE_THINKING_BUDGET",
                    "reason": f"Sub-optimal ROI ({avg_score:.2f}). Requires more test-time compute.",
                    "dimension": "Accuracy"
                })

        return recommendations

    async def apply_calibration_stroke(self, recommendation: dict[str, Any]) -> bool:
        """
        Persist a calibration rule to PsycheBank based on the recommendation.
        """
        # In a real Tier-5 system, this would modify CogRules or Roadmap behaviors.
        # For now, we inject a 'calibration' rule.
        from engine.psyche_bank import CogRule
        
        rule = CogRule(
            id=f"CALIBRATION_{recommendation['action']}_{recommendation['target'].replace(':', '_')}",
            description=recommendation['reason'],
            pattern=recommendation['target'],
            enforcement="warn",
            category="performance",
            source="vast_learn"
        )
        
        return await self.pb.capture(rule, ttl_seconds=86400) # 24hr TTL for calibration strokes
