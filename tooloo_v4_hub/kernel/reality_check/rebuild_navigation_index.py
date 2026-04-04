# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: rebuild_navigation_index.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/reality_check/rebuild_navigation_index.py
# WHEN: 2026-04-03T16:08:23.409530+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import logging
import sys
import os

# Environment Setup
sys.path.insert(0, os.getcwd())
logging.basicConfig(level=logging.INFO, format="%(message)s")

from tooloo_v4_hub.kernel.governance.navigation_index import get_navigation_index

def run_indexing_audit():
    print("\n" + "="*60)
    print("TOO LOO V3: NAVIGATION INDEXING PASS")
    print("="*60)
    
    idx = get_navigation_index()
    
    # Force rebuild
    print("Scanning Hub Kernel for 6W Metadata...")
    idx.build_index()
    
    # Load and stats
    idx.load_index()
    total = idx._cache.get("meta", {}).get("total_stamped_files", 0)
    domains = len(idx._cache.get("by_domain", {}))
    
    print(f"\nIndexed Files: {total}")
    print(f"Grounded Domains: {domains}")
    
    # Verify core grounding
    core_files = idx.search_by_domain("core")
    print(f"Core Logic Grounding: {len(core_files)} files.")
    
    print("\n" + "="*60)
    print("NAVIGATION INDEXING: READY")
    print("="*60)

if __name__ == "__main__":
    run_indexing_audit()
