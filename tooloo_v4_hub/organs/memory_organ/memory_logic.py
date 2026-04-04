# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: memory_logic.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/memory_organ/memory_logic.py
# WHEN: 2026-04-03T16:08:23.386435+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
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
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
from tooloo_v4_hub.organs.memory_organ.firestore_persistence import get_firestore_persistence
from functools import lru_cache
import collections

class SovereignConstitutionException(Exception):
    """Rule 10/11 Violation: Structural data integrity breach."""
    pass

logger = logging.getLogger("MemoryOrganLogic")

TIER_FAST = "fast"
TIER_MEDIUM = "medium"
TIER_LONG = "long"

# Foundational Keywords that trigger a LONG-tier bias (Rule 1-18)
ARCHITECTURAL_ANCHORS = [
    "rule", "constitution", "sovereign", "purity", "identity", "principle", "sota",
    "dag", "inverse-dag", "manifestation", "jit", "autopoiesis", "ouroboros",
    "decoupling", "federated", "6w", "accountability", "purity-audit", "vitality"
]

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
    
    def __init__(self, psyche_bank_root: Optional[str] = None):
        if not psyche_bank_root:
            psyche_bank_root = os.getenv("PSYCHE_BANK_ROOT") or "psyche_bank"
        
        self.root = Path(psyche_bank_root)
        self.paths = {
            TIER_FAST: self.root / "fast_memory.json",
            TIER_MEDIUM: self.root / "medium_memory.json",
            TIER_LONG: self.root / "long_memory.json"
        }
        self.vector_store_path = self.root / "vector_store.json"
        self._docs: Dict[str, MemoryRecord] = {}
        self._embedding_cache: Dict[str, List[float]] = {} # Rule 7: Efficiency Cache
        self._query_latency_cache = collections.OrderedDict() # Rule 7: LRU Result Cache
        self._lock = asyncio.Lock()
        
        cloud_env = os.getenv("CLOUD_NATIVE", "true").lower() == "true"
        self.project_id = os.getenv("ACTIVE_SOVEREIGN_PROJECT")
        self.region = os.getenv("ACTIVE_SOVEREIGN_REGION", "me-west1")
        
        can_run_cloud = bool(self.project_id or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        self.cloud_native = cloud_env and can_run_cloud
        
        if cloud_env and not can_run_cloud:
            logger.warning("Memory: CLOUD_NATIVE=true but ACTIVE_SOVEREIGN_PROJECT is missing. Falling back to robust local offline persistence.")
        
        if self.cloud_native:
            # Enforce defaults for safe Vertex init
            self.project_id = self.project_id or "too-loo-zi8g7e"
            self.firestore = get_firestore_persistence()
            try:
                vertexai.init(project=self.project_id, location=self.region)
                self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
                logger.info(f"Memory: Cloud Native ACTIVE (Project: {self.project_id}). Vertex AI Embeddings and Firestore initialized.")
            except Exception as e:
                logger.error(f"Memory: Vertex AI Init Failed: {e}. Falling back to HEURISTIC.")
                self.embedding_model = None
        else:
            self.firestore = None
            self.embedding_model = None
            self._load_vector_store()

    def _load_vector_store(self):
        """Rule 12: Load vector store with self-healing JSON wrapper."""
        data = self._load_json(self.vector_store_path)
        if data:
            for eid, entry in data.items():
                self._docs[eid] = MemoryRecord(
                    id=eid,
                    text="",
                    metadata=entry.get("metadata", {}),
                    tier=entry.get("tier", TIER_MEDIUM),
                    embedding=entry.get("vector")
                )
            logger.info(f"Memory: Vector Store synchronized [{len(self._docs)} Nodes].")

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
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Memory: JSON Corruption detected at {path}: {e}")
                # Rule 12: Autonomous Self-Healing (Backup and restart)
                try:
                    path.rename(path.with_suffix(".json.corrupt"))
                except: pass
        return {}

    def _save_json(self, path: Path, data: Dict):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _generate_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """Rule 9: Real SOTA Semantic Embedding (Vertex AI) with Rule 7 Cache."""
        cache_key = f"{task_type}:{text}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.embedding_model:
            return self._generate_heuristic_embedding(text)
            
        try:
            inputs = [TextEmbeddingInput(text, task_type)]
            embeddings = self.embedding_model.get_embeddings(inputs)
            vector = [float(x) for x in embeddings[0].values]
            self._embedding_cache[cache_key] = vector
            return vector
        except Exception as e:
            logger.error(f"Vertex AI Embedding Fault: {e}. Falling back to Heuristic Hash.")
            return self._generate_heuristic_embedding(text)

    def _generate_heuristic_embedding(self, text: str) -> List[float]:
        """Rule 11: Fallback positional vectorization (512-dim)."""
        tokens = str(text).lower().split()
        dim = 768 # Match Vertex AI default dimensionality if possible, or stick to 512
        vector = [0.0] * dim
        for i, token in enumerate(tokens):
            idx = hash(token) % dim
            weight = 1.0 / (1.0 + (i * 0.05))
            if token in ARCHITECTURAL_ANCHORS:
                weight *= 5.0 
            vector[idx] += weight
        return vector

    async def _compact_to_long_tier(self):
        """Rule 9: Autonomous Transcript Compaction (Fast -> Long Migration)."""
        logger.info("Memory: Initiating Autonomous Transcript Compaction...")
        fast_records = []
        
        if self.firestore:
            # Query the psyche_fast collection
            fast_results = await self.firestore.query_memory("", top_k=50, layer=TIER_FAST)
            fast_records = [r["data"] for r in fast_results]
        else:
            records_dict = self._load_json(self.paths[TIER_FAST])
            fast_records = list(records_dict.values())

        if len(fast_records) < 10:
            return # Not enough density for a meaningful anchor

        # Create a Summary/Engram from the collective "Fast" memory
        summary_text = f"COMPACTED_NEXUS_{datetime.datetime.now().strftime('%Y%m%d')}: "
        summary_text += " | ".join([r.get("text", str(r.get("data", "")))[:100] for r in fast_records[:10]])
        
        c_id = f"compact_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        payload = {
            "type": "compacted_transcript",
            "content": summary_text,
            "source_records": [r.get("engram_id") for r in fast_records],
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "stamping": {"who": "Sovereign-Autopoietic-Loop", "why": "Rule 9 Compaction"}
        }

        # Store in LONG tier
        await self.store_engram(c_id, payload, layer=TIER_LONG)
        
        # Rule 15: Clear the FAST tier to maintain zero-footprint
        if self.firestore:
            await self.firestore.delete_engrams_by_prefix("fast_")
        else:
            self._save_json(self.paths[TIER_FAST], {})
            
        logger.info(f"Memory: Compaction complete. Engram '{c_id}' anchored in Long-Term Memory.")

    async def store(self, engram_id: str, data: Dict[str, Any], layer: str = TIER_MEDIUM) -> Dict[str, Any]:
        """Wrapper for store_engram to maintain Hub Orchestrator compatibility."""
        return await self.store_engram(engram_id, data, layer)

    async def log_execution_receipt(self, mission_id: str, receipt: Dict[str, Any]) -> str:
        """Primitive 8: Solidified storage for mission execution receipts."""
        r_id = f"mission_receipt_{mission_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        payload = {
            "type": "execution_receipt",
            "mission_id": mission_id,
            "receipt": receipt,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "stamping": {
                "who": "Sovereign-Orchestrator",
                "what": "Execution Tracking",
                "rules": [8, 10, 11]
            }
        }
        await self.store_engram(r_id, payload, layer=TIER_MEDIUM)
        return r_id

    async def store_knowledge_item(self, ki_id: str, decision: str, rationale: str, impact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formalized Knowledge Capture (Buddy Mandate).
        Stores architectural decisions and technical debt metrics.
        """
        payload = {
            "type": "knowledge_item",
            "decision": decision,
            "rationale": rationale,
            "impact": impact,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "stamping": {
                "who": "Sovereign-Architect",
                "why": "Buddy Sprint Completion Mandate",
                "rules": [7, 10, 11, 16]
            }
        }
        return await self.store_engram(f"ki_{ki_id}", payload, layer=TIER_LONG)

    async def query_knowledge_base(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Queries specifically for Knowledge Items (KIs)."""
        results = await self.query_memory(query, top_k=20)
        ki_results = [r for r in results if r.get("metadata", {}).get("type") == "knowledge_item"]
        return ki_results[:top_k]


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
        
        # Rule 10: Pre-emptive Zero-Trust Ingestion Protocol
        self._validate_rule_10(engram_id, data)
        
        if self.firestore:
            return await self.firestore.store_engram(engram_id, data, layer)
            
        async with self._lock:
            return await asyncio.to_thread(self._sync_store, engram_id, data, layer)

    def _validate_rule_10(self, engram_id: str, data: Dict[str, Any]):
        """Mandated validation layer to reject atomic ghost data (Rule 1, 10)."""
        stamp = data.get("stamp") or data.get("stamping")
        
        if not stamp:
            raise SovereignConstitutionException(f"Rule 10 Violation: Engram '{engram_id}' missing mandatory 6W stamp.")
        
        # Mandatory 6W Fields
        mandatory = ["who", "what", "where", "why", "how"]
        missing = [f for f in mandatory if not stamp.get(f) or stamp.get(f) == "Hub"]
        
        # Root-level source check
        if data.get("source") is None and stamp.get("where") is None:
            missing.append("source/where")
            
        if missing:
            raise SovereignConstitutionException(
                f"Rule 10 Violation: Engram '{engram_id}' failed structural validation. "
                f"Missing or generic fields: {', '.join(missing)}"
            )

    async def store_engrams(self, engrams: List[Dict[str, Any]], layer: str = TIER_MEDIUM) -> Dict[str, Any]:
        """Batch store engrams (Rule 11: Optimized IO)."""
        layer = layer.lower()
        if layer not in self.paths:
            layer = TIER_MEDIUM
        async with self._lock:
            return await asyncio.to_thread(self._sync_store_batch, engrams, layer)

    def _sync_store_batch(self, engrams: List[Dict[str, Any]], layer: str):
        try:
            records = self._load_json(self.paths[layer])
            for entry in engrams:
                eid = entry["engram_id"]
                data = entry["data"]
                
                # Rule 10: 6W Stamping
                stamp = data.get("stamp") or {"who": "Hub", "what": "Batch_Store", "when": datetime.datetime.now().isoformat()}
                
                records[eid] = {
                    "data": data,
                    "tier": layer,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "stamp": stamp
                }
                
                # Indexing
                index_text = data.get("full_md") or data.get("text") or str(data)
                embedding = self._generate_embedding(index_text)
                
                self._docs[eid] = MemoryRecord(
                    id=eid,
                    text="",
                    metadata={
                        "type": data.get("type", "engram"),
                        "tier": layer,
                        "source": data.get("source"),
                        "chunk_index": data.get("chunk_index")
                    },
                    tier=layer,
                    embedding=embedding
                )
            
            self._save_json(self.paths[layer], records)
            self._save_vector_store()
            return {"status": "success", "count": len(engrams)}
        except Exception as e:
            logger.error(f"Batch Store Fault: {e}")
            return {"status": "error", "message": str(e)}

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
            embedding = self._generate_embedding(index_text)
            
            # Rule 3/9: Enriched Metadata for source tracking
            enriched_metadata = {
                "type": data.get("type", "engram"),
                "tier": layer,
                "source": data.get("source"),
                "chunk_index": data.get("chunk_index"),
                "total_chunks": data.get("total_chunks"),
                "stamping": data.get("stamping")
            }
            
            self._docs[engram_id] = MemoryRecord(
                id=engram_id,
                text="",
                metadata=enriched_metadata,
                tier=layer,
                embedding=embedding
            )
            self._save_vector_store()
            return {"status": "success", "engram_id": engram_id}
        except Exception as e:
            logger.error(f"Store Fault: {e}")
            return {"status": "error", "message": str(e)}

    async def retrieve(self, engram_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return await asyncio.to_thread(self._sync_retrieve, engram_id)

    def _sync_retrieve(self, engram_id: str):
        for path in self.paths.values():
            records = self._load_json(path)
            if engram_id in records:
                return records[engram_id].get("data")
        return None

    async def clear_engrams_by_prefix(self, prefix: str):
        """Rule 15: Garbage Collection for re-indexed components."""
        async with self._lock:
            return await asyncio.to_thread(self._sync_clear_prefix, prefix)

    def _sync_clear_prefix(self, prefix: str):
        logger.info(f"Memory: Clearing engrams with prefix '{prefix}'...")
        removed_count = 0
        
        # Clear from Tiers
        for tier, path in self.paths.items():
            records = self._load_json(path)
            keys_to_remove = [k for k in records.keys() if k.startswith(prefix)]
            if keys_to_remove:
                for k in keys_to_remove:
                    del records[k]
                    removed_count += 1
                self._save_json(path, records)
        
        # Clear from Vector Store
        keys_to_remove_docs = [k for k in self._docs.keys() if k.startswith(prefix)]
        for k in keys_to_remove_docs:
            del self._docs[k]
        
        if removed_count > 0:
            self._save_vector_store()
            logger.info(f"Memory: {removed_count} engrams purged.")
        return {"status": "success", "removed": removed_count}

    async def query_memory(self, query: str = "", top_k: int = 5, tier: Optional[str] = None) -> List[Dict[str, Any]]:
        """Improved SOTA querying with Sovereign Mandate priority logic + LRU Cache."""
        cache_key = f"{query}:{top_k}:{tier}"
        if cache_key in self._query_latency_cache:
            # Rule 7: Move to end (LRU)
            self._query_latency_cache.move_to_end(cache_key)
            return self._query_latency_cache[cache_key]

        if self.firestore:
            results = await self.firestore.query_memory(query, top_k, tier)
            # Store in cache
            self._query_latency_cache[cache_key] = results
            if len(self._query_latency_cache) > 128:
                self._query_latency_cache.popitem(last=False)
            return results
            
        query_text = (query or "").lower()
        query_emb_list = self._generate_embedding(query_text, task_type="RETRIEVAL_QUERY")
        query_emb = np.array(query_emb_list)
        norm_a = np.linalg.norm(query_emb)
        
        # Improvement: Determine implicit tier bias from query keywords
        is_architectural = any(anchor in query_text for anchor in ARCHITECTURAL_ANCHORS)
        # Rule 1/13: Sovereign Mandates force LONG_TIER retrieval
        force_long_term = "sovereign" in query_text or "constitution" in query_text
        
        results = []
        for doc_id, doc in self._docs.items():
            if tier and doc.tier != tier.lower():
                continue
            
            if doc.embedding is None:
                continue
            
            # Dimension alignment check (for version migration)
            doc_vec = doc.embedding
            target_dim = len(query_emb_list)
            if len(doc_vec) < target_dim:
                doc_vec = doc_vec + [0.0] * (target_dim - len(doc_vec))
            elif len(doc_vec) > target_dim:
                doc_vec = doc_vec[:target_dim]
                
            doc_emb = np.array(doc_vec)
            norm_b = np.linalg.norm(doc_emb)
            
            # Safe cosine similarity
            if norm_a > 0 and norm_b > 0:
                sim = np.dot(query_emb, doc_emb) / (norm_a * norm_b)
            else:
                sim = 0.5 if not query_text else 0.0
            
            # Applying Tier Bias Improvement
            if is_architectural and doc.tier == TIER_LONG:
                sim *= 2.0 # Rule 3: Heavy boost for foundational matches
            
            if force_long_term and doc.tier == TIER_LONG:
                sim += 1.0 # Guarantee foundational presence
                
            elif doc.tier == TIER_FAST:
                sim *= 1.2 # Subtle boost for session context
                
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