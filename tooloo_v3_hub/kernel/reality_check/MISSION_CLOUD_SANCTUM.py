import asyncio
import logging
import os
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator

# Configure logging for 16-Rule Transparency
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("CloudSanctumMission")

async def execute_macro_deployment():
    """
    Rule 16: Live MACRO-scale Build Verification.
    Tests Phase-Aware routing by executing a real-world Cloud Deployment Mission.
    """
    logger.info("--- MACRO MISSION: CLOUD SANCTUM AWAKENING ---")
    
    orchestrator = get_orchestrator()
    
    # The Goal: Deploy the Hub to Cloud Run as a self-hosted Developer Sanctum.
    goal = "Deploy the TooLoo Sovereign Hub to Google Cloud Run (project: too-loo-zi8g7e) using a Phase-Aware Inverse DAG."
    
    # The Context: Real project ID and SOTA requirements.
    context = {
        "project_id": "too-loo-zi8g7e",
        "region": "us-central1",
        "environment": "cloud",
        "jit_boosted": True
    }
    
    logger.info(f"Galactic Node: Dispatching MACRO mission...")
    
    try:
        # We ensure the Orchestrator uses the real SOTA thinking for this build.
        # This will trigger the _decompose_inverse_dag thinking phase.
        results = await orchestrator.execute_goal(goal, context, mode="MACRO")
        
        logger.info("\n=== MISSION RECEIPT ===")
        receipt = results[0]["receipt"]
        print(f"Goal: {goal}")
        print(f"Predicted Emergence: {receipt['predicted_emergence']:.4f}")
        print(f"Actual Emergence: {receipt['actual_emergence']:.4f}")
        print(f"Audit Status: {receipt['audit_status']}")
        
        if receipt['actual_emergence'] > 0.8:
            logger.info("✅ SUCCESS: Cloud Sanctum Manifested via Phase-Aware Routing.")
        else:
            logger.warning("⚠️ PARTIAL SUCCESS: Mission completed but Emergence delta was high.")
            
    except Exception as e:
        logger.error(f"❌ MISSION CRITICAL FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(execute_macro_deployment())
