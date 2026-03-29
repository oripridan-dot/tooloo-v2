# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.schemas.six_w.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

from __future__ import annotations
import datetime
import hashlib
import numpy as np
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class SixWProtocol(BaseModel):
    """
    The strict 6W Stamping Protocol for the Sovereign Cognitive Engine.
    Required for all artifacts, engrams, and execution nodes.
    """
    who: str = Field(..., description="The originating agent or principal architect ID")
    what: str = Field(..., description="Action, payload, or intent identifier")
    where: str = Field(..., description="Execution environment or logical sector")
    when: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    why: str = Field(..., description="The teleological goal or parent mandate")
    how: str = Field(..., description="The procedural strategy or tool vector used")
    
    # Optional signature for cryptographic attestation (Rekor/Fulcio compatibility)
    signature: Optional[str] = Field(None, description="Cryptographic signature of the stamp")
    
    # ── Sovereign Telemetry ────────────────────────────────────────────────
    em_verified: bool = Field(False, description="Whether the artifact passed the Verification Gate")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Captured EM_actual metrics (latency, delta, etc.)")

    def vectorize(self) -> np.ndarray:
        """
        Normalized 6D hash vector [0, 1].
        Used as the 'C' (Context) in the (C + I) x E = EM equation.
        """
        vals = []
        for key in ["who", "what", "where", "when", "why", "how"]:
            val_str = str(getattr(self, key))
            h = hashlib.blake2b(val_str.encode(), digest_size=8).hexdigest()
            # Normalize to [0, 1]
            vals.append(int(h, 16) / 0xFFFFFFFFFFFFFFFF)
        return np.array(vals)

    def to_stamp_header(self) -> str:
        """Generates the standardized 6W_STAMP comment block."""
        return (
            f"# 6W_STAMP\n"
            f"# WHO: {self.who}\n"
            f"# WHAT: {self.what}\n"
            f"# WHERE: {self.where}\n"
            f"# WHEN: {self.when}\n"
            f"# WHY: {self.why}\n"
            f"# HOW: {self.how}\n"
            f"# =========================================================="
        )

    class Config:
        frozen = True # Stamping should be immutable once issued

SixWProtocol.model_rebuild()
