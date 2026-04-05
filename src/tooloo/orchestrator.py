import asyncio
import logging
import sys
import os
import argparse

from src.tooloo.core.mega_dag import ContinuousMegaDAG, NodeType
from src.tooloo.tools.core_fs import DEFAULT_TOOLS
from src.tooloo.core.buddy import BuddyOperator

# Ensure logging goes to stderr so it doesn't break MCP stdio if running in MCP mode
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s', stream=sys.stderr)
logger = logging.getLogger("Tooloo.Orchestrator")

async def ignite_production_hub(mcp_mode: bool = False, goal: str = ""):
    if not goal:
        goal = (
            "Recursively observe the files in your /tmp/tooloo_sandbox environment (you may need to write some files first to establish the environment if empty). "
            "Apply your SOTA JIT web knowledge to audit the capabilities of your sandboxed filesystem securely against RULE 0 (Brutal Honesty / Systemic clarity). "
            "Consolidate all brutally honest findings by outputting them via `fs_write_report` to `RULE0_CORE_AUDIT.md`. "
        )
    
    # We initialize the DAG and manually load the production schema-bound tools.
    dag = ContinuousMegaDAG(max_iterations=60, max_depth=6, node_timeout_sec=45.0)
    
    logger.info("Initializing Sandbox Hub...")
    for tool_name, tool_config in DEFAULT_TOOLS.items():
        dag.register_tool(tool_name, tool_config["handler"], tool_config["schema"])
        logger.info(f"Registered Secure Sandbox capability -> [ {tool_name} ]")
        
    # Register the new Native Co-Operator Buddy
    dag.register_operator(NodeType.BUDDY, BuddyOperator())
    logger.info("Registered Co-Operator -> [ Buddy ] (Weaving Contextual Story)")
        
    logger.info("🔥 Igniting LIVE Gemini 2.5 Flash Zero-Trust Orchestrator 🔥")
    
    if mcp_mode:
        from src.tooloo.core.chat import run_mcp_chat_server
        dag_task = asyncio.create_task(dag.ignite(goal, {"target_dir": ""}))
        await run_mcp_chat_server(dag)
        await dag_task
    else:
        res = await dag.ignite(goal, {"target_dir": ""})
        
        logger.info(f"Hub Execution Complete: {res['status']}")
        logger.info(f"Nodes executed: {res['iterations']}")
        logger.info(f"Latency: {res['latency_sec']}s")
        logger.info(f"Final Contextual Story:\n{dag.context.contextual_story}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tooloo Sovereign Orchestrator")
    parser.add_argument("--mcp", action="store_true", help="Run the Chat MCP Server over stdio instead of standard exit")
    parser.add_argument("--goal", type=str, default="", help="The mission goal to ignite the DAG with. Defaults to the RULE0 audit.")
    args = parser.parse_args()

    asyncio.run(ignite_production_hub(mcp_mode=args.mcp, goal=args.goal))
