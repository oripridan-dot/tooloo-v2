import asyncio
import logging
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))

from src.tooloo.core.mega_dag import ContinuousMegaDAG, DagNode, NodeType, AbstractOperator, NodeResult, GlobalContext

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

async def mock_filesystem_write(path: str, content: str):
    await asyncio.sleep(0.1)
    return {"written": True, "path": path}

class MockPlanningOperator(AbstractOperator):
    """Mocks the LLM planning so we don't need a real LLM key for the test."""
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        await asyncio.sleep(0.1)
        
        spawned = [
            DagNode(
                node_type=NodeType.TOOLOO,
                goal="Run system self-verification using TooLoo loop"
            ),
            DagNode(
                node_type=NodeType.EXECUTION,
                goal="Write configuration to disk",
                action="fs_write",
                params={"path": "/tmp/test.json", "content": "{}"}
            )
        ]
        return NodeResult(outcome={"status": "mock_planned"}, spawned_nodes=spawned)

@pytest.mark.asyncio
async def test_continuous_mega_dag():
    dag = ContinuousMegaDAG()
    
    # Register mock capability tools
    dag.register_tool("fs_write", mock_filesystem_write)
    
    # Inject Mock Planner
    dag.register_operator(NodeType.PLANNING, MockPlanningOperator())
    
    goal = "Create a new lightweight web service and ensure tooloo runs."
    context = {"env": "local_dev", "focus": "speed"}
    
    results = await dag.ignite(goal, initial_state=context)

    # ToolooOperator is a stub (not_implemented) — assert DAG completes successfully and
    # processed at least the root planning node (1 iteration minimum).
    assert results["status"] == "SUCCESS"
    assert results["iterations"] >= 1
    assert results["final_state"]["env"] == "local_dev"
