# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining firestore_memory.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.912223
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/firestore_memory.py — Tier 3 Cold Memory (GCP Firestore).

Integrates natively with Google Cloud Platform's scale-to-zero serverless architecture.
If `GOOGLE_APPLICATION_CREDENTIALS` is available, this acts as the infinite-scaling
Knowledge Graph for "pure facts". If not, acts as a compliant mock.
"""
import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class ColdMemoryFirestore:
    def __init__(self, collection_name: str = "cold_memory"):
        self.collection_name = collection_name
        self.enabled = False
        self.db = None
        
        # Check GCP credentials context
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                from google.cloud import firestore
                self.db = firestore.Client()
                self.enabled = True
                logger.info(f"ColdMemory: Native GCP Firestore connected for '{collection_name}'.")
            except Exception as e:
                logger.warning(f"ColdMemory: GCP setup found but init failed: {e}")
        else:
            logger.info("ColdMemory: No GCP Credentials. Operating in offline/mock mode.")
            self._mock_db = {}

    def store_fact(self, fact_id: str, payload: Dict[str, Any]) -> bool:
        """Stores a pure fact in Cold Memory (Firestore)."""
        if not self.enabled:
            self._mock_db[fact_id] = payload
            return True
            
        try:
            doc_ref = self.db.collection(self.collection_name).document(fact_id)
            doc_ref.set(payload, merge=True)
            return True
        except Exception as e:
            logger.error(f"ColdMemory: Failed writing to Firestore for {fact_id}: {e}")
            return False

    def link_facts(self, source_id: str, target_id: str, relation: str) -> bool:
        """Creates a symbolic link between two facts in the Knowledge Graph."""
        link_data = {
            "source": source_id,
            "target": target_id,
            "relation": relation,
            "type": "symbolic_link"
        }
        if not self.enabled:
            if "links" not in self._mock_db:
                self._mock_db["links"] = []
            self._mock_db["links"].append(link_data)
            return True
            
        try:
            # We store links in a sub-collection of the source fact
            link_id = f"link_{source_id}_{target_id}"
            doc_ref = self.db.collection(self.collection_name).document(source_id).collection("links").document(link_id)
            doc_ref.set(link_data)
            return True
        except Exception as e:
            logger.error(f"ColdMemory: Failed linking facts {source_id} -> {target_id}: {e}")
            return False

    def query_facts(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Retrieves facts from Cold Memory."""
        if not self.enabled:
            return [v for k, v in self._mock_db.items() if k != "links"][:limit]
            
        try:
            docs = self.db.collection(self.collection_name).limit(limit).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"ColdMemory: Failed querying Firestore: {e}")
            return []
            
