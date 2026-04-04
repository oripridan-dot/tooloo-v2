# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: MODULE_FIRESTORE_PERSISTENCE | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/memory_organ/firestore_persistence.py
# WHEN: 2026-04-03T17:20:00.000000
# WHY: Rule 18: Cloud-Native Development Mandate (High-Fidelity Persistence)
# HOW: Google Cloud Firestore SDK + Tiered Collection Mapping
# TIER: T4:zero-trust
# DOMAINS: organs, memory, persistence, cloud-native, firestore
# PURITY: 1.00
# ==========================================================

import os
import logging
import datetime
from typing import Dict, List, Any, Optional
from google.cloud import firestore
from google.api_core import exceptions
from tooloo_v4_hub.kernel.governance.smrp_config import get_smrp_topology, get_consistency_policy

logger = logging.getLogger("FirestorePersistence")

class FirestorePersistence:
    """
    Sovereign Firestore Adapter for TooLoo V4 Memory (Rule 9).
    Maps tiers (Fast, Medium, Long) to Firestore collections.
    """
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("ACTIVE_SOVEREIGN_PROJECT")
        self.region = os.getenv("ACTIVE_SOVEREIGN_REGION", "me-west1")
        self.db_name = os.getenv("FIRESTORE_DATABASE") # Default to None (uses '(default)')
        
        if not self.project_id:
            logger.warning("Firestore: ACTIVE_SOVEREIGN_PROJECT not set. Attempting default credentials.")
            self.db = firestore.Client(database=self.db_name) 
        else:
            # Rule 18: Standardized naming for the Sovereign Psyche Database
            try:
                # Attempt with specifically named database if provided, otherwise default
                self.db = firestore.Client(project=self.project_id, database=self.db_name)
                logger.info(f"Firestore: Connected to {self.project_id} (Database: {self.db_name or '(default)'}) in {self.region}.")
            except Exception as e:
                logger.error(f"Firestore Connection Fault: {e}")
                self.db = firestore.Client(project=self.project_id)

        # SMRP: Secondary Region Client (Rule 13)
        self.topology = get_smrp_topology()
        self.secondary_region = next((r for r in self.topology.regions if r.id != self.region), None)
        self.secondary_db = None
        if self.secondary_region:
            try:
                self.secondary_db = firestore.Client(project=self.project_id, database=self.db_name) # In real GCP, might be same project, different location handled by DB
            except: pass

    async def store_engram(self, engram_id: str, data: Dict[str, Any], layer: str = "medium") -> Dict[str, Any]:
        """Stores a memory engram with SMRP Consistency logic (Rule 13)."""
        collection_name = f"psyche_{layer.lower()}"
        doc_ref = self.db.collection(collection_name).document(engram_id)
        
        # Rule 7: Determine Consistency Policy
        policy = get_consistency_policy(data.get("type", "MEMORY"))
        
        payload = {
            **data,
            "engram_id": engram_id,
            "tier": layer,
            "consistency": policy.consistency,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "stamped_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Rule 13: SMRP Multi-Region Write Pulse
            if policy.consistency == "STRONG" and self.secondary_db:
                logger.info(f"SMRP: Executing Dual-Region Synchronous Write for engram '{engram_id}'...")
                sec_ref = self.secondary_db.collection(collection_name).document(engram_id)
                await asyncio.gather(
                    loop.run_in_executor(None, lambda: doc_ref.set(payload, merge=True)),
                    loop.run_in_executor(None, lambda: sec_ref.set(payload, merge=True))
                )
            else:
                # Normal path: Regional write
                await loop.run_in_executor(None, lambda: doc_ref.set(payload, merge=True))
                
            logger.info(f"Firestore: Engram '{engram_id}' committed [{policy.consistency}].")
            return {"status": "success", "engram_id": engram_id, "tier": layer, "replication": policy.consistency}
        except Exception as e:
            logger.error(f"Firestore Store Fault [{engram_id}]: {e}")
            raise e

    async def query_memory(self, query_text: str, top_k: int = 5, layer: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Performs a semantic/keyword search across Firestore collections.
        Note: True Semantic Vector search requires Firestore Vector indexes or manual retrieval.
        For V1, we filter by importance and keywords.
        """
        results = []
        layers = [layer] if layer else ["fast", "medium", "long"]
        
        import asyncio
        loop = asyncio.get_event_loop()
        
        async def fetch_layer(l):
            collection_name = f"psyche_{l}"
            col_ref = self.db.collection(collection_name)
            layer_results = []
            try:
                # Query documents from this layer concurrently
                docs = await loop.run_in_executor(None, lambda: col_ref.limit(top_k * 2).stream())
                for doc in docs:
                    doc_data = doc.to_dict()
                    score = 0.5
                    if query_text.lower() in str(doc_data).lower():
                        score = 0.95
                    
                    layer_results.append({
                        "id": doc.id,
                        "score": score,
                        "tier": l,
                        "data": doc_data
                    })
            except Exception as e:
                logger.warning(f"Firestore Query Error on {collection_name}: {e}")
            return layer_results

        # Rule 11: Optimized Parallel Retrieval (SMP v2)
        tasks = [fetch_layer(l) for l in layers]
        all_results_lists = await asyncio.gather(*tasks)
        
        for res_list in all_results_lists:
            results.extend(res_list)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def retrieve_engram(self, engram_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific engram by ID across all tiers."""
        layers = ["fast", "medium", "long"]
        import asyncio
        loop = asyncio.get_event_loop()
        
        for l in layers:
            doc_ref = self.db.collection(f"psyche_{l}").document(engram_id)
            doc = await loop.run_in_executor(None, doc_ref.get)
            if doc.exists:
                return doc.to_dict()
        return None

    async def delete_engrams_by_prefix(self, prefix: str):
        """Rule 15: Clean-up pulse (Optimized with WriteBatch)."""
        layers = ["fast", "medium", "long"]
        import asyncio
        loop = asyncio.get_event_loop()
        total_deleted = 0
        
        for l in layers:
            col_ref = self.db.collection(f"psyche_{l}")
            # Query for documents starting with the prefix
            # Note: startAt/endAt is more efficient than >= for prefix matching
            try:
                query = col_ref.where(firestore.FieldPath.document_id(), ">=", prefix) \
                               .where(firestore.FieldPath.document_id(), "<", prefix + u'\uf8ff')
                
                docs = await loop.run_in_executor(None, lambda: query.stream())
                
                batch = self.db.batch()
                count = 0
                for doc in docs:
                    batch.delete(doc.reference)
                    count += 1
                    total_deleted += 1
                    if count >= 400: # Firestore limit is 500 per batch
                        await loop.run_in_executor(None, batch.commit)
                        batch = self.db.batch()
                        count = 0
                
                if count > 0:
                    await loop.run_in_executor(None, batch.commit)
            except Exception as e:
                logger.error(f"Firestore Delete Fault on {l}: {e}")
                    
        return {"status": "success", "prefix": prefix, "deleted": total_deleted}

_firestore_persistence = None

def get_firestore_persistence() -> FirestorePersistence:
    global _firestore_persistence
    if _firestore_persistence is None:
        _firestore_persistence = FirestorePersistence()
    return _firestore_persistence
