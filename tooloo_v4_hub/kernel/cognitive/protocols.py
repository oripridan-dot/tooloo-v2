# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: PROTOCOLS.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/protocols.py
# WHY: Rule 10 - Structured Accountability
# HOW: Pydantic Schema Enforcement
# ==========================================================

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class SovereignStamping(BaseModel):
    """Rule 10: 6W Accountability Protocol."""
    who: str = "Buddy"
    what: str
    where: str
    when: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    why: str
    how: str

class ChatDynamics(BaseModel):
    """Rule 16: Cognitive Vitals."""
    intent: str
    stage: str
    load: float = 0.0
    resonance: float = 1.0
    value_score: float = 0.0

class SovereignMessage(BaseModel):
    """The Fundamental Communication Unit."""
    type: str = "buddy_chat"
    role: str = "assistant"
    content: str
    speaker: str = "Buddy"
    dynamics: Optional[ChatDynamics] = None
    stamping: Optional[SovereignStamping] = None
    manifestation: Optional[Dict[str, Any]] = None

class CognitivePulse(BaseModel):
    """Real-time 'Thinking' and 'Status' events."""
    type: str = "thinking_pulse"
    thought: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[float] = None
    payload: Optional[Dict[str, Any]] = None

class HandoverEvent(BaseModel):
    """Rule 18: Cloud Migration Trigger."""
    type: str = "handover_ready"
    cloud_url: str
    msg: str = "Psyche migration sequence ARMED."
    payload: Optional[Dict[str, Any]] = None
