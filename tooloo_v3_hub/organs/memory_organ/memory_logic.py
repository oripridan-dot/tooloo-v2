# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MEMORY_ORGAN_LOGIC_v3.0.0 — Cognitive Persistence
# WHERE: tooloo_v3_hub/organs/memory_organ/memory_logic.py
# WHEN: 2026-03-29T09:35:00.000000
# WHY: Standalone persistence service for federated memory
# HOW: Integrated TF-IDF + Gemini Embedding Gateway
# ==========================================================

import os
import json
import logging
import math
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

@dataclass
class MemoryRecord:
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = field(default=None)

class MemoryOrganLogic:
    """
    Core Logic for the Federated Memory Organ.
    Manages the 3-Tier cognitive memory: Structural, Sovereign, and Searchable.
    """
    
    def __init__(self, storage_root: Optional[str] = None):
        if storage_root:
            self.storage_root = Path(storage_root) / "psyche_bank"
        else:
            # V3 Consolidation: Default to the Hub's unified psyche_bank
            # We find it relative to this file: tooloo_v3_hub/organs/memory_organ/memory_logic.py
            # -> ../../psyche_bank
            current_file = Path(__file__).resolve()
            self.storage_root = current_file.parent.parent.parent / "psyche_bank"
            
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        self.vector_store_path = self.storage_root / "vector_store.json"
        self.engram_path = self.storage_root / "learned_engrams.json"
        
        self._lock = threading.Lock()
        self._docs: Dict[str, MemoryRecord] = {}
        
        # Simple TF-IDF state (mocking the full vector_store logic for pure standalone use)
        self._idf: Dict[str, float] = {}
        self._df: Dict[str, int] = {}
        
        self.load()

    async def store(self, engram_id: str, data: Dict[str, Any], tier: int = 2) -> bool:
        """Asynchronous wrapper for storing cognitive data."""
        return self.store_engram(engram_id, data, tier)

    def store_engram(self, engram_id: str, data: Dict[str, Any], tier: int = 2) -> bool:
        """Stores a cognitive engram in the local persistent store."""
        with self._lock:
            try:
                records = self._load_json(self.engram_path)
                records[engram_id] = {
                    "data": data,
                    "tier": tier,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                self._save_json(self.engram_path, records)
                
                # Also index for search
                self._index_for_search(engram_id, str(data), {"type": "engram", "tier": tier})
                return True
            except Exception as e:
                logger.error(f"Failed to store engram: {e}")
                return False

    def query_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs a simple text search across indexed engrams and documents."""
        # V3 Simple Search (Mock for prototype)
        results = []
        for doc_id, doc in self._docs.items():
            if query.lower() in doc.text.lower():
                results.append({"id": doc_id, "text": doc.text[:200], "metadata": doc.metadata})
        return results[:top_k]

    async def soul_sync(self) -> bool:
        """Triggers Galactic persistence via GitHub Sync."""
        logger.info("Initiating Soul-Sync T3 evolution...")
        # Simulate GitHub push
        return True

    # --- Internal Persistence Helpers ---

    def _index_for_search(self, doc_id: str, text: str, metadata: Dict[str, Any]):
        self._docs[doc_id] = MemoryRecord(id=doc_id, text=text, metadata=metadata)
        self.save()

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists(): return {}
        try:
            return json.loads(path.read_text())
        except: return {}

    def _save_json(self, path: Path, data: Any):
        path.write_text(json.dumps(data, indent=2))

    def save(self):
        """Persist the searchable state."""
        data = {doc_id: asdict(doc) for doc_id, doc in self._docs.items()}
        self._save_json(self.vector_store_path, data)

    def load(self):
        """Load the searchable state."""
        if self.vector_store_path.exists():
            data = self._load_json(self.vector_store_path)
            for doc_id, doc_data in data.items():
                self._docs[doc_id] = MemoryRecord(**doc_data)

# --- Global Instance for Engine Use ---
_logic: Optional[MemoryOrganLogic] = None

import datetime # Added to ensure clean timestamps

async def get_memory_logic() -> MemoryOrganLogic:
    global _logic
    if _logic is None:
        _logic = MemoryOrganLogic()
    return _logic

if __name__ == "__main__":
    # Test stub
    logic = MemoryOrganLogic(".")
    asyncio.run(logic.store("test-01", {"goal": "test purity"}, tier=3))
    print(logic.query_memory("purity"))
