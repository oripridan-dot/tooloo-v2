"""
engine/buddy_memory.py — Persistent cross-session memory for Buddy.

Buddy remembers previous conversations across server restarts.  Each finished
(or saved) session is compressed into a ``BuddyMemoryEntry`` — a compact
summary that can be surfaced as context in future turns without bloating the
LLM prompt.

Storage: ``psyche_bank/buddy_memory.json`` (newline-delimited JSON records,
         re-written atomically on every save).

Tribunal invariant: the raw session text is NEVER stored verbatim.  Only the
summary, key topics, emotional arc, and a brief last-message preview are
persisted.  This prevents any accidentally poisoned content from being
replayed into future LLM prompts unfiltered.

Thread safety: a single ``threading.Lock`` guards all reads and writes.

Usage::

    store = BuddyMemoryStore()

    # persist a finished ConversationSession
    store.save_session(session)

    # retrieve the 5 most recent entries
    recent = store.recent(limit=5)

    # find entries topically similar to a new user message
    relevant = store.find_relevant(text="debugging the auth flow", limit=3)
"""
from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.conversation import ConversationSession

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[1] / "psyche_bank" / "buddy_memory.json"
)

# Maximum number of entries to retain (rolling window – oldest pruned first)
_MAX_ENTRIES = 200

# Maximum length for the saved last-message preview
_PREVIEW_MAX = 120

# Maximum length for the generated one-line summary
_SUMMARY_MAX = 200


@dataclass
class BuddyMemoryEntry:
    """Compact summary of a finished conversation session."""

    session_id: str
    summary: str               # 1–2 sentence summary of what was worked on
    key_topics: list[str]      # up to 3 distinct intents from the session
    emotional_arc: list[str]   # non-neutral emotional states in order
    turn_count: int
    created_at: str            # ISO-8601 UTC
    last_turn_at: str          # ISO-8601 UTC
    last_message_preview: str  # first _PREVIEW_MAX chars of last user message

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BuddyMemoryEntry":
        return cls(
            session_id=d.get("session_id", ""),
            summary=d.get("summary", ""),
            key_topics=d.get("key_topics", []),
            emotional_arc=d.get("emotional_arc", []),
            turn_count=int(d.get("turn_count", 0)),
            created_at=d.get("created_at", ""),
            last_turn_at=d.get("last_turn_at", ""),
            last_message_preview=d.get("last_message_preview", ""),
        )


def _build_summary(session: "ConversationSession") -> str:
    """Create a short human-readable summary of a ConversationSession.

    Uses the session's intent history and last user messages to construct a
    deterministic, offline summary.  No LLM required.
    """
    user_turns = [t for t in session.turns if t.role == "user"]
    if not user_turns:
        return "Empty session."

    # ordered unique
    intents = list(dict.fromkeys(t.intent for t in user_turns))
    dominant = intents[0] if intents else "EXPLAIN"
    topic_phrases = [t.text[:60] for t in user_turns[:2]]
    joined = "; ".join(topic_phrases)

    summary = f"{dominant} session ({len(user_turns)} user turns): {joined}"
    return summary[:_SUMMARY_MAX]


def _build_key_topics(session: "ConversationSession") -> list[str]:
    """Extract up to 3 distinct intents from user turns, in order of appearance."""
    seen: list[str] = []
    for t in session.turns:
        if t.role == "user" and t.intent not in seen:
            seen.append(t.intent)
            if len(seen) == 3:
                break
    return seen


