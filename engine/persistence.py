"""
engine/persistence.py — Unified file I/O utilities for TooLoo storage.

Provides atomic writes and safe reads for JSON stores, eliminating
duplication across memory, cache, and psyche bank modules.
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

def atomic_write_json(path: Path, data: Any, indent: int = 2) -> None:
    """Safely writes JSON data to a file using a temporary file and atomic rename."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Use .json.tmp to match previous module conventions
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=indent, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except Exception as e:
        logger.error(f"Persistence: Failed atomic write to {path}: {e}")
        # We don't swallow completely, allow caller to handle if they want to
        raise

def safe_read_json(path: Path, default: Any = None) -> Any:
    """Reads JSON from a file, returning a default value if missing or corrupted."""
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Persistence: Failed to read {path} - {e}. Returning default.")
        return default
