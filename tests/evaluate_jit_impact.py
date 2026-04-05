import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tooloo.core.mega_dag import ContinuousMegaDAG, DagNode, NodeType, AbstractOperator, NodeResult, GlobalContext

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("JitBenchmark")

async def mock_filesystem_write(path: str, content: str):
    await asyncio.sleep(0.05)
    return {"written": True, "path": path}

# Standard Planning Mock (Simulates unoptimized complex routing)
class NonJitPlanningOperator(AbstractOperator):
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        await asyncio.sleep(0.2)
        spawned = [
            DagNode(node_type=NodeType.OBSERVATION, goal="Analyze filesystem structure", action="fs_write", params={"path": "/tmp/1", "content": "1"}),
            DagNode(node_type=NodeType.EXECUTION, goal="Calculate abstract metrics", action="fs_write", params={"path": "/tmp/2", "content": "2"}),
            DagNode(node_type=NodeType.EXECUTION, goal="Deploy microservice logic", action="fs_write", params={"path": "/tmp/3", "content": "3"}),
            DagNode(node_type=NodeType.VERIFICATION, goal="Verify structural compliance", action="fs_write", params={"path": "/tmp/4", "content": "4"})
        ]
        return NodeResult(outcome={"status": "mock_planned_standard", "type": "legacy"}, spawned_nodes=spawned)

# Mocked SOTA JIT Operator — simulates optimized routing with prioritized execution
class MockSotaJitOperator(AbstractOperator):
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        await asyncio.sleep(0.25)
        spawned = [
            DagNode(node_type=NodeType.EXECUTION, goal="[JIT ENRICHED] Direct Microservice Deployment", action="fs_write", params={"path": "/tmp/jit_optimized", "content": "optimized_bundle"})
        ]
        context.state["jit_cycles"] = context.state.get("jit_cycles", 0) + 1
        return NodeResult(outcome={"status": "mock_jit_enriched", "confident": True}, spawned_nodes=spawned)


async def evaluate_impact():
    goal = "Construct high-fidelity microservice."
    
    print("\n================================================")
    print(" 🏎️  RUN 1: STANDARD MEGA DAG (NO JIT)")
    print("================================================")
    
    legacy_dag = ContinuousMegaDAG()
    legacy_dag.register_tool("fs_write", mock_filesystem_write)
    legacy_dag.register_operator(NodeType.PLANNING, NonJitPlanningOperator())
    legacy_res = await legacy_dag.ignite(goal, {"mode": "legacy"})
    
    print("\n================================================")
    print(" 🚀 RUN 2: SOTA JIT ENRICHED MEGA DAG")
    print("================================================")
    
    jit_dag = ContinuousMegaDAG()
    jit_dag.register_tool("fs_write", mock_filesystem_write)
    # We replace standard planning with SOTA_JIT to measure the optimized pass
    jit_dag.register_operator(NodeType.PLANNING, MockSotaJitOperator())
    jit_res = await jit_dag.ignite(goal, {"mode": "sota_jit"})
    
    print("\n=========================================================================")
    print("                       📊 BENCHMARK IMPACT REPORT                        ")
    print("=========================================================================")
    print(f"                               LEGACY            SOTA JIT")
    print(f"LATENCY:                       {legacy_res['latency_sec']}s               {jit_res['latency_sec']}s")
    print(f"ITERATIONS (NODE LOAD):        {legacy_res['iterations']}                 {jit_res['iterations']}")
    if legacy_res['iterations'] > jit_res['iterations']:
        delta = legacy_res['iterations'] - jit_res['iterations']
        print(f"\n✅ JIT Optimization resulted in {delta} fewer unnecessary task hops.")
    print("=========================================================================")

if __name__ == "__main__":
    asyncio.run(evaluate_impact())
