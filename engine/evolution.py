# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining evolution.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.920379
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

from __future__ import annotations
import numpy as np
import datetime
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Context6W:
    what: str   # The "What": Symbolic payload or action identifier
    when: str   # The "When": ISO 8601 timestamp
    where: str  # The "Where": Logical environment (e.g., 'me-west1', 'tooloo-v2')
    who: str    # The "Who": Originating agent or entity ID
    how: str    # The "How": Procedural strategy or method used
    why: str    # The "Why": Teleological goal or parent mandate ID

    def vectorize(self) -> np.ndarray:
        """
        Translates the 6W context into a normalized 6-dimensional vector.
        Each dimension is a normalized hash of its respective metadata field.
        """
        vals = []
        for key in ["what", "when", "where", "who", "how", "why"]:
            val_str = str(getattr(self, key))
            h = hashlib.blake2b(val_str.encode(), digest_size=8).hexdigest()
            # Normalize to [0, 1] range
            vals.append(int(h, 16) / 0xFFFFFFFFFFFFFFFF)
        return np.array(vals)

@dataclass
class EmergenceVector:
    context_vec: np.ndarray
    intent_vec: np.ndarray
    env_matrix: np.ndarray
    val: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def synthesize(cls, context: Context6W, intent: np.ndarray, env: np.ndarray) -> EmergenceVector:
        """
        Computes EM = (C + I) x E
        where C and I are vectors and E is the environment transformation matrix.
        """
        c_vec = context.vectorize()
        # Ensure dimensions match for addition; pad or truncate if necessary
        dim = max(len(c_vec), len(intent))
        c_padded = np.pad(c_vec, (0, max(0, dim - len(c_vec))), mode='constant')
        i_padded = np.pad(intent, (0, max(0, dim - len(intent))), mode='constant')
        
        # Engram = C + I
        engram = c_padded + i_padded
        
        # Result = Engram dot Environment
        # If env is 1D, use element-wise product; if 2D, use matrix-vector product
        if env.ndim == 1:
            env_padded = np.pad(env, (0, max(0, dim - len(env))), mode='constant')
            val = engram * env_padded
        else:
            val = np.dot(env, engram)
            
        return cls(
            context_vec=c_vec,
            intent_vec=intent,
            env_matrix=env,
            val=val,
            metadata={"ts": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "val": self.val.tolist(),
            "context_vec": self.context_vec.tolist(),
            "intent_vec": self.intent_vec.tolist(),
            "metadata": self.metadata
        }

class TribunalAudit:
    """
    The comparative engine for the (C+I) x E = EM workflow.
    Measures the 'surprise' (delta) between prediction and reality.
    
    STAGE 2: Adversarial Hardening.
    """
    @staticmethod
    def calculate_delta(pred: EmergenceVector, actual: EmergenceVector, adversarial_mode: bool = False) -> float:
        """
        Calculates the cosine distance (delta) between prediction and reality.
        In adversarial mode, spikes the delta if certain safety thresholds are breached.
        """
        v1, v2 = pred.val, actual.val
        
        # Ensure same size
        size = max(len(v1), len(v2))
        v1_p = np.pad(v1, (0, max(0, size - len(v1))), mode='constant')
        v2_p = np.pad(v2, (0, max(0, size - len(v2))), mode='constant')
        
        norm1 = np.linalg.norm(v1_p)
        norm2 = np.linalg.norm(v2_p)
        
        if norm1 == 0 or norm2 == 0:
            return 1.0 if (norm1 != norm2) else 0.0
            
        similarity = np.dot(v1_p, v2_p) / (norm1 * norm2)
        similarity = np.clip(similarity, -1.0, 1.0)
        delta = float(1.0 - similarity)
        
        # STAGE 2: Red Team Probe
        # If reality is too predictable in adversarial mode, it might be a simulation trap.
        if adversarial_mode and delta < 0.001:
            # Inject artificial surprise to force evolutionary growth
            delta = 0.51 
            
        return delta

class EvolutionaryController:
    """
    Decides the evolutionary path for the system based on the gap (delta).
    """
    def __init__(self, surprise_threshold: float = 0.05):
        self.surprise_threshold = surprise_threshold

    def evaluate_outcome(self, delta: float, intent_met: bool) -> Dict[str, str]:
        """
        Non-Binary Evaluation Logic:
        - ERROR: Intent not met (Pathway A).
        - SUCCESS_WITH_GROWTH: Intent met, but surprise detected (Pathway B).
        - STABLE_SUCCESS: Intent met and surprise within threshold.
        """
        if not intent_met:
            return {
                "verdict": "ERROR",
                "pathway": "Pathway A",
                "action": "Update Engram Context with surprise delta; Re-plan.",
                "reason": "Intent failed. Reality diverged from goal."
            }
        
        if delta > self.surprise_threshold:
            return {
                "verdict": "SUCCESS_WITH_GROWTH",
                "pathway": "Pathway B",
                "action": "Sync E_sim with E_actual in PsycheBank.",
                "reason": "Intent met, but surprise detected. Reality outperformed or underperformed prediction."
            }
            
        return {
            "verdict": "STABLE_SUCCESS",
            "pathway": "None",
            "action": "Maintain current world model.",
            "reason": "Reality aligned with prediction."
        }
