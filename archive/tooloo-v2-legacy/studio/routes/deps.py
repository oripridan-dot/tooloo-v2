"""
studio/routes/deps.py — Shared singletons and utilities for all route modules.

All singletons are imported from here (not created here) — they are
initialised lazily in api.py's _lifespan() or at module-load time.
Route modules import ``from studio.routes.deps import ...`` to access them.
"""
from __future__ import annotations

import asyncio
from typing import Any

# ── Re-export singletons from api.py ──────────────────────────────────────────
# These are set by api.py before routers are included, so they are always
# available when route handlers execute.  The module-level names below act as
# lazy references — actual values are injected by ``init_deps()``.

_broadcast_fn = None
_sse_queues: list[asyncio.Queue[str]] = []

# Singleton references (populated by init_deps)
router = None
graph = None
bank = None
tribunal = None
executor = None
sorter = None
scope_evaluator = None
refinement_loop = None
buddy_memory = None
conversation_engine = None
jit_booster = None
engram_generator = None
self_improvement_engine = None
bank_manager = None
sota_ingestion = None
mcp_manager = None
model_selector = None
refinement_supervisor = None
intent_discovery = None
validator_16d = None
async_fluid_executor = None
jit_designer = None
startup_time = ""


def init_deps(**kwargs: Any) -> None:
    """Inject singleton references from api.py.

    Called once during api.py module load so all route modules can
    access singletons without circular imports.
    """
    g = globals()
    for key, value in kwargs.items():
        if key in g:
            g[key] = value


def broadcast(event: dict[str, Any]) -> None:
    """Broadcast an SSE event to all connected clients."""
    if _broadcast_fn is not None:
        _broadcast_fn(event)
