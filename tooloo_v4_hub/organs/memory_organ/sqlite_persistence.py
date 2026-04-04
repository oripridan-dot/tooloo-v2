# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: SQLITE_PERSISTENCE.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/memory_organ/sqlite_persistence.py
# WHY: Rule 9/10 - Structured Long-Term History
# HOW: SQLite3 + Pydantic Serialization
# ==========================================================

import sqlite3
import json
import logging
from typing import List, Optional
from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage
from tooloo_v4_hub.shared.interfaces.chat_repository import IChatRepository

logger = logging.getLogger("ChatPersistence")

class ChatRepository(IChatRepository):
    """
    Dedicated Persistence for Sovereign Chat (Rule 9).
    Stores structured messages with full metadata and 6W stamps.
    """
    
    def __init__(self, db_path: str = None):
        import os
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = os.getenv("CHAT_DB_PATH", "")
            if not self.db_path:
                # Cloud Run: use /tmp (ephemeral filesystem)
                # Local: use the psyche_bank directory relative to this module
                if os.getenv("CLOUD_NATIVE_WORKSPACE") == "true" or os.getenv("K_SERVICE"):
                    self.db_path = "/tmp/sovereign_chat.db"
                else:
                    self.db_path = os.path.join(
                        os.path.dirname(__file__), "..", "..", "psyche_bank", "sovereign_chat.db"
                    )
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    speaker TEXT,
                    dynamics TEXT,
                    stamping TEXT,
                    manifestation TEXT
                )
            """)
            conn.commit()

    def store_message(self, message: SovereignMessage, session_id: str = "default"):
        """Saves a SovereignMessage to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO messages (session_id, role, content, speaker, dynamics, stamping, manifestation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    message.role,
                    message.content,
                    message.speaker,
                    json.dumps(message.dynamics.dict()) if message.dynamics else None,
                    json.dumps(message.stamping.dict()) if message.stamping else None,
                    json.dumps(message.manifestation) if message.manifestation else None
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Persistence Fault: {e}")
            raise RuntimeError(f"ChatRepository Failed to store message: {str(e)}")

    def get_history(self, session_id: str = "default", limit: int = 50) -> List[SovereignMessage]:
        """Retrieves structured chat history."""
        messages = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT role, content, speaker, dynamics, stamping, manifestation 
                    FROM messages 
                    WHERE session_id = ? 
                    ORDER BY id DESC LIMIT ?
                """, (session_id, limit))
                
                for row in cursor.fetchall():
                    role, content, speaker, dynamics, stamping, manifestation = row
                    messages.append(SovereignMessage(
                        role=role,
                        content=content,
                        speaker=speaker,
                        dynamics=json.loads(dynamics) if dynamics else None,
                        stamping=json.loads(stamping) if stamping else None,
                        manifestation=json.loads(manifestation) if manifestation else None
                    ))
        except Exception as e:
            logger.error(f"History Retrieval Fault: {e}")
            raise RuntimeError(f"ChatRepository Failed to get history: {str(e)}")
        
        return messages[::-1] # Return in chronological order
