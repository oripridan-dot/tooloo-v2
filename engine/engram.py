# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining engram.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.915710
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

from __future__ import annotations
import numpy as np
import datetime
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

# --- 22D VECTOR SPACE CONSTANTS ---
CONTEXT_DIM = 6
INTENT_DIM = 16
TOTAL_DIM = CONTEXT_DIM + INTENT_DIM
EMERGENCE_DIM = 6

MENTAL_DIMENSIONS_16D = [
    "ROI", "Safety", "Security", "Legal", "Human Considering",
    "Accuracy", "Efficiency", "Quality", "Speed", "Monitor",
    "Control", "Honesty", "Resilience", "Financial Awareness",
    "Convergence", "Reversibility"
]

EMERGENCE_LABELS = [
    "Success", "Latency", "Stability", "Quality", "ROI", "Safety"
]

class Context6W(BaseModel):
    """The 'C' in (C+I) x E = EM. Dimensional Context."""
    what: str = Field(..., description="Action/Payload identifier")
    when: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    where: str = Field(..., description="Logical environment (e.g. 'me-west1')")
    who: str = Field(..., description="Originating agent/entity ID")
    how: str = Field(..., description="Procedural strategy")
    why: str = Field(..., description="Teleological goal/Parent mandate")

    def vectorize(self) -> np.ndarray:
        """Normalized 6D hash vector [0, 1]."""
        vals = []
        for key in ["what", "when", "where", "who", "how", "why"]:
            val_str = str(getattr(self, key))
            h = hashlib.blake2b(val_str.encode(), digest_size=8).hexdigest()
            vals.append(int(h, 16) / 0xFFFFFFFFFFFFFFFF)
        return np.array(vals)

class Intent16D(BaseModel):
    """The 'I' in (C+I) x E = EM. Mental Dimensions."""
    values: Dict[str, float] = Field(default_factory=dict)

    def vectorize(self) -> np.ndarray:
        """16D normalized vector."""
        vec = np.zeros(INTENT_DIM)
        for i, dim in enumerate(MENTAL_DIMENSIONS_16D):
            vec[i] = self.values.get(dim, 0.5) # Default to 0.5 (Neutral)
        return vec

class EmergenceVector(BaseModel):
    """The 'EM' in (C+I) x E = EM. Tangible outcomes."""
    val: List[float]
    ts: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_vec(self) -> np.ndarray:
        return np.array(self.val)

    @classmethod
    def from_vec(cls, vec: np.ndarray) -> EmergenceVector:
        return cls(val=vec.flatten().tolist())

class Engram(BaseModel):
    """Unified D = C ⊕ I Payload. The atomic unit of TooLoo PURE."""
    context: Context6W
    intent: Intent16D
    em_pred: Optional[EmergenceVector] = None
    em_actual: Optional[EmergenceVector] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def vectorize(self) -> np.ndarray:
        """22D Unified Engram Vector. Supports override for decompiled assets."""
        if "override_vec" in self.metadata:
            return np.array(self.metadata["override_vec"])
        return np.concatenate([self.context.vectorize(), self.intent.vectorize()])

    def process(self, env_matrix: np.ndarray) -> EmergenceVector:
        """
        PURE Workflow: EM = D x E
        If env_matrix is 22x6, result is 6D EM vector.
        """
        d = self.vectorize()
        if env_matrix.shape == (TOTAL_DIM, EMERGENCE_DIM):
            em_vec = np.dot(d, env_matrix)
        else:
            # Fallback or diagnostic linear response
            em_vec = d[:EMERGENCE_DIM] * 1.0 
        
        return EmergenceVector.from_vec(em_vec)

    @staticmethod
    def infer_from_emergence(em_actual: EmergenceVector, env_matrix: np.ndarray) -> np.ndarray:
        """
        The Anti-Formula: D = EM * E_inv
        Given an observed outcome and the environment physics, infer the required (C+I) intent.
        Uses Moore-Penrose pseudo-inverse for robust reconstruction.
        """
        em_vec = em_actual.to_vec()
        # Moore-Penrose pseudo-inverse of E
        # E is (22, 6), E_pinv is (6, 22)
        e_pinv = np.linalg.pinv(env_matrix)
        
        # D_inferred = em_vec * E_pinv
        d_inferred = np.dot(em_vec, e_pinv)
        return d_inferred

def gelu(x: np.ndarray) -> np.ndarray:
    """Gaussian Error Linear Unit - Non-linear activation for E_sim."""
    return 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x**3)))

def swish(x: np.ndarray, beta: float = 1.0) -> np.ndarray:
    """Swish (SiLU) activation function - Alternative for E_sim."""
    return x * (1 / (1 + np.exp(-beta * x)))
