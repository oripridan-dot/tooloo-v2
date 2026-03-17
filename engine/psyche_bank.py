"""
engine/psyche_bank.py — lightweight .cog.json rule store.

No external deps beyond stdlib + pydantic.

Rules are keyed by id and deduplicated on write. The default
store path is <repo_root>/psyche_bank/forbidden_patterns.cog.json,
but any Path can be supplied for testing.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_BANK = (
    Path(__file__).resolve().parents[1] / "psyche_bank" / "forbidden_patterns.cog.json"
)


@dataclass
class CogRule:
    id: str
    description: str
    pattern: str
    enforcement: str  # "block" | "warn"
    category: str     # "security" | "quality" | "style"
    source: str       # "tribunal" | "manual" | "vast_learn"


@dataclass
class CogStore:
    version: str = "1.0.0"
    rules: list[CogRule] = field(default_factory=list)


class PsycheBank:
    """Thread-safe reader/writer for .cog.json rule files."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_BANK
        self._lock = threading.Lock()
        self._store: CogStore = self._load()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def capture(self, rule: CogRule) -> bool:
        """Add rule if not already present (dedup by id). Returns True if added."""
        with self._lock:
            ids = {r.id for r in self._store.rules}
            if rule.id in ids:
                return False
            self._store.rules.append(rule)
            self._persist()
            return True

    def all_rules(self) -> list[CogRule]:
        with self._lock:
            return list(self._store.rules)

    def rules_by_category(self, category: str) -> list[CogRule]:
        with self._lock:
            return [r for r in self._store.rules if r.category == category]

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "version": self._store.version,
                "rules": [asdict(r) for r in self._store.rules],
            }

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _load(self) -> CogStore:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            return CogStore()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            rules = [CogRule(**r) for r in raw.get("rules", [])]
            return CogStore(version=raw.get("version", "1.0.0"), rules=rules)
        except (json.JSONDecodeError, TypeError, KeyError):
            return CogStore()

    def _persist(self) -> None:
        blob = {
            "version": self._store.version,
            "rules": [asdict(r) for r in self._store.rules],
        }
        self._path.write_text(
            json.dumps(blob, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
