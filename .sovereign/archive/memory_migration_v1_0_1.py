# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_MEMORY_MIGRATION.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tools/memory_migration.py
# WHEN: 2026-04-01T16:35:57.936967+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import json
import os
from pathlib import Path

# Paths
hub_root = Path("/Users/oripridan/ANTIGRAVITY/tooloo-v2/tooloo_v4_hub")
psyche_bank = hub_root / "psyche_bank"
learned_engrams_path = psyche_bank / "learned_engrams.json"
vector_store_path = psyche_bank / "vector_store.json"

long_path = psyche_bank / "long_memory.json"
medium_path = psyche_bank / "medium_memory.json"
fast_path = psyche_bank / "fast_memory.json"

TIER_LONG = "long"
TIER_MEDIUM = "medium"
TIER_FAST = "fast"

def migrate():
    print("--- Memory Migration Initialized ---")
    
    if not learned_engrams_path.exists():
        print(f"Error: {learned_engrams_path} not found.")
        return

    with open(learned_engrams_path, 'r') as f:
        old_engrams = json.load(f)

    with open(vector_store_path, 'r') as f:
        old_vectors = json.load(f)

    long_records = {}
    medium_records = {}
    fast_records = {}
    
    new_vectors = {}

    # Logic for categorization
    for eid, record in old_engrams.items():
        data = record.get("data", {})
        e_type = data.get("type", "")
        e_url = data.get("url", "")
        
        target_tier = TIER_MEDIUM # Default
        
        # Rule of thumb: Major academy SOTA is LONG
        if e_type == "sota_ingestion":
            if any(provider in e_url for provider in ["google", "anthropic", "meta", "ibm", "deepseek", "openai"]):
                target_tier = TIER_LONG
            else:
                target_tier = TIER_MEDIUM
        elif e_type in ["prediction", "outcome"]:
            target_tier = TIER_MEDIUM
        
        # Update record with new tier
        record["tier"] = target_tier
        
        if target_tier == TIER_LONG:
            long_records[eid] = record
        elif target_tier == TIER_MEDIUM:
            medium_records[eid] = record
        else:
            fast_records[eid] = record

        # Update Vector Store entry
        if eid in old_vectors:
            vec_entry = old_vectors[eid]
            vec_entry["tier"] = target_tier
            new_vectors[eid] = vec_entry

    # Save new tiers
    for path, data in [(long_path, long_records), (medium_path, medium_records), (fast_path, fast_records)]:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Manifested {len(data)} engrams in {path.name}")

    # Save updated vector store
    with open(vector_store_path, 'w') as f:
        json.dump(new_vectors, f, indent=2)
    print(f"Synchronized Vector Store with {len(new_vectors)} indexed nodes.")

    print("--- Migration Successful ---")

if __name__ == "__main__":
    migrate()
