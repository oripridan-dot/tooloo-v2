# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: memory_indexer.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/memory_organ/memory_indexer.py
# WHY: Rule 1, 10 - Long-term Orientation and Self-Indexing (Claude-Style)
# HOW: Periodic scans and updates to root-level MEMORY.md file.
# PURITY: 1.00
# ==========================================================

import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger("MemoryIndexer")

class MemoryIndexer:
    """
    Sovereign Memory Indexer.
    Maintains a human-readable and model-consumable functional map of the codebase.
    """
    
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.index_file = os.path.join(workspace_root, "MEMORY.md")

    def initialize_index(self):
        """Creates the shell for MEMORY.md if it doesn't exist."""
        if not os.path.exists(self.index_file):
            logger.info("MemoryIndexer: Initializing root-level MEMORY.md")
            with open(self.index_file, "w") as f:
                f.write("# Sovereign Project Memory Index\n\n")
                f.write("> [!NOTE]\n> This file is maintained automatically for agentic orientation.\n\n")
                f.write("## 🏗️ Functional Architecture\n- [ ] Main Hub (`tooloo_v4_hub/`)\n- [ ] Portal UX (`portal/`)\n")

    async def update_index(self, changes: List[Dict[str, Any]]):
        """Updates the MEMORY.md based on recent missions and architectural shifts."""
        self.initialize_index()
        
        with open(self.index_file, "a") as f:
            for change in changes:
                timestamp = change.get("timestamp", "N/A")
                summary = change.get("summary", "New engram added.")
                f.write(f"\n### Update: {timestamp}\n- {summary}\n")
        
        logger.info(f"MemoryIndexer: Appended {len(changes)} updates to MEMORY.md")

_indexer = None

def get_memory_indexer(workspace_root: str) -> MemoryIndexer:
    global _indexer
    if _indexer is None:
        _indexer = MemoryIndexer(workspace_root)
    return _indexer
