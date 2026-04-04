# 6W_STAMP
# WHO: TooLoo V4 (Buddy Sync)
# WHAT: SCRIPT_BUDDY_SYNC | Version: 1.0.0
# WHERE: scripts/buddy_sync.py
# WHY: Rule 16 Integration for Agent Manager
# HOW: Aggregating SOTABenchmarker results into Markdown
# ==========================================================

import asyncio
import json
import os
import time
from datetime import datetime
from tooloo_v4_hub.kernel.cognitive.north_star import get_north_star

async def run_sync():
    print("--- [BUDDY SYNC] Initiating Telemetry Harvesting ---")
    star = get_north_star()
    report = await star.recalibrate()
    
    # Determine Status
    status = "APPROVED" if report['svi'] >= 0.95 else "WARNING"
    if report['svi'] < 0.85:
        status = "FAILED"

    # Buddy Verdict Extraction (from North Star state or logic)
    verdict = ""
    if status == "APPROVED":
        verdict = "The system is pure. Execution permitted."
    elif status == "WARNING":
        verdict = f"Minor architectural drift detected ({report['purity']['purity_score']:.4f}). Proceed with caution."
    else:
        verdict = "CRITICAL FAILURE. ARCHITECTURAL PURITY BREACHED. HALT ALL NEW FEATURES."

    # Manifest the Audit Report
    sync_content = f"""# BUDDY AUDIT VERDICT: {status}
**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**SVI (Sovereign Vitality Index):** {report['svi']:.4f}

## Telemetry Data
- **Constitutional Purity:** {report['purity']['purity_score']:.4f} ({report['purity']['stamped_count']}/{report['purity']['total_nodes']} nodes)
- **Cognitive Latency:** {report['latency']['latency_ms']}ms (Score: {report['latency']['latency_score']:.4f})
- **Market Parity:** {report['market_parity']['parity_score']:.4f}

## Buddy's Verdict
> {verdict}

## Blockade Status
- **Crucible Security Check:** {"PASSED" if report['svi'] > 0.8 else "FAILED"}
- **Architectural Alignment:** {"ALIGNED" if report['purity']['purity_score'] > 0.9 else "DRIFTING"}

## Action Items
- [ ] Fix unstamped nodes: {', '.join(report['purity']['unstamped'][:5])}
"""
    
    with open("buddy_audit_latest.md", "w") as f:
        f.write(sync_content)
    
    print(f"--- [BUDDY SYNC] Manifested: buddy_audit_latest.md (Status: {status}) ---")

if __name__ == "__main__":
    asyncio.run(run_sync())
