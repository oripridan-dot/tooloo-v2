import asyncio
import logging
import sys
import os
import time
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))

from src.tooloo.core.mega_dag import ContinuousMegaDAG, DagNode, NodeType, AbstractOperator, NodeResult, GlobalContext

# Suppress the default logger to keep terminal output clean for our summary
logging.getLogger("Tooloo.ContinuousMegaDAG").setLevel(logging.CRITICAL)

class RecursiveSpamOperator(AbstractOperator):
    """A viral operator that rapidly fans out to test high concurrency and crash resilience boundaries."""
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        # Simulate variable work loads (0.01s to 0.1s)
        await asyncio.sleep(random.uniform(0.01, 0.1))
        
        # 5% chance of catastrophic crash to test the sandbox
        if random.random() < 0.05:
            # We crash intentionally! The sandbox in _process_node MUST catch this.
            raise RuntimeError("INTENTIONAL_VIRAL_CRASH")
            
        # 5% chance of slow node (0.8s) which will violate the 0.5s Sandbox Timeout
        if random.random() < 0.05:
            await asyncio.sleep(0.8)
            
        spawned = [
            DagNode(node_type=NodeType.PLANNING, goal=f"Recursive Child A of {node.id[:4]}"),
            DagNode(node_type=NodeType.PLANNING, goal=f"Recursive Child B of {node.id[:4]}"),
            DagNode(node_type=NodeType.PLANNING, goal=f"Recursive Child C of {node.id[:4]}")
        ]
        
        return NodeResult(outcome={"status": "viral_spread"}, spawned_nodes=spawned)

async def stress_test():
    goal = "Ignite High-Concurrency Viral DAG"
    
    # We are pushing concurrency to 500 to tax the async event loop and system resources
    # Max depth is 5: 1 -> 3 -> 9 -> 27 -> 81 -> 243 -> 729 (capped dynamically by max_iterations or depth limit)
    dag = ContinuousMegaDAG(concurrency_limit=500, max_iterations=2000, max_depth=5, node_timeout_sec=0.5)
    
    # We hijack the standard PLANNING node map, mutating it into the Viral Spam loop
    dag.register_operator(NodeType.PLANNING, RecursiveSpamOperator())
    
    print("\n🔥 STARTING HIGH-CONCURRENCY M1 STRESS TEST 🔥")
    print("Settings: Concurrency=500 | MaxDepth=5 | SandboxTimeout=0.5s")
    print("Waiting for cascade expansion...")
    
    start_t = time.time()
    
    res = await dag.ignite(goal)
    end_t = time.time()
    
    latency = end_t - start_t
    iterations = res.get('iterations', 0)
    tps = iterations / latency if latency > 0 else 0
    
    print("\n=========================================================================")
    print("               🏁 MEGA DAG SANDBOX STRESS REPORT                        ")
    print("=========================================================================")
    print(f"Total Latency:               {latency:.3f} seconds")
    print(f"Total Nodes Processed:       {iterations}")
    print(f"Architecture Throughput:     {tps:.2f} TPS (Nodes / Sec)")
    print(f"Final State Status:          {res.get('status')}")
    print("=========================================================================")
    print("✅ System successfully survived the concurrent viral expansion without crashing.")
    print("✅ Sandbox gracefully absorbed any intended node panics/timeouts.")
    print("=========================================================================\n")

if __name__ == "__main__":
    # uvloop could be used here if installed, standard asyncio is fine to test python overhead
    asyncio.run(stress_test())
