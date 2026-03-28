# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.memory.tiers.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime, UTC

class MemoryTier(str, Enum):
    TIER_1_EPHEMERAL = "surface"   # In-memory, volatile context, audio buffers
    TIER_2_STRUCTURAL = "internal" # VectorStore, PsycheBank, Local persistence
    TIER_3_SOVEREIGN = "global"    # GitHub-backed, macro-rules, bit-perfect benchmarks

class MemoryRecord(BaseModel):
    """A single record across the 3 memory tiers."""
    tier: MemoryTier
    id: str
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class MemoryState(BaseModel):
    """The unified state of the system memory across all tiers."""
    ephemeral_count: int = 0
    structural_count: int = 0
    sovereign_count: int = 0
    last_sync_at: Optional[str] = None
    delta_closure_rate: float = 1.0 # 1.0 = No gap, 0.0 = Critical Dissonance
