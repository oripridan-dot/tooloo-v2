# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining test_billing_bypass.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.393980
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import asyncio
import sys
from pathlib import Path
import numpy as np

# Add root directory to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from engine.tribunal import Tribunal, TribunalVerdict
from engine.engram import Engram, Context6W, Intent16D

async def test_rule_4_bypass():
    print("--- CLAUDIO SOTA; RULE 4 BILLING BYPASS VERIFICATION ---")
    
    tribunal = Tribunal(threshold=0.05)
    
    # 1. Create a valid engram
    context = Context6W(
        what="Infrastructure Update", 
        where="cloud", 
        who="architect", 
        how="gcloud", 
        why="Hardening"
    )
    intent = Intent16D(values={"ROI": 1.0, "Efficiency": 0.9})
    engram = Engram(context=context, intent=intent)
    
    # 2. Simulate a GCP Tool call
    tool_call = "mcp_cloudrun_list_services"
    print(f"[TEST] Triggering tool call: {tool_call}")
    
    # Evaluate with the bridge
    result = await tribunal.evaluate(engram, tool_call=tool_call)
    
    print(f"Verdict: {result.verdict.value}")
    print(f"Violations/Flags: {result.violations}")
    
    if result.verdict == TribunalVerdict.STABLE_SUCCESS and "RULE_4_EXEMPT" in result.violations:
        print("Status: SUCCESS (Billing Exemption Active)")
    else:
        print("Status: FAILURE (Bypass failed)")

if __name__ == "__main__":
    asyncio.run(test_rule_4_bypass())
