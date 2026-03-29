from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional

class TooLooRequest(BaseModel):
    """Encapsulates a request to the TooLoo engine."""
    prompt: str = Field(..., description="The user's prompt or mandate.")
    session_id: Optional[str] = Field(None, description="Optional session ID for context persistence.")
    intent: str = Field("IDEATE", description="The high-level intent (IDEATE, BUILD, DEBUG, etc.)")
    domain: str = "backend"

class TooLooResponse(BaseModel):
    """Encapsulates a response from the TooLoo engine."""
    response: str
    session_id: str
    violations: List[str] = []
    latency_ms: float
