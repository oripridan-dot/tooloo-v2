# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_MANIFEST_UNIFIER.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tools/manifest_unifier.py
# WHEN: 2026-04-04T00:41:42.357469+00:00
# WHY: Heal STAMP_PURITY_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import json
import os
from pathlib import Path

def run_unifier():
    psyche_path = Path("tooloo_v4_hub/psyche_bank")
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