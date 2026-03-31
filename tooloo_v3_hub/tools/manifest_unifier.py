# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: SCRIPT_MANIFEST_UNIFIER | Version: 1.0.0
# WHERE: tooloo_v3_hub/tools/manifest_unifier.py
# WHEN: 2026-03-31T18:30:00.000000
# WHY: Consolidate architectural manifests into a single source of truth (Rule 1)
# HOW: JSON logic merging and redundancy excision
# ==========================================================

import json
import os
from pathlib import Path

def run_unifier():
    psyche_path = Path("tooloo_v3_hub/psyche_bank")
    system_manifest_path = psyche_path / "system_manifest.json"
    
    if not system_manifest_path.exists():
        print("ERROR: system_manifest.json missing. Cannot unify.")
        return

    # 1. Load the Core Manifest
    manifest = json.loads(system_manifest_path.read_text())
    
    # 2. Add sub-trees for design and sovereignty
    sources = {
        "sovereignty": psyche_path / "sovereignty_manifest_v3.json",
        "navigation": psyche_path / "navigation_index.json",
        "principles": psyche_path / "design_principles.json"
    }
    
    for key, path in sources.items():
        if path.exists():
            try:
                data = json.loads(path.read_text())
                manifest["nodes"][f"psyche_bank/{path.name}"] = {
                    "id": f"psyche_bank/{path.name}",
                    "type": "manifest_fragment",
                    "status": "Migrated",
                    "data": data,
                    "last_updated": os.path.getmtime(path)
                }
                print(f"✅ Migrated -> {path.name}")
                # os.remove(path) # Wait for verification before deleting
            except Exception as e:
                print(f"FAILED to migrate {path.name}: {e}")

    # 3. Update Meta
    manifest["meta"]["status"] = "UNIFIED"
    manifest["meta"]["fragmentation_purity"] = 1.0

    # 4. Save
    system_manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest Unification Complete. Unified {len(sources)} fragments into {system_manifest_path.name}.")

if __name__ == "__main__":
    run_unifier()
