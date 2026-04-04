# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: repositories.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/spokes/repositories.py
# WHEN: 2026-04-03T16:08:23.390478+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import os
import asyncio
import aiosqlite
from datetime import datetime
from typing import Optional

from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'chat.db'))

class ChatRepository:
    """Async repository for persisting chat messages.

    Uses a local SQLite database (aiosqlite). The DB is created on first use.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self._initialized = False

    async def _ensure_db(self):
        if self._initialized:
            return
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            await db.commit()
        self._initialized = True

    async def store_message(self, message: SovereignMessage) -> None:
        """Persist a :class:`SovereignMessage`.

        The method is async; if called synchronously it will raise ``TypeError`` which
        the caller can fallback to a sync call.
        """
        await self._ensure_db()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messages (role, content, timestamp) VALUES (?, ?, ?)",
                (message.role, message.content, datetime.utcnow().isoformat()),
            )
            await db.commit()

    async def fetch_recent(self, limit: int = 50):
        """Return the most recent *limit* messages as list of dicts."""
        await self._ensure_db()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT role, content, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [
                {"role": r[0], "content": r[1], "timestamp": r[2]}
                for r in reversed(rows)
            ]
