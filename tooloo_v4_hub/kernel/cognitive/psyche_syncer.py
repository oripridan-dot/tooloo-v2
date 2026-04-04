# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_PSYCHE_SYNCER | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/cognitive/psyche_syncer.py
# WHEN: 2026-04-03T15:35:00.000000
# WHY: Rule 3/9: Unified Topography and Memory (Deep Retrieval)
# HOW: Semantic Chunking + Tier-Aware Indexing
# ==========================================================

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from tooloo_v4_hub.organs.memory_organ.memory_logic import get_memory_logic, TIER_LONG, TIER_MEDIUM
from tooloo_v4_hub.kernel.governance.living_map import get_living_map

logger = logging.getLogger("PsycheSyncer")

class PsycheSyncer:
    """
    Sovereign Context Syncer.
    Bridges the Living Map (Topography) and the Memory Organ (Engrams).
    """

    def __init__(self):
        self.living_map = get_living_map()
        self.memory = None # Lazy load

    async def _init_memory(self):
        if self.memory is None:
            self.memory = await get_memory_logic()

    async def sync_node(self, node_id: str):
        """Indexes the content of a single topography node into memory."""
        await self._init_memory()
        
        node = self.living_map.nodes.get(node_id)
        if not node:
            logger.warning(f"PsycheSyncer: Node {node_id} not found in Living Map.")
            return

        path = Path(node_id)
        if not path.exists() or not path.is_file():
            return

        try:
            content = path.read_text(errors="ignore")
            chunks = self._chunk_content(content)
            print(f"PsycheSyncer: Indexing {node_id} ({len(content)} chars) -> {len(chunks)} Chunks")
            
            # Rule 15: Garbage Collection (Clear old chunks first)
            prefix = f"file_{node_id.replace('/', '_')}_chunk_"
            await self.memory.clear_engrams_by_prefix(prefix)
            
            # Determine Tier based on node type
            tier = TIER_LONG if node["type"] in ["kernel", "cognitive"] else TIER_MEDIUM
            
            engrams_to_store = []
            for i, chunk in enumerate(chunks):
                engram_id = f"file_{node_id.replace('/', '_')}_chunk_{i}"
                payload = {
                    "type": "code_context",
                    "source": node_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "text": chunk,
                    "stamping": node.get("metadata", {})
                }
                engrams_to_store.append({"engram_id": engram_id, "data": payload})
            
            if engrams_to_store:
                await self.memory.store_engrams(engrams_to_store, layer=tier)
            
            logger.info(f"PsycheSyncer: {node_id} indexed into {tier} tier [{len(chunks)} Chunks].")
        except Exception as e:
            logger.error(f"PsycheSyncer: Fault indexing {node_id}: {e}")

    def _chunk_content(self, content: str, max_chunk_size: int = 1500) -> List[str]:
        """Performs semantic chunking based on double-newlines (Rule 7 logic)."""
        # Hard break on large blocks
        parts = content.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if len(current_chunk) + len(part) < max_chunk_size:
                current_chunk += part + "\n\n"
            else:
                if current_chunk: chunks.append(current_chunk.strip())
                current_chunk = part + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    async def sync_all(self):
        """Triggers a full system index pulse (Sovereign Context Sync)."""
        logger.info("PsycheSyncer: Initiating Full Sovereign Context Sync...")
        nodes = list(self.living_map.nodes.keys())
        for node_id in nodes:
            await self.sync_node(node_id)
        logger.info("PsycheSyncer: Full Hub Index Pulse COMPLETE.")

_psyche_syncer = None

def get_psyche_syncer() -> PsycheSyncer:
    global _psyche_syncer
    if _psyche_syncer is None:
        _psyche_syncer = PsycheSyncer()
    return _psyche_syncer
