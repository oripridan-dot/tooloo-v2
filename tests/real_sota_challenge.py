import asyncio
import logging
import sys

from src.tooloo.core.mega_dag import ContinuousMegaDAG, NodeType
from src.tooloo.tools.core_fs import DEFAULT_TOOLS
from src.tooloo.core.buddy import BuddyOperator

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Test.RealSOTAChallenge")

async def run_claude_review():
    logger.info("Initiating full Claude validation on Vertex AI MegaDAG...")
    
    dag = ContinuousMegaDAG(
        max_iterations=15, 
        max_depth=4, 
        node_timeout_sec=60.0,
        target_model="gemini-flash-latest"
    )
    
    # Register tools
    for tool_name, tool_config in DEFAULT_TOOLS.items():
        dag.register_tool(tool_name, tool_config["handler"], tool_config["schema"])
        
    dag.register_operator(NodeType.BUDDY, BuddyOperator())
    
    goal = (
        "Scan the tools and current path using observation. Then, using fs_write_report, "
        "write a highly intelligent and brutally honest review of the DAG's capabilities "
        "to a file called CLAUDIO_REVIEW.md in your current working directory."
    )
    
    logger.info(f"Goal: {goal}")
    res = await dag.ignite(goal, {"target_dir": ""})
    
    logger.info(f"Challenge Results: {res['status']}")
    logger.info(f"Iterations: {res['iterations']}")
    logger.info(f"Execution Latency: {res['latency_sec']}s")
    
    print("\n--- Final Contextual Story ---")
    print(dag.context.contextual_story)

if __name__ == "__main__":
    asyncio.run(run_claude_review())
