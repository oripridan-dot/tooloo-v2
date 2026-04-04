# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TREE_BUILDER.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v4_hub/tools/tree_builder.py
# WHEN: 2026-03-31T14:26:13.336194+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: tool, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import os
import re
import logging
from pathlib import Path
from tooloo_v4_hub.kernel.governance.stamping import StampingEngine
from tooloo_v4_hub.kernel.governance.living_map import get_living_map

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TreeBuilder")

def run_tree_builder(root_dir: str = "tooloo_v4_hub"):
    map_engine = get_living_map()
    root = Path(root_dir)
    tracked_exts = (".py", ".html", ".js", ".css", ".ts")
    
    print(f"Tree Formation: Mapping {root_dir}...")
    
    # regex for python imports within the hub
    import_pattern = re.compile(r"from (tooloo_v4_hub\.[a-zA-Z0-9_\.]+) import|import (tooloo_v4_hub\.[a-zA-Z0-9_\.]+)")
    
    nodes_found = 0
    
    for file_path in root.rglob("*"):
        if not file_path.is_file() or file_path.suffix not in tracked_exts:
            continue
            
        try:
            rel_path = str(file_path)
            content = file_path.read_text(errors="ignore")
            
            metadata = StampingEngine.extract_metadata(content)
            if not metadata:
                continue
                
            dependencies = []
            if file_path.suffix == ".py":
                matches = import_pattern.findall(content)
                for m in matches:
                    mod_path = m[0] if m[0] else m[1]
                    dep_path = mod_path.replace(".", "/") + ".py"
                    if os.path.exists(dep_path):
                        dependencies.append(dep_path)
            
            map_engine.register_node(rel_path, metadata, dependencies)
            nodes_found += 1
        except Exception as e:
            print(f"FAILED to map {file_path}: {e}")

    print(f"Tree Formation Complete: Registered {nodes_found} nodes in the Living Map.")
    return nodes_found

if __name__ == "__main__":
    run_tree_builder()