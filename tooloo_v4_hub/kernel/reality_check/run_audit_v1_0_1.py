# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_RUN_AUDIT.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/kernel/reality_check/run_audit.py
# WHEN: 2026-04-03T10:37:24.470035+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
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
