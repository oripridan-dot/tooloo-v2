import asyncio
import logging
import sys
import os

# Environment Setup
sys.path.insert(0, os.getcwd())
logging.basicConfig(level=logging.INFO, format="%(message)s")

from tooloo_v3_hub.kernel.cognitive.pathway_b import get_pathway_manager

async def mock_executor(goal, context, strategy):
    # Simulate execution with varying latency
    # "Fast" takes less time, but has logic to differentiate its result
    if "Fast" in strategy["name"]:
        await asyncio.sleep(0.01)
    elif "Deep" in strategy["name"]:
        await asyncio.sleep(0.15)
    else:
        await asyncio.sleep(0.05)
        
    return {
        "status": "success", 
        "payload": {
            "stamp": {
                "who": "Audit", "what": "Test", "where": "Local", 
                "why": "Audit", "how": "Mock", "when": "Now"
            }
        }
    }

async def run_pathway_audit():
    print("\n" + "="*60)
    print("TOO LOO V3: PATHWAY B COMPETITIVE AUDIT")
    print("="*60)
    
    manager = get_pathway_manager()
    
    # We define 3 strategies with varying drift_bias
    # Scoring Algorithm: 10 + (latency * -0.001) + (6w_score * 1.0) + (drift * -2.0)
    strategies = [
        {"name": "Standard-Precision", "drift_bias": 0.3}, # Drift Score = -0.6
        {"name": "Fast-Response", "drift_bias": 0.8},     # Drift Score = -1.6 (Should lose)
        {"name": "Deep-Alignment", "drift_bias": 0.05}     # Drift Score = -0.1 (Should win)
    ]
    
    goal = "Implement Sovereign Resilience Loop"
    winner = await manager.resolve_competitive(goal, {}, strategies, mock_executor)
    
    print("\n" + "-"*30)
    print(f"Goal: {goal}")
    print("-"*30)
    
    for v in manager.variants:
        idx = v.id
        print(f"Variant: {v.name} ({v.id})")
        print(f"  Latency: {v.latency_ms:.2f}ms | 6W: {v.six_w_score:.2f} | Drift: {v.drift_score:.2f}")
        print(f"  Total Score: {v.total_score:.4f}")
        print("-"*10)

    print(f"\nWINNER: {winner.name} (Score: {winner.total_score:.4f})")
    
    if winner.name == "Deep-Alignment":
        print("\n✅ Pathway B Logic GROUNDED.")
    else:
        print(f"\n❌ AUDIT FAILURE: Incorrect winner resolved ({winner.name}).")

    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(run_pathway_audit())
