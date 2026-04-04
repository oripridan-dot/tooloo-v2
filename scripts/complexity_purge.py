import json
import os

REGISTRY_PATH = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/tooloo_v4_hub/psyche_bank/model_garden_registry.json"

def complexity_purge():
    if not os.path.exists(REGISTRY_PATH):
        print("Registry not found.")
        return

    with open(REGISTRY_PATH, "r") as f:
        data = json.load(f)

    # Rule 7: Purge Uncalibrated Noise (Minimal Complexity)
    purged_count = 0
    for provider in data["models"]:
        original_count = len(data["models"][provider])
        # Keep only models with a known task AND non-placeholder capabilities
        data["models"][provider] = [
            m for m in data["models"][provider] 
            if m.get("task") != "unknown" and "capabilities" in m
        ]
        purged_count += (original_count - len(data["models"][provider]))

    with open(REGISTRY_PATH, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Complexity Purge Complete: {purged_count} uncalibrated variables removed (Rule 7).")

if __name__ == "__main__":
    complexity_purge()
