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
            # Local mock behaviour so unit tests pass without GCP project setups.
            self._mock_db[fact_id] = payload
            return True
            
        try:
            doc_ref = self.db.collection(self.collection_name).document(fact_id)
            doc_ref.set(payload, merge=True)
            return True
        except Exception as e:
            logger.error(f"ColdMemory: Failed writing to Firestore for {fact_id}: {e}")
            return False

    def query_facts(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Retrieves facts from Cold Memory."""
        if not self.enabled:
            return list(self._mock_db.values())[:limit]
            
        try:
            docs = self.db.collection(self.collection_name).limit(limit).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"ColdMemory: Failed querying Firestore: {e}")
            return []
            
