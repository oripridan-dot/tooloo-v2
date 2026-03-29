# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.organs.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from engine.schemas.six_w import SixWProtocol

class OrganType(str, Enum):
    HUB = "hub"             # Reasoning, DAG Orchestration, Planning
    SPOKE_GENERIC = "spoke" # Ephemeral Sandbox, Tool Execution
    SPOKE_AUDIO = "audio"   # Claudio DSL, Spectral Synthesis
    MEMORY = "memory"       # VectorStore, PsycheBank, Sovereign tiers

class OrganPayload(BaseModel):
    """
    Standardized inter-organ communication payload.
    Must always carry a 6W Stamp for provenance.
    """
    stamp: SixWProtocol
    origin: OrganType
    target: OrganType
    data: Dict[str, Any]
    priority: int = 1 # 1-10

class HubOrgan:
    """The Brain: Responsible for high-level reasoning and goal decomposition."""
    def __init__(self):
        self.type = OrganType.HUB

class SpokeOrgan:
    """The Limbs: Responsible for task execution and tool invocation."""
    def __init__(self):
        self.type = OrganType.SPOKE_GENERIC

class AudioOrgan:
    """The Voice: Responsible for bit-perfect audio synthesis and spectral gap detection."""
    def __init__(self):
        self.type = OrganType.SPOKE_AUDIO

class MemoryOrgan:
    """The Soul: Responsible for persistent knowledge and long-term engrams."""
    def __init__(self):
        self.type = OrganType.MEMORY
