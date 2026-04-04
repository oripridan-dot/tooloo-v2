# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_MEMORY_LOGIC.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/organs/memory_organ/memory_logic.py
# WHEN: 2026-04-01T16:35:57.988993+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

# WHAT: MEMORY_LOGIC.PY | Version: 2.2.0
# WHERE: tooloo_v4_hub/organs/memory_organ/memory_logic.py
# WHY: Rule 3/9: Native AI Leveraging of Long-Term Foundations
# HOW: Positional TF-IDF + Tier Bias (Architectural Anchoring)

import json
import logging
import os
import datetime
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger("MemoryOrganLogic")

TIER_FAST = "fast"
TIER_MEDIUM = "medium"
TIER_LONG = "long"

# Foundational Keywords that trigger a LONG-tier bias
ARCHITECTURAL_ANCHORS = ["rule", "constitution", "sovereign", "purity", "identity", "principle", "sota"]

@dataclass
class MemoryRecord:
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tier: str = TIER_MEDIUM
    embedding: Optional[List[float]] = None

class MemoryOrganLogic:
    """
    Sovereign Memory Logic (Rule 9).
    Improved V2.2.0: Added Tier Bias for Foundational Architectural continuity.
    """
    
    def __init__(self, psyche_bank_root: str = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/tooloo_v4_hub/psyche_bank"):
        self.root = Path(psyche_bank_root)
        self.paths = {
            TIER_FAST: self.root / "fast_memory.json",
            TIER_MEDIUM: self.root / "medium_memory.json",
            TIER_LONG: self.root / "long_memory.json"
        }
        self.vector_store_path = self.root / "vector_store.json"
        self._docs: Dict[str, MemoryRecord] = {}
        self._load_vector_store()

    def _load_vector_store(self):
        if self.vector_store_path.exists():
            try:
                with open(self.vector_store_path, 'r') as f:
                    data = json.load(f)
                    for eid, entry in data.items():
                        self._docs[eid] = MemoryRecord(
                            id=eid,
                            text="",
                            metadata=entry.get("metadata", {}),
                            tier=entry.get("tier", TIER_MEDIUM),
                            embedding=entry.get("vector")
                        )
                logger.info(f"Memory: Vector Store synchronized [{len(self._docs)} Nodes].")
            except Exception as e:
                logger.error(f"Failed to load vector store: {e}")

    def _save_vector_store(self):
        data = {
            eid: {
                "vector": doc.embedding,
                "tier": doc.tier,
                "metadata": doc.metadata
            } for eid, doc in self._docs.items()
        }
        with open(self.vector_store_path, 'w') as f:
            json.dump(data, f)

    def _load_json(self, path: Path) -> Dict:
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    def _save_json(self, path: Path, data: Dict):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _generate_heuristic_embedding(self, text: str) -> List[float]:
        """Rule 11: High-fidelity positional vectorization."""
        tokens = str(text).lower().split()
        vector = [0.0] * 64
        for i, token in enumerate(tokens):
            idx = hash(token) % 64
            # Improvement: Positional weighting and Anchor boosting
            weight = 1.0 / (1.0 + (i * 0.05))
            if token in ARCHITECTURAL_ANCHORS:
                weight *= 3.0 # Rule 3: Boost foundational truths
            
            vector[idx] += weight
        return vector

    async def store(self, engram_id: str, data: Dict[str, Any], layer: str = TIER_MEDIUM) -> Dict[str, Any]:
        """Wrapper for store_engram to maintain Hub Orchestrator compatibility."""
        return await self.store_engram(engram_id, data, layer)

    async def store_prediction(self, goal: str, context: Dict[str, Any], prediction: Dict[str, Any]) -> str:
        """Rule 16: Specialized storage for mission predictions."""
        p_id = f"pred_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(goal) % 10000}"
        payload = {
            "type": "prediction",
            "goal": goal,
            "context": context,
            "prediction": prediction,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        await self.store_engram(p_id, payload, layer=TIER_MEDIUM)
        return p_id

    async def store_outcome(self, p_id: str, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Rule 16: Specialized storage for mission outcomes (closes the loop)."""
        o_id = f"out_{p_id[5:]}"
        payload = {
            "type": "outcome",
            "p_id": p_id,
            "outcome": outcome,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        return await self.store_engram(o_id, payload, layer=TIER_MEDIUM)

    async def soul_sync(self):
        """Rule 12: Force-synchronization of all memory tiers to persistent storage."""
        logger.info("Memory: Initiating Soul Sync (Physical Preservation Pulse)...")
        # In this implementation, _save_json is already called per store, 
        # but we can ensure vector store consistency here.
        await asyncio.to_thread(self._save_vector_store)
        return {"status": "synchronized"}

    async def store_engram(self, engram_id: str, data: Dict[str, Any], layer: str = TIER_MEDIUM) -> Dict[str, Any]:
        layer = layer.lower()
        if layer not in self.paths:
            layer = TIER_MEDIUM
        return await asyncio.to_thread(self._sync_store, engram_id, data, layer)

    def _sync_store(self, engram_id: str, data: Dict[str, Any], layer: str):
        try:
            records = self._load_json(self.paths[layer])
            # Rule 10: 6W Stamping
            stamp = data.get("stamp")
            if not stamp:
                try:
                    from tooloo_v4_hub.kernel.governance.stamping import SixWProtocol
                    protocol = SixWProtocol(
                        who="Sovereign-Hub-Logic",
                        what=f"MEMORY_MANIFEST: {layer.upper()}",
                        where="memory_logic.py",
                        why="Rule 9/10 Sovereign Persistence",
                        how="Heuristic Layering"
                    )
                    stamp = json.loads(protocol.model_dump_json())
                except:
                    stamp = {"who": "Hub", "what": "Internal_Store", "when": datetime.datetime.now().isoformat()}
            
            records[engram_id] = {
                "data": data,
                "tier": layer,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "stamp": stamp
            }
            self._save_json(self.paths[layer], records)
            
            # Indexing
            index_text = data.get("full_md") or data.get("text") or str(data)
            embedding = self._generate_heuristic_embedding(index_text)
            self._docs[engram_id] = MemoryRecord(
                id=engram_id,
                text="",
                metadata={"type": data.get("type", "engram"), "tier": layer},
                tier=layer,
                embedding=embedding
            )
            self._save_vector_store()
            return {"status": "success", "engram_id": engram_id}
        except Exception as e:
            logger.error(f"Store Fault: {e}")
            return {"status": "error", "message": str(e)}

    async def retrieve(self, engram_id: str) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._sync_retrieve, engram_id)

    def _sync_retrieve(self, engram_id: str):
        for path in self.paths.values():
            records = self._load_json(path)
            if engram_id in records:
                return records[engram_id].get("data")
        return None

    async def query_memory(self, query: str, top_k: int = 5, tier: Optional[str] = None) -> List[Dict[str, Any]]:
        """Improved SOTA querying with Tier Bias."""
        query_text = query.lower()
        query_emb = np.array(self._generate_heuristic_embedding(query))
        
        # Improvement: Determine implicit tier bias from query keywords
        is_architectural = any(anchor in query_text for anchor in ARCHITECTURAL_ANCHORS)
        
        results = []
        for doc_id, doc in self._docs.items():
            if tier and doc.tier != tier.lower():
                continue
            
            if doc.embedding is None:
                continue
            
            doc_emb = np.array(doc.embedding)
            norm_a = np.linalg.norm(query_emb)
            norm_b = np.linalg.norm(doc_emb)
            sim = (np.dot(query_emb, doc_emb) / (norm_a * norm_b)) if (norm_a > 0 and norm_b > 0) else 0.0
            
            # Applying Tier Bias Improvement
            if is_architectural and doc.tier == TIER_LONG:
                sim *= 1.5 # Boost foundational matches
            elif doc.tier == TIER_FAST:
                sim *= 1.1 # Subtle boost for session context
                
            results.append({
                "id": doc_id, 
                "score": float(sim), 
                "tier": doc.tier,
                "metadata": doc.metadata
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def list_engrams(self, tier: Optional[str] = None) -> List[str]:
        return await asyncio.to_thread(self._sync_list, tier)

    def _sync_list(self, tier: Optional[str] = None):
        ids = []
        for t, path in self.paths.items():
            if tier and t != tier.lower():
                continue
            records = self._load_json(path)
            ids.extend(records.keys())
        return ids

_memory_logic = None

async def get_memory_logic() -> MemoryOrganLogic:
    global _memory_logic
    if _memory_logic is None:
        _memory_logic = MemoryOrganLogic()
    return _memory_logic

if __name__ == "__main__":
    async def test():
        logic = await get_memory_logic()
        await logic.store_engram("rule-9-proto", {"text": "Rule 9 governs memory tiers."}, layer=TIER_LONG)
        res = await logic.query_memory("Rule 9", top_k=1)
        print(f"Top Result [{res[0]['tier']}]: {res[0]['score']:.4f}")
    asyncio.run(test())