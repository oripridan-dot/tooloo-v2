# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining bus.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.926511
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/bus.py — The Unified Notification Bus (The Pulse).

Pub/Sub event router that handles both internal agent-to-agent signalling
and user-facing alerts streamed via SSE.  Any component can publish an event;
any subscriber callback processes it asynchronously.

Event levels
------------
INFO      — Routine system chatter (background indexing, cache warm, etc.)
INSIGHT   — A non-obvious discovery the user or an agent might act on.
WARNING   — A degraded condition that does not stop execution
            (e.g., Vertex rate-limit approaching, confidence drop).
CRITICAL  — A hard safety or security violation that requires attention
            (e.g., OWASP Tribunal poison detected).

Confirmation Protocol
---------------------
Events with ``requires_confirmation=True`` are held in ``_pending`` until
``confirm(event_id)`` or ``dismiss(event_id)`` is called.  The bus broadcasts
a ``bus_confirm_request`` SSE event so the UI can surface a blocking dialog.
Once acknowledged the bus publishes a ``bus_confirm_response`` event and
invokes any ``on_confirm`` callback registered at publish time.

Usage
-----
    from engine.bus import get_bus, BusEvent

    # Publish
    get_bus().publish(BusEvent(
        level="CRITICAL",
        source="tribunal",
        message="OWASP A03 injection pattern detected in generated code",
        payload={"violations": ["SQL Injection"], "slug": "api-handler"},
        requires_confirmation=True,
    ))

    # Subscribe (permanent — survives multiple events)
    get_bus().subscribe("CRITICAL", my_remediation_callback)

    # Confirm a held event (from /v2/alerts/confirm/<id>)
    get_bus().confirm(event_id, accepted=True)
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── DTOs ──────────────────────────────────────────────────────────────────────

BUS_LEVELS = {"INFO", "INSIGHT", "WARNING", "CRITICAL"}


@dataclass
class BusEvent:
    """A single event on the Notification Bus."""

    level: str                            # INFO | INSIGHT | WARNING | CRITICAL
    # component that published (e.g. "tribunal")
    source: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    # If True, the bus broadcasts a confirmation request to SSE before proceeding
    requires_confirmation: bool = False
    # Optional callback invoked once the user confirms — receives accepted: bool
    on_confirm: Callable[[bool], None] | None = field(default=None, repr=False)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "level": self.level,
            "source": self.source,
            "message": self.message,
            "payload": self.payload,
            "requires_confirmation": self.requires_confirmation,
            "ts": self.ts,
        }


@dataclass
class ConfirmationResult:
    event_id: str
    accepted: bool
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "accepted": self.accepted,
            "ts": self.ts,
        }


# ── Bus ───────────────────────────────────────────────────────────────────────

_DEFAULT_HISTORY_CAP = 200   # rolling window of recent events


