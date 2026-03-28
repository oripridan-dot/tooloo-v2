# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining kv_store.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.938086
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import json
import threading
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_KV_PATH = (
    Path(__file__).resolve().parents[1] / "psyche_bank" / "cognitive_payloads.json"
)

class KVStore:
    """
    Absolute Truth storage for heavy cognitive payloads.
    Thread-safe and disk-persistent.
    """
    def __init__(self, path: Path = _DEFAULT_KV_PATH):
        self._path = path
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = self._load()

    def set(self, hash_id: str, payload: Dict[str, Any]) -> None:
        """Store a payload indexed by its deterministic hash."""
        with self._lock:
            self._data[hash_id] = payload
            self._persist()
            logger.debug(f"KVStore: Saved payload for hash {hash_id}")

    def get(self, hash_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a payload by its hash."""
        with self._lock:
            return self._data.get(hash_id)

    def _load(self) -> Dict[str, Any]:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
            return json.loads(raw)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"KVStore: Failed to load from {self._path}: {e}")
            return {}

    def _persist(self) -> None:
        """Atomic write to disk."""
        try:
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)
        except OSError as e:
            logger.error(f"KVStore: Failed to persist to {self._path}: {e}")

# Global instance for system-wide use
_kv_store_instance = None
def get_kv_store() -> KVStore:
    global _kv_store_instance
    if _kv_store_instance is None:
        _kv_store_instance = KVStore()
    return _kv_store_instance
