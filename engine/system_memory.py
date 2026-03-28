# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.system_memory.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/system_memory.py — Tier 1 Hot Memory for the TooLoo System Daemon.

Just as Buddy saves user conversations into Hot Memory before vectorisation,
the autonomous TooLoo Daemon saves records of its self-improvement cycles
and architectural mandates into this System Memory layer.

Storage: `psyche_bank/system_memory.json` (newline-delimited JSON).

This allows the daemon to read what it *just did* in recent cycles to avoid
infinite loops, regression loops, or repeatedly applying failed patches.
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[1] / "psyche_bank" / "system_memory.json"
)

# Maximum system cycles to keep in Hot Memory before oldest are purged
_MAX_ENTRIES = 100


@dataclass
class SystemMemoryEntry:
    """A record of one completed daemon or self-improvement cycle."""

    cycle_id: str               # UUID or run_id of the daemon cycle
    domain: str                 # "self-improvement", "tribunal-sweep", etc.
    summary: str                # Human-readable summary of what was attempted
    modules_touched: list[str]  # e.g. ["engine/router.py", "engine/executor.py"]
    success: bool               # Did the cycle pass regression gates?
    composite_score_delta: float# +0.02, -0.01, etc.
    key_learnings: list[str]    # Extracted lessons or root causes from the cycle
    created_at: str             # ISO-8601 UTC timestamp
    git_sha: str                # State Checkpointing: Codebase reality anchor
    is_anti_pattern: bool       # Anti-Pattern Index: Flag for catastrophic failure / rejected mutation
    distilled: bool = False     # Promoted to Warm memory?

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SystemMemoryEntry":
        return cls(
            cycle_id=d.get("cycle_id", ""),
            domain=d.get("domain", "system"),
            summary=d.get("summary", ""),
            modules_touched=d.get("modules_touched", []),
            success=bool(d.get("success", False)),
            composite_score_delta=float(d.get("composite_score_delta", 0.0)),
            key_learnings=d.get("key_learnings", []),
            created_at=d.get("created_at", ""),
            git_sha=d.get("git_sha", "unknown"),
            is_anti_pattern=bool(d.get("is_anti_pattern", False)),
            distilled=bool(d.get("distilled", False)),
        )


class SystemMemoryStore:
    """Thread-safe persistent store for TooLoo's Hot Memory tier."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self._path = storage_path or _DEFAULT_PATH
        self._lock = threading.Lock()
        
        # Ensure directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    def _read_all(self) -> list[SystemMemoryEntry]:
        """Read all entries from disk safely."""
        entries: list[SystemMemoryEntry] = []
        try:
            raw = self._path.read_text(encoding="utf-8")
            for line in raw.splitlines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    entries.append(SystemMemoryEntry.from_dict(data))
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass
        # Order by created_at ascending
        entries.sort(key=lambda e: e.created_at)
        return entries

    def _write_all(self, entries: list[SystemMemoryEntry]) -> None:
        """Write records to disk, keeping only the most recent _MAX_ENTRIES."""
        keep = entries[-_MAX_ENTRIES:]
        lines = [json.dumps(e.to_dict()) for e in keep]
        self._path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def record_cycle(
        self,
        cycle_id: str,
        domain: str,
        summary: str,
        modules_touched: list[str],
        success: bool,
        composite_score_delta: float,
        key_learnings: list[str] | None = None,
        git_sha: str = "unknown",
        is_anti_pattern: bool = False,
    ) -> SystemMemoryEntry:
        """Record the outcome of a system action or training cycle."""
        entry = SystemMemoryEntry(
            cycle_id=cycle_id,
            domain=domain,
            summary=summary,
            modules_touched=modules_touched,
            success=success,
            composite_score_delta=composite_score_delta,
            key_learnings=key_learnings or [],
            created_at=datetime.now(UTC).isoformat(),
            git_sha=git_sha,
            is_anti_pattern=is_anti_pattern,
        )

        
        with self._lock:
            entries = self._read_all()
            # remove duplicate cycle_ids if they exist (should not, but safety first)
            entries = [e for e in entries if e.cycle_id != cycle_id]
            entries.append(entry)
            self._write_all(entries)
            
        return entry

    def recent(self, limit: int = 10, domain: str | None = None) -> list[SystemMemoryEntry]:
        """Return the most recent cycles, optionally filtered by domain."""
        with self._lock:
            entries = self._read_all()
            
        if domain:
            entries = [e for e in entries if e.domain == domain]
            
        # Return newest first
        return list(reversed(entries))[:limit]

    def mark_distilled(self, cycle_id: str) -> None:
        """Mark an entry as promoted to Warm Memory."""
        with self._lock:
            entries = self._read_all()
            changed = False
            for e in entries:
                if e.cycle_id == cycle_id and not e.distilled:
                    e.distilled = True
                    changed = True
            if changed:
                self._write_all(entries)

    def entry_count(self) -> int:
        with self._lock:
            return len(self._read_all())
