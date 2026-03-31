# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MODULE_LIVING_MAP | Version: 1.1.0
# WHERE: tooloo_v3_hub/kernel/governance/living_map.py
# WHEN: 2026-03-31T18:45:00.000000
# WHY: Single Source of Topography and Navigation Truth (Rule 1, 11)
# HOW: Relational Graph and Metadata Search Unity
# TIER: T3:architectural-purity
# DOMAINS: mapping, topography, navigation, governance, relational-graph
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from tooloo_v3_hub.kernel.governance.stamping import StampingEngine

logger = logging.getLogger("LivingMap")

MANIFEST_PATH = "tooloo_v3_hub/psyche_bank/system_manifest.json"

class LivingMap:
    """
    The dynamic topography and navigation interface for the Sovereign Hub.
    Unifies the relational graph (Matrix) with metadata search (Search).
    """

    def __init__(self, manifest_file: str = MANIFEST_PATH):
        self.manifest_path = Path(manifest_file)
        self.nodes: Dict[str, Any] = {}
        self.edges: List[Dict[str, str]] = []
        self._load_manifest()

    def _load_manifest(self):
        """Loads the relational graph from the psyche bank."""
        if self.manifest_path.exists():
            try:
                data = json.loads(self.manifest_path.read_text())
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", [])
                logger.info(f"Living Map loaded: {len(self.nodes)} nodes registered.")
            except: 
                logger.error("Failed to load System Manifest. Architectural drift detected.")
        else:
            self.nodes = {}
            self.edges = []

    def _save_manifest(self):
        """Persists the Living Map to the psyche bank."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "meta": {
                "last_sync": time.time(),
                "version": "1.1.0",
                "purity": 1.0,
                "status": "UNIFIED"
            },
            "nodes": self.nodes,
            "edges": self.edges
        }
        self.manifest_path.write_text(json.dumps(data, indent=2))

    def rebuild_topography(self, root_dir: str = "tooloo_v3_hub"):
        """Performs a global scan to rebuild the Hub topography from 6W stamps."""
        logger.info(f"LivingMap: Rebuilding topography for {root_dir}...")
        root = Path(root_dir)
        new_nodes = {}
        
        for file in root.rglob("*"):
            if not file.is_file() or file.suffix not in [".py", ".html", ".js", ".css", ".ts"]:
                continue
                
            try:
                content = file.read_text(errors="ignore")
                metadata = StampingEngine.extract_metadata(content)
                if metadata:
                    node_id = str(file)
                    new_nodes[node_id] = {
                        "id": node_id,
                        "type": self._determine_type(node_id),
                        "status": "Active",
                        "metadata": metadata,
                        "version": metadata.get("version", "1.0.0")
                    }
            except: pass
            
        self.nodes = new_nodes
        logger.info(f"LivingMap: Hub topography rebuilt. {len(self.nodes)} components mapped.")
        self._save_manifest()

    def register_node(self, path: str, metadata: Dict[str, Any], dependencies: List[str] = []):
        """Atomic registration of a new or modified component."""
        node_id = str(path)
        self.nodes[node_id] = {
            "id": node_id,
            "type": self._determine_type(node_id),
            "status": "Active",
            "metadata": metadata,
            "version": metadata.get("version", "1.0.0")
        }
        # Update dependencies (Matrix)
        self.edges = [e for e in self.edges if e["source"] != node_id]
        for target in dependencies:
            self.edges.append({"source": node_id, "target": target, "relation": "depends_on"})
        self._save_manifest()

    def query_capabilities(self, inquiry: str) -> List[Dict[str, Any]]:
        """Searches for existing components satisfying a capability requirement."""
        results = []
        inq_l = inquiry.lower()
        for node in self.nodes.values():
            meta_str = str(node.get("metadata", {})).lower()
            if inq_l in meta_str or inq_l in node["id"].lower():
                results.append(node)
        return results

    def _determine_type(self, path: str) -> str:
        if "kernel" in path: return "kernel"
        if "cognitive" in path: return "cognitive"
        if "organs" in path: return "organ"
        if "tools" in path: return "tool"
        if "tests" in path: return "test"
        return "component"

_living_map = None

def get_living_map() -> LivingMap:
    global _living_map
    if _living_map is None:
        _living_map = LivingMap()
    return _living_map