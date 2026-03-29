import unittest
import json
import os
from pathlib import Path
from engine.cognitive import CognitiveCoordinate, SystemAgency, ExecutionIntent
from engine.kv_store import get_kv_store
from engine.buddy_cache import BuddyCache

class TestCognitiveSystem(unittest.TestCase):
    def test_cognitive_coordinate_determinism(self):
        """Verify that identical inputs produce the same hash_id."""
        # Fix 'when' for determinism
        fixed_when = 1711310000.0
        c1 = CognitiveCoordinate(
            when=fixed_when,
            where="tests/test_cognitive.py",
            what="Test action",
            how="test_case",
            why=ExecutionIntent.BUILD,
            who=SystemAgency.EXECUTOR
        )
        c2 = CognitiveCoordinate(
            when=fixed_when,
            where="tests/test_cognitive.py",
            what="Test action",
            how="test_case",
            why=ExecutionIntent.BUILD,
            who=SystemAgency.EXECUTOR
        )
        self.assertEqual(c1.hash_id, c2.hash_id)
        self.assertEqual(len(c1.hash_id), 64)  # SHA-256

    def test_kv_store_persistence(self):
        """Verify that payloads can be stored and retrieved from the KV store."""
        kv = get_kv_store()
        test_id = "test-hash-123"
        payload = {"result": "success", "data": [1, 2, 3]}
        
        kv.set(test_id, payload)
        retrieved = kv.get(test_id)
        
        self.assertEqual(retrieved, payload)

    def test_buddy_cache_antigravity_layer(self):
        """Verify that BuddyCache can retrieve from Antigravity layer."""
        kv = get_kv_store()
        cache = BuddyCache()
        
        # Pre-populate VectorStore and KVStore
        test_what = "Explain the 6W system"
        test_intent = "EXPLAIN"
        test_response = "The 6W system is a deterministic cognitive coordinate system."
        
        # 1. Create a coordinate
        coord = CognitiveCoordinate(
            when=1711310000.0,
            where="engine/pipeline.py",
            what=test_what,
            how="NStrokeEngine.run",
            why=ExecutionIntent.EXPLAIN,
            who=SystemAgency.EXECUTOR
        )
        
        # 2. Store in KV
        kv.set(coord.hash_id, {"response_text": test_response})
        
        # 3. Index in VectorStore (BuddyCache uses its own _vector_store instance)
        # VectorStore.add signature: add(id, text, metadata=None)
        cache._vector_store.add(coord.hash_id, test_what, metadata=coord.model_dump())
        
        # 4. Lookup
        result = cache.lookup("test-session", test_what, test_intent)
        
        self.assertEqual(result, test_response)

if __name__ == "__main__":
    unittest.main()