def _keyword_overlap(text: str, entry: "BuddyMemoryEntry") -> float:
    """Compute a simple keyword relevance score between a query and a memory entry.

    Normalised by total unique words across both.  Returns [0, 1].
    """
    def words(s: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", s.lower()))

    query_words = words(text)
    entry_words = (
        words(entry.summary)
        | words(entry.last_message_preview)
        | {w.lower() for w in entry.key_topics}
    )
    if not query_words or not entry_words:
        return 0.0
    intersection = len(query_words & entry_words)
    union = len(query_words | entry_words)
    return intersection / union if union else 0.0


class BuddyMemoryStore:
    """Thread-safe persistent store for conversation session summaries.

    Entries are stored in ``psyche_bank/buddy_memory.json`` as a JSON array.
    The file is re-written atomically on every save (write to a temp sibling,
    then rename) to prevent partial writes.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_PATH
        self._lock = threading.Lock()
        self._entries: list[BuddyMemoryEntry] = self._load()

    # ── Public API ─────────────────────────────────────────────────────────

    def save_session(self, session: "ConversationSession") -> BuddyMemoryEntry | None:
        """Summarise and persist a ConversationSession.

        Returns the created ``BuddyMemoryEntry``, or ``None`` if the session
        has fewer than 2 user turns (not worth saving).
        """
        user_turns = [t for t in session.turns if t.role == "user"]
        if len(user_turns) < 2:
            return None

        last_user = user_turns[-1]
        entry = BuddyMemoryEntry(
            session_id=session.session_id,
            summary=_build_summary(session),
            key_topics=_build_key_topics(session),
            emotional_arc=session.emotional_arc(),
            turn_count=len(session.turns),
            created_at=session.created_at,
            last_turn_at=last_user.ts,
            last_message_preview=last_user.text[:_PREVIEW_MAX],
        )
        self._upsert(entry)
        return entry

    def save_entry(self, entry: BuddyMemoryEntry) -> None:
        """Directly persist a pre-built ``BuddyMemoryEntry`` (for testing)."""
        self._upsert(entry)

    def recent(self, limit: int = 5) -> list[BuddyMemoryEntry]:
        """Return the *limit* most recently updated entries, newest first."""
        with self._lock:
            sorted_entries = sorted(
                self._entries,
                key=lambda e: e.last_turn_at,
                reverse=True,
            )
            return sorted_entries[:limit]

    def find_relevant(self, text: str, limit: int = 3) -> list[BuddyMemoryEntry]:
        """Return entries most topically similar to *text*, best first.

        Uses simple keyword-overlap scoring — no external dependencies, safe for
        offline use inside ``ThreadPoolExecutor`` (stateless call, Law 17).
        """
        with self._lock:
            if not self._entries:
                return []
            scored = [
                (e, _keyword_overlap(text, e)) for e in self._entries
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            # Only return entries with non-zero overlap
            return [e for e, score in scored[:limit] if score > 0.0]

    def recall_narrative(self, text: str, limit: int = 2) -> str:
        """Return a first-person narrative memory snippet for Buddy to use in context.

        Produces a conversational, in-character paragraph that Buddy can reference
        naturally (e.g. "Building on what we worked through before…").  Uses
        the same keyword-overlap scoring as ``find_relevant`` so only topically
        relevant past sessions are surfaced.

        Returns an empty string when no store is configured or no relevant
        sessions exist — callers should treat empty-string as "no prior context".
        """
        relevant = self.find_relevant(text, limit=limit)
        if not relevant:
            return ""
        parts: list[str] = []
        for e in relevant:
            topics = ", ".join(
                e.key_topics) if e.key_topics else "general topics"
            preview = e.last_message_preview[:80]
            arc_note = (
                f" (you seemed {e.emotional_arc[-1]})"
                if e.emotional_arc else ""
            )
            snippet = (
                f"We explored {topics} together{arc_note}. "
                f'You were working on: "{preview}".'
            )
            parts.append(snippet)
        return "Here's what I remember from before: " + " ".join(parts)

    def all_entries(self) -> list[BuddyMemoryEntry]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        """Remove all entries (does NOT delete the file)."""
        with self._lock:
            self._entries = []
            self._persist()

    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)

    # ── Internal ───────────────────────────────────────────────────────────

    def _upsert(self, entry: BuddyMemoryEntry) -> None:
        """Insert or update an entry, then persist. Called with lock NOT held."""
        with self._lock:
            # Replace existing entry with same session_id
            updated = False
            for i, existing in enumerate(self._entries):
                if existing.session_id == entry.session_id:
                    self._entries[i] = entry
                    updated = True
                    break
            if not updated:
                self._entries.append(entry)
            # Rolling window — drop oldest entries beyond cap
            if len(self._entries) > _MAX_ENTRIES:
                self._entries.sort(key=lambda e: e.last_turn_at)
                self._entries = self._entries[-_MAX_ENTRIES:]
            self._persist()

    def _load(self) -> list[BuddyMemoryEntry]:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            return [BuddyMemoryEntry.from_dict(d) for d in raw if isinstance(d, dict)]
        except (json.JSONDecodeError, TypeError):
            return []

    def _persist(self) -> None:
        """Atomic write: write to temp sibling then rename."""
        data = [e.to_dict() for e in self._entries]
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(
            data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)
