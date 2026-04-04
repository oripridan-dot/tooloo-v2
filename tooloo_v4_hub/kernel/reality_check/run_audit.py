# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: run_audit.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/reality_check/run_audit.py
# WHEN: 2026-04-03T16:08:23.414125+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import os
import sys
import asyncio
import logging

# Set up logging to show everything clearly on stdout
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

# Ensure tooloo_v4_hub is in path (it's in the current working directory)
sys.path.insert(0, os.getcwd())

async def main():
    print("\n" + "="*60)
    print("PHASE 1: SOVEREIGN VALUE EVALUATION (ECOSYSTEM AUDIT)")
    print("="*60)
    
    try:
        from tooloo_v4_hub.tests.test_real_component_evaluation import test_component_goals
        await test_component_goals()
    except Exception as e:
        print(f"Value Evaluation Failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("PHASE 2: OUROBOROS STRUCTURAL DIAGNOSTIC (SELF-HEALING)")
    print("="*60)
    
    try:
        from tooloo_v4_hub.kernel.cognitive.ouroboros import get_ouroboros
        ouroboros = get_ouroboros()
        
        # Execute diagnostic and healing once
        await ouroboros.execute_self_play()
        
    except Exception as e:
        print(f"Ouroboros Execution Failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("AUDIT COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
