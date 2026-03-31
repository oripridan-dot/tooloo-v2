import asyncio
import os
import json
import logging
from tooloo_v3_hub.kernel.orchestrator import get_orchestrator
from tooloo_v3_hub.kernel.cognitive.predictive_trainer import get_predictive_trainer
from tooloo_v3_hub.kernel.cognitive.calibration import get_calibration_engine

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("TestTraining")

async def run_predictive_benchmark():
    print("\n" + "="*60)
    print("TOO LOO V3: PREDICTIVE TRAINING BENCHMARK")
    print("="*60)
    
    orchestrator = get_orchestrator()
    trainer = get_predictive_trainer()
    calibration = get_calibration_engine()
    
    # 1. Simulate NANO execution (Low complexity)
    print("\n[SCENARIO 1] Routine Logic Fix (NANO)")
    goal_1 = "Fix the syntax error in the helper function."
    context_1 = {"environment": "local"}
    res_1 = await orchestrator.execute_goal(goal_1, context_1)
    print(f"Receipt: {res_1[0].get('receipt')}")
    
    # 2. Simulate MACRO execution (High complexity + Security)
    print("\n[SCENARIO 2] Architectural Overhaul (MACRO)")
    goal_2 = "Industrialize the entire Hub with deep security and foresight."
    context_2 = {"environment": "gcp", "jit_boosted": True}
    res_2 = await orchestrator.execute_goal(goal_2, context_2)
    print(f"Receipt: {res_2[0].get('receipt')}")
    
    # 3. Perform a Focused Training Cycle (MESO)
    print("\n[SCENARIO 3] Meso-Scale Autonomous Training")
    print("Minimizing Emergence Delta across 3 rounds...")
    await trainer.run_training_cycle(scale="MESO", rounds=3)
    
    # 4. Verify Final Weight Convergence
    print("\n[SCENARIO 4] Verification of Weight Calibration")
    with open(calibration.bank_path, "r") as f:
        model = json.load(f)
        # Check first logic vector (idx 12)
        weight_val = model["w1"][12][0]
        print(f"Logic Weight [Index 12]: {weight_val:.4f}")
    
    print("\n" + "="*60)
    print("BENCHMARK COMPLETE: TooLoo is training on its own predictions.")
    print("="*60)

if __name__ == "__main__":
    try:
        asyncio.run(run_predictive_benchmark())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Test failed: {e}")
