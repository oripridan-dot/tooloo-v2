"""
engine/model_selector.py — Re-export shim for backwards compatibility.

ModelSelector and ModelSelection have been folded into ``engine/model_garden.py``.
Import from ``engine.model_garden`` for new code.
"""
from engine.model_garden import (  # noqa: F401
    ModelSelection,
    ModelSelector,
    TIER_1_MODEL,
    TIER_2_MODEL,
    TIER_3_MODEL,
    TIER_4_MODEL,
    VERTEX_TIER_MAP,
)

__all__ = [
    "ModelSelection",
    "ModelSelector",
    "TIER_1_MODEL",
    "TIER_2_MODEL",
    "TIER_3_MODEL",
    "TIER_4_MODEL",
    "VERTEX_TIER_MAP",
]
