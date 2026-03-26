"""
engine/model_selector.py — Re-export shim for backwards compatibility.

ModelSelector and ModelSelection have been folded into ``engine/model_garden.py``.
Import from ``engine.model_garden`` for new code.
"""
from engine.model_garden import (  # noqa: F401
    ModelSelection,
    ModelSelector,
    get_full_tier_models,
)

# Dynamic mapping for backward compatibility
_tiers = get_full_tier_models()
TIER_1_MODEL = _tiers[1]
TIER_2_MODEL = _tiers[2]
TIER_3_MODEL = _tiers[3]
TIER_4_MODEL = _tiers[4]
VERTEX_TIER_MAP = _tiers

__all__ = [
    "ModelSelection",
    "ModelSelector",
    "TIER_1_MODEL",
    "TIER_2_MODEL",
    "TIER_3_MODEL",
    "TIER_4_MODEL",
    "VERTEX_TIER_MAP",
]
