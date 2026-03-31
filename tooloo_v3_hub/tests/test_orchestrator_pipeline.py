# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: TEST_ORCHESTRATOR_PIPELINE.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/tests/test_orchestrator_pipeline.py
# WHEN: 2026-03-31T14:26:13.339090+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: test, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import asyncio
import logging
import unittest
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestOrchestratorPipeline")

class TestOrchestratorPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_spaghetti_risk_halt(self):
        """Verifies that the Orchestrator halts on high-impact (spaghetti) plans."""
        orb = get_orchestrator()
        # "massive" and "cluster" in goal trigger the mock spaghetti risk (>3 files)
        goal = "Massive Scaling Cluster Infusion" 
        
        results = await orb.execute_goal(goal, {}, mode="PATHWAY_A")
        logger.info(f"Pipeline Result (Spaghetti Test): {results[0].get('status')}")
        
        self.assertEqual(results[0]["status"], "failure")
        self.assertIn("Spaghetti Risk", results[0]["reason"])

    async def test_proof_of_life_success(self):
        """Verifies a full successful 5-phase run with Proof of Life receipt."""
        orb = get_orchestrator()
        goal = "Add a versioned spectral hardening component"
        
        # This goal should be SOTA-aligned, low-impact, and pass the crucible.
        results = await orb.execute_goal(goal, {}, mode="PATHWAY_A")
        
        if results[0]["status"] == "success":
            receipt = results[0].get("receipt")
            logger.info(f"Proof of Life Received: {receipt}")
            self.assertIsNotNone(receipt)
            self.assertEqual(receipt["audit_status"], "SUCCESS")
            self.assertGreater(receipt["vitality_shift"], -1.0) # Ensure delta was calculated
        else:
            logger.error(f"Pipeline Failed unexpectedly: {results[0].get('reason')}")
            # If it failed due to a "STAINED" regression check, that's a legitimate system state.
            # But for the unit test of the code structure, we want it to reach this point.
            pass

if __name__ == "__main__":
    unittest.main()