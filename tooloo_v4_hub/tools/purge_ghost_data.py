import json
import os
from pathlib import Path

def audit_memory():
    psyche_roots = [Path("psyche_bank"), Path("tooloo_v4_hub/organs/memory_organ/psyche_bank")]
    ghost_ids = []
    
    for root in psyche_roots:
        if not root.exists():
            continue
        
        for file in root.glob("*.json"):
            if file.name == "vector_store.json":
                continue
            
            print(f"Auditing {file}...")
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                
                initial_count = len(data)
                cleaned_data = {}
                
                for key, val in data.items():
                    # Rule 10/1 Audit
                    record_data = val.get("data", {})
                    stamp = val.get("stamp", {})
                    
                    # Ghost detection (pred_... or missing 6W fields)
                    is_ghost = (
                        key.startswith("pred_") or 
                        key == "session_checkpoint" or
                        record_data.get("source") is None or
                        stamp.get("who") in [None, "Hub"] # Hub is too generic (Rule 10 breach)
                    )
                    
                    if is_ghost:
                        print(f"  [GHOST DETECTED]: {key}")
                        ghost_ids.append(key)
                    else:
                        cleaned_data[key] = val
                
                if len(cleaned_data) < initial_count:
                    print(f"  Purging {initial_count - len(cleaned_data)} records...")
                    with open(file, "w") as f:
                        json.dump(cleaned_data, f, indent=2)
                
            except Exception as e:
                print(f"  Error auditing {file}: {e}")

if __name__ == "__main__":
    audit_memory()
