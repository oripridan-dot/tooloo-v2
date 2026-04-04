# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MODULE_VALUE_EVALUATOR | Version: 1.2.0
# WHERE: tooloo_v4_hub/kernel/cognitive/value_evaluator.py
# WHEN: 2026-03-31T21:15:00.000000
# WHY: (C+I)/ENV = Emergence (TooLoo Formula Integration)
# HOW: 16D Dimensional Intent Mapping and Vector Aggregation
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, value, measurement, constitution
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from tooloo_v4_hub.kernel.governance.billing_manager import get_billing_manager

logger = logging.getLogger("SovereignValueEvaluator")

class ValueScore(BaseModel):
    # TooLoo Formula Components
    context_6w: float = 1.0
    intent_16d: float = 1.0
    environment: float = 1.0
    
    # Constituent Metrics
    purity: float = 1.0
    vitality: float = 1.0
    efficiency: float = 1.0
    sota_alignment: float = 1.0
    
    # 16D Weights (The Intent Vector)
    dimensions: Dict[str, float] = Field(default_factory=dict)
    
    # Rule 14: Real-World Cost Grounding
    cost_usd: float = 0.0

    @property
    def total_emergence(self) -> float:
        """
        The V4 TooLoo Formula: (C+I)/(ENV * ε) = Emergence
        Rule 1: Mandatory (C+I)/*ENV Formula Compliance
        """
        # Ensure denominators are never zero to prevent singularity
        safe_env = max(0.1, self.environment)
        safe_eff = max(0.1, self.efficiency)
        
        # Scaling Emergence for higher resolution
        base_em = (self.context_6w + self.intent_16d) / (safe_env * safe_eff)
        return float(base_em * self.sota_alignment)

    @property
    def value_score(self) -> float:
        """V4 ValueScore: (Emergence * Vitality * Focus) / (Complexity * Financial_Cost_Factor)."""
        complexity = self.dimensions.get("Complexity", 0.5)
        # Rule 14: Financial Penalty if cost exceeds $0.10 for a single cognitive pulse
        financial_penalty = 1.0 + (self.cost_usd * 10.0) 
        
        safe_comp = max(0.1, complexity)
        return (self.total_emergence * self.vitality * self.focus_coefficient) / (safe_comp * financial_penalty)

    # 16D Multi-Provider Extension
    provider: Optional[str] = None
    model: Optional[str] = None
    routing_reason: Optional[str] = None
    
    # [AUTOPOIETIC_REFUSE] Dynamic Scaling (Rule 16)
    focus_coefficient: float = 1.0
    creativity_multiplier: float = 1.0

class SovereignValueEvaluator:
    # 16-Rule Sovereign Dimensions (Normalized)
    D16 = [
        "Architectural_Foresight", "Root_Cause_Analysis", "Syntax_Precision",
        "Constitutional", "Efficiency", "Quality", "Speed", "Safety",
        "Security", "Complexity", "Financial", "Legal", "Human_Factor",
        "Limitations", "Environment", "Vector_Intent"
    ]

    def __init__(self):
        logger.info("Sovereign Formula Engine V1.2.0 Initialized.")

    def calculate_emergence(self, goal: str, context_var: Dict[str, Any]) -> ValueScore:
        """Calculates Predicted Emergence based on the TooLoo Formula (C+I)/ENV."""
        logger.info(f"Predicting Emergence for goal: '{goal}'")
        goal_l = goal.lower()
        
        # 1. Intent (I) - Map Goal to 16D Vector
        dimensions = self.map_to_16d(goal)
        
        # Rule 7: Respect User Vision (Merge manual intent if provided)
        manual_intent = context_var.get("intent", {})
        if manual_intent:
            logger.info(f"Merging manual intent vector: {manual_intent}")
            dimensions.update(manual_intent)
            
        avg_intent = sum(dimensions.values()) / len(dimensions)
        
        # 2. Context (C) - 6W Coverage
        context_score = 1.0
        if any(w in goal.lower() for w in ["fix", "drifting", "refine"]):
            context_score = 0.8 # Context is remediation-heavy
            
        # 3. Environment (ENV) - Operational Coefficient
        env_coeff = 1.0
        env_str = context_var.get("environment") or context_var.get("env_state", {}).get("env")
        if env_str == "gcp": env_coeff = 1.2
        elif env_str == "local": env_coeff = 0.8
        
        # 4. SOTA Alignment
        sota_alignment = 1.0
        if context_var.get("jit_boosted", False) or manual_intent.get("Rule_16_Calibration"):
            sota_alignment = 1.2

        # 5. Focus & Creativity (Self-Correction Rule)
        focus = 1.0
        creat = 1.0
        
        # Heuristic: Focus increases if goal is 'direct', Creat if 'exploratory'
        if any(w in goal_l for w in ["fix", "now", "stop", "direct", "execute"]):
            focus = 1.2
        if any(w in goal_l for w in ["imagine", "evolve", "future", "creative", "architect"]):
            creat = 1.2

        # 6. Rule 14: Financial Grounding
        billing = get_billing_manager()
        summary = billing.get_session_summary()
        financial_vitality = summary.get("financial_vitality", 1.0)

        score = ValueScore(
            context_6w=context_score,
            intent_16d=avg_intent,
            environment=env_coeff,
            sota_alignment=sota_alignment,
            dimensions=dimensions,
            focus_coefficient=focus,
            creativity_multiplier=creat,
            cost_usd=summary.get("total_cost_usd", 0.0),
            vitality=financial_vitality # Grounding vitality in financial health
        )
        
        return score

    def map_to_16d(self, goal: str) -> Dict[str, float]:
        """Maps a natural language goal to 16-dimensional Constitutional weights."""
        goal_l = goal.lower()
        weights = {d: 0.5 for d in self.D16} # Base normalization
        
        # Intent Vectoring logic: Rule 5 Purity
        if any(w in goal_l for w in ["architect", "foresight", "next", "refactor"]):
            weights["Architectural_Foresight"] = 0.95
            weights["Complexity"] = 0.8
        if any(w in goal_l for w in ["fix", "why", "root", "failure", "diagnostic"]):
            weights["Root_Cause_Analysis"] = 0.98
            weights["Complexity"] = 0.9
        if any(w in goal_l for w in ["syntax", "purity", "precision", "hardening", "bit-perfect"]):
            weights["Syntax_Precision"] = 1.0
            weights["Quality"] = 0.9
        if any(w in goal_l for w in ["constitution", "rule", "protocol", "governance", "audit"]):
            weights["Constitutional"] = 1.0
            weights["Safety"] = 0.9
        if any(w in goal_l for w in ["speed", "latency", "fast", "realtime"]):
            weights["Speed"] = 1.0
        if any(w in goal_l for w in ["security", "safety", "threat", "leak"]):
            weights["Security"] = 1.0
            weights["Safety"] = 1.0
        if any(w in goal_l for w in ["cost", "billing", "resource", "efficiency"]):
            weights["Financial"] = 0.9
            weights["Efficiency"] = 0.95
        if any(w in goal_l for w in ["ux", "human", "ui", "chat", "visual"]):
            weights["Human_Factor"] = 0.95
            
        return weights

_evaluator = None

def get_value_evaluator() -> SovereignValueEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = SovereignValueEvaluator()
    return _evaluator