class NotificationBus:
    """
    Central Pub/Sub bus.

    Subscribers are keyed by level or the magic string ``"ALL"`` (matches every
    level).  Callbacks are synchronous and executed in the publishing thread for
    low overhead; if a subscriber raises it is logged and skipped.

    Thread-safe: all pubsub state is protected by ``_lock``.
    """

    def __init__(self, history_cap: int = _DEFAULT_HISTORY_CAP) -> None:
        self._lock = threading.Lock()
        # level → list[callback]
        self._subscribers: dict[str, list[Callable[[BusEvent], None]]] = {
            level: [] for level in BUS_LEVELS
        }
        self._subscribers["ALL"] = []
        # Confirmed events pending acknowledgement
        self._pending: dict[str, BusEvent] = {}
        # Rolling history
        self._history: deque[BusEvent] = deque(maxlen=history_cap)
        # SSE broadcast function — injected by api.py at startup
        self._broadcast_fn: Callable[[dict[str, Any]], None] | None = None

    # ── Registration ─────────────────────────────────────────────────────────

    def register_broadcast(self, fn: Callable[[dict[str, Any]], None]) -> None:
        """Connect the SSE broadcaster so events reach the UI."""
        self._broadcast_fn = fn
        logger.debug("NotificationBus: SSE broadcaster registered")

    def subscribe(
        self,
        level: str,
        callback: Callable[[BusEvent], None],
    ) -> None:
        """Register a subscriber for a specific level or "ALL".

        ``callback(event: BusEvent)`` is called synchronously in the publish
        thread.  Keep callbacks fast; defer heavy work to a background thread.
        """
        key = level.upper()
        with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            if callback not in self._subscribers[key]:
                self._subscribers[key].append(callback)

    def unsubscribe(
        self,
        level: str,
        callback: Callable[[BusEvent], None],
    ) -> None:
        key = level.upper()
        with self._lock:
            listeners = self._subscribers.get(key, [])
            try:
                listeners.remove(callback)
            except ValueError:
                pass

    # ── Publishing ───────────────────────────────────────────────────────────

    def publish(self, event: BusEvent) -> None:
        """Publish an event to all matching subscribers and the SSE layer.

        If ``event.requires_confirmation`` is True, the event is held in
        ``_pending`` and a ``bus_confirm_request`` SSE event is emitted.
        The normal subscriber callbacks are still fired immediately so that
        internal agents react without waiting for the human.
        """
        if event.level not in BUS_LEVELS:
            logger.warning(
                "NotificationBus: unknown level %r — defaulting to INFO", event.level)
            event.level = "INFO"

        with self._lock:
            self._history.append(event)
            subscribers = (
                list(self._subscribers.get(event.level, []))
                + list(self._subscribers.get("ALL", []))
            )
            if event.requires_confirmation:
                self._pending[event.event_id] = event

        # Fire subscribers outside the lock
        for cb in subscribers:
            try:
                cb(event)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error(
                    "NotificationBus: subscriber %r raised: %s", cb, exc, exc_info=True
                )

        # SSE broadcast
        if self._broadcast_fn:
            sse_type = (
                "bus_confirm_request" if event.requires_confirmation else "bus_event"
            )
            try:
                self._broadcast_fn({
                    "type": sse_type,
                    **event.to_dict(),
                })
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("NotificationBus: broadcast error: %s", exc)

    # ── Confirmation Protocol ─────────────────────────────────────────────────

    def confirm(self, event_id: str, accepted: bool = True) -> ConfirmationResult | None:
        """Acknowledge a pending confirmation event.

        Invokes ``event.on_confirm(accepted)`` if present, then broadcasts a
        ``bus_confirm_response`` SSE event.  Returns None if the event_id is
        not in the pending queue.
        """
        with self._lock:
            event = self._pending.pop(event_id, None)
        if event is None:
            return None

        result = ConfirmationResult(event_id=event_id, accepted=accepted)

        if event.on_confirm:
            try:
                event.on_confirm(accepted)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error(
                    "NotificationBus: on_confirm callback raised: %s", exc)

        if self._broadcast_fn:
            try:
                self._broadcast_fn({
                    "type": "bus_confirm_response",
                    **result.to_dict(),
                    "original_message": event.message,
                    "level": event.level,
                    "source": event.source,
                })
            except Exception:  # pylint: disable=broad-except
                pass

        return result

    def dismiss(self, event_id: str) -> bool:
        """Remove a pending confirmation without invoking on_confirm."""
        with self._lock:
            removed = self._pending.pop(event_id, None)
        return removed is not None

    # ── Introspection ─────────────────────────────────────────────────────────

    def pending(self) -> list[BusEvent]:
        """Return all events awaiting user confirmation."""
        with self._lock:
            return list(self._pending.values())

    def history(
        self,
        level: str | None = None,
        limit: int = 50,
    ) -> list[BusEvent]:
        """Return recent event history, optionally filtered by level."""
        with self._lock:
            events = list(self._history)
        if level:
            events = [e for e in events if e.level == level.upper()]
        return events[-limit:]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            counts: dict[str, int] = {lvl: 0 for lvl in BUS_LEVELS}
            for e in self._history:
                counts[e.level] = counts.get(e.level, 0) + 1
            return {
                "total": len(self._history),
                "pending_confirmations": len(self._pending),
                "by_level": counts,
                "subscribers": {
                    k: len(v) for k, v in self._subscribers.items()
                },
            }


# ── Singleton ────────────────────────────────────────────────────────────────

_bus_instance: NotificationBus | None = None
_bus_lock = threading.Lock()


def get_bus() -> NotificationBus:
    """Return the process-level NotificationBus singleton."""
    global _bus_instance
    if _bus_instance is None:
        with _bus_lock:
            if _bus_instance is None:
                _bus_instance = NotificationBus()
    return _bus_instance
