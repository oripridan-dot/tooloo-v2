# WHAT: DELTA_CALCULATOR.PY | Version: 1.3.0
# WHERE: tooloo_v3_hub/kernel/cognitive/delta_calculator.py
# WHEN: 2026-03-31T23:14:00.000000
# WHY: Rule 16 Empirical Calibration & SOTA Hardening (Fallback Awareness)
# HOW: (Predicted - Actual) Delta with Hardness-Adjusted Emergence
# TIER: T3:architectural-purity
# DOMAINS: kernel, cognitive, measurement, calibration, empirical
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import numpy as np
from typing import Dict, Any, List, Optional
from tooloo_v3_hub.kernel.cognitive.value_evaluator import ValueScore
from tooloo_v3_hub.kernel.cognitive.calibration import get_calibration_engine

logger = logging.getLogger("DeltaCalculator")

class DeltaCalculator:
    """
    The Empirical Feedback Loop for TooLoo V3.
    Calculates the 'Eval Prediction Delta' and triggers self-calibration.
    """

    def __init__(self):
        self.calibrator = get_calibration_engine()
        logger.info("Sovereign Delta Calculator V1.3.0 Awakened (Fallback-Aware).")

    async def calculate_delta(self, predicted: ValueScore, actual: float, domain: str = "logic") -> float:
        """Calculates the prediction error and triggers weight refinement (Rule 16)."""
        pred_value = predicted.total_emergence
        delta = pred_value - actual # Predicted - Actual
        
        logger.info(f"--- Rule 16: Evaluation Delta Verification ---")
        logger.info(f"Predicted Emergence: {pred_value:.4f}")
        logger.info(f"Observed Emergence: {actual:.4f}")
        logger.info(f"Eval Prediction Delta (Δ): {delta:.4f}")
        
        # Self-Healing Threshold (Rule 16 Calibration Intensity)
        drift_percent = abs(delta) / max(0.1, pred_value)
        if drift_percent > 0.50:
            logger.warning(f"EXTREME Intent-Drift Detected ({drift_percent:.1%}). Activating Aggressive Calibration Pulse.")
            await self.calibrator.refine_weights(domain=domain, delta=delta * 0.5) # Forced Learning
        elif drift_percent > 0.15:
            logger.warning(f"High Intent-Drift Detected ({drift_percent:.1%}). Intensifying Calibration Pulse.")
            await self.calibrator.refine_weights(domain=domain, delta=delta * 0.2)
        else:
            await self.calibrator.refine_weights(domain=domain, delta=delta * 0.05)
            
        return delta

    async def calculate_semantic_delta(self, pred_desc: str, actual_desc: str) -> float:
        """
        Calculates the semantic distance between expected and real outcomes.
        Uses the Memory Organ's 32D Heuristic Embedding engine.
        """
        from tooloo_v3_hub.organs.memory_organ.memory_logic import get_memory_logic
        memory = await get_memory_logic()
        
        v1 = np.array(memory._generate_heuristic_embedding(pred_desc))
        v2 = np.array(memory._generate_heuristic_embedding(actual_desc))
        
        # Cosine Similarity
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            similarity = 0.0
        else:
            similarity = np.dot(v1, v2) / (norm_v1 * norm_v2)
            
        semantic_drift = 1.0 - similarity
        logger.info(f"Semantic Alignment: {similarity:.4f} (Drift: {semantic_drift:.4f})")
        return semantic_drift

    def compute_observed_emergence(self, metrics: Dict[str, Any]) -> float:
        """
        Derives an empirical 'Actual' Emergence score from real system metrics.
        Formula: (Purity + Vitality + Hardness_Adjusted_Success) / System_Complexity
        """
        purity = metrics.get("purity", 1.0)
        vitality = metrics.get("vitality", 1.0)
        
        # Hardness Adjustment: Penalize emergence if SOTA Reasoning fallback occurred
        base_success = 1.0 if metrics.get("status") == "success" else 0.5
        if metrics.get("fallback_occurred", False):
            logger.warning("Applying Architectural Hardness Penalty (SOTA Fallback detected).")
            success = base_success * 0.7 # Penalize sub-SOTA results
        else:
            success = base_success
            
        complexity = metrics.get("complexity", 1.0)
        
        # Empirical actual value calculation
        actual = (purity + vitality + success) / max(0.5, complexity)
        return actual

_delta_calculator = None

def get_delta_calculator() -> DeltaCalculator:
    global _delta_calculator
    if _delta_calculator is None:
        _delta_calculator = DeltaCalculator()
    return _delta_calculator
