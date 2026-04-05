"""
engine/knowledge_banks/base.py — Abstract base class for all TooLoo knowledge banks.

Every bank stores KnowledgeEntry records organised by domain.
Thread-safe reads and writes. Persists to a .cog.json sidecar file.

Knowledge tiers:
  "foundational" — timeless principles (Gestalt, SOLID, transformer basics)
  "current"      — 2024-2025 best practices, stable and widely adopted
  "sota_2026"    — leading-edge as of March 2026, may evolve

Relevance weight: 0.0–1.0. Higher = higher priority in query results.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from engine.persistence import atomic_write_json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class KnowledgeEntry:
    """Atomic unit of SOTA knowledge in a bank."""

    id: str
    title: str
    body: str               # 1-3 sentence dense signal
    domain: str             # sub-domain within a bank
    tags: list[str]
    relevance_weight: float = 0.80   # 0.0–1.0
    source: str = "seeded"           # "seeded" | "web" | "derived"
    last_verified: str = "2026-03"   # YYYY-MM
    sota_level: str = "current"      # "foundational" | "current" | "sota_2026"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def signal(self) -> str:
        """Short signal string suitable for JIT injection or Buddy context."""
        return f"[{self.domain}] {self.title}: {self.body}"


@dataclass
class BankStore:
    """On-disk serialisation envelope for a knowledge bank."""

    bank_id: str
    version: str = "1.0.0"
    entries: list[KnowledgeEntry] = field(default_factory=list)


class KnowledgeBank(ABC):
    """
    Thread-safe, persistent knowledge bank.

    Subclasses must implement:
      bank_id   — unique slug (e.g. "design")
      bank_name — human-readable name
      domains   — list of sub-domain strings
      _seed()   — populate initial curated knowledge
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._store: BankStore = self._load()
        if not self._store.entries:
            self._seed()
            self._persist()

    # ── Subclass contract ──────────────────────────────────────────────────────

    @property
    @abstractmethod
    def bank_id(self) -> str: ...

    @property
    @abstractmethod
    def bank_name(self) -> str: ...

    @property
    @abstractmethod
    def domains(self) -> list[str]: ...

    @abstractmethod
    def _seed(self) -> None:
        """Populate self._store.entries with foundational SOTA entries."""
        ...

    # ── Public API ─────────────────────────────────────────────────────────────

    def query(self, topic: str, context: str = "", n: int = 5) -> list[KnowledgeEntry]:
        """Return the top-N most relevant entries for the given topic/context.

        Ranking: tag/title/domain keyword overlap (TF-style) × relevance_weight.
        """
        tokens = set(re.findall(r"\w+", (topic + " " + context).lower()))
        with self._lock:
            scored: list[tuple[float, KnowledgeEntry]] = []
            for e in self._store.entries:
                entry_tokens = set(
                    re.findall(r"\w+", (e.title + " " + e.domain +
                               " " + " ".join(e.tags)).lower())
                )
                overlap = len(tokens & entry_tokens) / max(len(tokens), 1)
                score = overlap * e.relevance_weight
                scored.append((score, e))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [e for _, e in scored[:n] if scored[0][0] > 0] or [
                e for _, e in scored[:n]
            ]

    def get_signals(self, domain: str = "", n: int = 5) -> list[str]:
        """Return top-N signal strings, optionally filtered by domain."""
        with self._lock:
            entries = (
                [e for e in self._store.entries if e.domain == domain]
                if domain
                else list(self._store.entries)
            )
            entries.sort(key=lambda e: e.relevance_weight, reverse=True)
            return [e.signal() for e in entries[:n]]

    def store(self, entry: KnowledgeEntry) -> bool:
        """Add an entry (dedup by id). Returns True if added."""
        with self._lock:
            ids = {e.id for e in self._store.entries}
            if entry.id in ids:
                return False
            self._store.entries.append(entry)
            self._persist()
            return True

    def all_entries(self) -> list[KnowledgeEntry]:
        with self._lock:
            return list(self._store.entries)

    def domain_summary(self) -> dict[str, int]:
        """Count entries per domain."""
        with self._lock:
            counts: dict[str, int] = {}
            for e in self._store.entries:
                counts[e.domain] = counts.get(e.domain, 0) + 1
            return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "bank_id": self.bank_id,
            "bank_name": self.bank_name,
            "domains": self.domains,
            "entry_count": len(self._store.entries),
            "domain_summary": self.domain_summary(),
            "version": self._store.version,
        }

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _load(self) -> BankStore:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                entries = [KnowledgeEntry(**e) for e in raw.get("entries", [])]
                return BankStore(
                    bank_id=raw.get("bank_id", self.bank_id),
                    version=raw.get("version", "1.0.0"),
                    entries=entries,
                )
            except Exception:
                pass
        return BankStore(bank_id=self.bank_id)

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "bank_id": self._store.bank_id,
            "version": self._store.version,
            "entries": [e.to_dict() for e in self._store.entries],
        }
        atomic_write_json(self._path, payload)

    @staticmethod
    def _make_id(prefix: str, title: str) -> str:
        slug = re.sub(r"\W+", "_", title.lower())[:40]
        return f"{prefix}_{slug}"
