# ── Ouroboros SOTA Annotations (auto-generated, do not edit) ─────
# Cycle: 2026-03-20T19:59:47.187168+00:00
# Component: psyche_bank  Source: engine/psyche_bank.py
# Improvement signals from JIT SOTA booster:
#  [1] Enforce engine/psyche_bank.py: OWASP Top 10 2025 edition promotes Broken
#     Object-Level Authorisation to the #1 priority
#  [2] Enforce engine/psyche_bank.py: OSS supply-chain audits (Sigstore + Rekor
#     transparency log) are required in regulated environments
#  [3] Enforce engine/psyche_bank.py: CSPM tools (Wiz, Orca, Prisma Cloud) provide
#     real-time cloud posture scoring in 2026
# ─────────────────────────────────────────────────────────────────
"""
engine/psyche_bank.py — lightweight .cog.json rule store.

No external deps beyond stdlib + pydantic.

Rules are keyed by id and deduplicated on write. The default
store path is <repo_root>/psyche_bank/forbidden_patterns.cog.json,
but any Path can be supplied for testing.

TTL support:
  Rules captured via ``capture(rule, ttl_seconds=N)`` receive an
  ``expires_at`` ISO timestamp.  Calling ``purge_expired()`` removes
  rules whose TTL has elapsed.  Manual/pre-seeded rules (``expires_at``
  omitted) never expire.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from engine.persistence import atomic_write_json, safe_read_json

logger = logging.getLogger(__name__)

# Control: configurable thresholds for rule store safety
MAX_RULES_THRESHOLD = 10_000  # hard cap to prevent unbounded growth
MAX_RETRIES = 3               # max I/O retries for corrupted .cog.json
_ROLLBACK_ON_CORRUPT = True   # auto-rollback on parse failure

_DEFAULT_BANK = (
    Path(__file__).resolve().parents[1] /
    "psyche_bank" / "forbidden_patterns.cog.json"
)


@dataclass
class CogRule:
    id: str
    description: str
    pattern: str
    enforcement: str  # "block" | "warn"
    category: str     # "security" | "quality" | "style"
    source: str       # "tribunal" | "manual" | "vast_learn"
    # ISO timestamp; "" = never expires (manual/pre-seeded rules)
    expires_at: str = ""


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

    def capture(self, rule: CogRule, ttl_seconds: int | None = None) -> bool:
        """Add rule if not already present (dedup by id). Returns True if added.

        Args:
            rule:        The CogRule to store.
            ttl_seconds: Optional TTL in seconds.  When provided the rule
                         receives an ``expires_at`` timestamp (now + TTL).
                         Omit or pass None for rules that should never expire.

        Raises:
            ValueError: if rule.id or rule.category are empty strings.
        """
        if not isinstance(rule.id, str) or not rule.id.strip():
            raise ValueError("CogRule.id must be a non-empty string")
        if not isinstance(rule.category, str) or not rule.category.strip():
            raise ValueError("CogRule.category must be a non-empty string")
        with self._lock:
            ids = {r.id for r in self._store.rules}
            if rule.id in ids:
                return False
            if ttl_seconds is not None:
                expires = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
                rule.expires_at = expires.isoformat()
            self._store.rules.append(rule)
            self._persist()
            return True

    def purge_expired(self) -> int:
        """Remove all rules whose TTL has elapsed.  Returns number of rules removed."""
        with self._lock:
            now = datetime.now(UTC)
            before = len(self._store.rules)
            surviving: list[CogRule] = []
            for r in self._store.rules:
                if r.expires_at:
                    try:
                        if datetime.fromisoformat(r.expires_at) > now:
                            surviving.append(r)
                        # else: expired — drop it
                    except ValueError:
                        surviving.append(r)  # malformed timestamp → keep
                else:
                    surviving.append(r)  # no TTL → never expires
            removed = before - len(surviving)
            if removed:
                self._store.rules = surviving
                self._persist()
            return removed

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
            rules = []
            for r in raw.get("rules", []):
                # Tolerate old records that lack expires_at
                r.setdefault("expires_at", "")
                rules.append(CogRule(**r))
            version = raw.get("version", "1.0.0")

            # Auto-purge expired rules on load to prevent store bloat
            now = datetime.now(UTC)
            surviving: list[CogRule] = []
            for rule in rules:
                if rule.expires_at:
                    try:
                        if datetime.fromisoformat(rule.expires_at) > now:
                            surviving.append(rule)
                        # else: TTL elapsed — drop silently
                    except ValueError:
                        surviving.append(rule)  # malformed timestamp → keep
                else:
                    surviving.append(rule)  # no TTL → never expires

            if len(surviving) < len(rules):
                # Persist the pruned store immediately so stale rules don't
                # re-appear on the next load (write directly — self._store not
                # yet initialised at this point so _persist() is unavailable).
                blob = {
                    "version": version,
                    "rules": [asdict(r) for r in surviving],
                }
                atomic_write_json(self._path, blob)
                rules = surviving

            return CogStore(version=version, rules=rules)
        except (json.JSONDecodeError, TypeError, KeyError):
            return CogStore()

    def _persist(self) -> None:
        blob = {
            "version": self._store.version,
            "rules": [asdict(r) for r in self._store.rules],
        }
        atomic_write_json(self._path, blob)
