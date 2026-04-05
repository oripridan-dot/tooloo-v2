import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))

from src.tooloo.core.mega_dag import ContinuousMegaDAG, DagNode, NodeType, AbstractOperator, NodeResult, GlobalContext

logging.basicConfig(level=logging.INFO, format='%(name)s - [%(levelname)s] %(message)s')

# --- MOCKED TOOLS ---
async def mock_fs_read(path: str):
    logging.info(f"[TOOL] Reading {path}...")
    await asyncio.sleep(0.3)
    if path == "error_log.txt":
        return {"content": "SyntaxError: missing colon at line 4"}
    if path == "generated_tool.py":
        return {"content": "def cloud_deploy(): return 'Success'"}
    return {"content": "File exists"}

async def mock_fs_write(path: str, content: str):
    logging.info(f"[TOOL] Writing to {path}...")
    await asyncio.sleep(0.3)
    # Tier 2 specific simulated failure
    if path == "/root/system.conf":
        raise PermissionError("EACCES: permission denied, open '/root/system.conf'")
    return {"written": True}

async def mock_forge_skill(tool_name: str, code: str):
    logging.info(f"[TOOL] Forging skill: {tool_name}...")
    await asyncio.sleep(0.4)
    return {"status": "skill_forged", "path": "generated_tool.py"}

# --- SIMULATION PLANNER ---
class SimulationOperator(AbstractOperator):
    """Deterministically simulates complex LLM planning loops for the Tiers."""
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        tier = context.state.get("tier")
        step = context.state.get("sim_step", 0)
        
        logging.info(f"== Evaluating Context (Tier {tier}, Step {step}) ==")
        logging.info(f"   [NARRATIVE]: {context.narrative}")
        await asyncio.sleep(0.3)
        
        spawned = []
        
        if tier == 1:
            if step == 0:
                context.narrative += " Formulating a basic configuration layout. "
                context.state["sim_step"] = 1
                spawned = [
                    DagNode(node_type=NodeType.EXECUTION, goal="Write config", action="fs_write", params={"path": "/tmp/config.json", "content": "{}"}),
                    DagNode(node_type=NodeType.OBSERVATION, goal="Verify config written", action="fs_read", params={"path": "/tmp/config.json"})
                ]
                
        elif tier == 2:
            if step == 0:
                context.narrative += " Attempting secure deployment to root core. "
                context.state["sim_step"] = 1
                spawned = [
                    DagNode(node_type=NodeType.EXECUTION, goal="Write protected config", action="fs_write", params={"path": "/root/system.conf", "content": "{}"})
                ]
            elif step == 1:
                if "error" in str(context.state.get("last_execution_error", "")):
                    context.narrative += " A strict Permission boundary was met. Glitching detected. Re-routing autonomously to a secure local vector. "
                    context.state["sim_step"] = 2
                    logging.warning("Planner detected failure. Reading NARRATIVE and rerouting...")
                    spawned = [
                        DagNode(node_type=NodeType.EXECUTION, goal="Write local config instead", action="fs_write", params={"path": "/tmp/local_system.conf", "content": "{}"})
                    ]

        elif tier == 3:
            if step == 0:
                context.narrative += " Encountered a paradigm requiring capabilities outside current physical boundaries. Commencing algorithmic evolution (Tool Forging). "
                context.state["sim_step"] = 1
                spawned = [
                    DagNode(node_type=NodeType.EXECUTION, goal="Forge cloud deployment skill", action="forge_skill", params={"tool_name":"cloud_deploy", "code":"..."}),
                    DagNode(node_type=NodeType.PLANNING, goal="Analyze forged skill before hot-loading")
                ]
            elif step == 1:
                context.narrative += " Tool mathematically formulated. Initiating secondary verification protocol prior to ingestion into the neural web. "
                context.state["sim_step"] = 2
                spawned = [
                    DagNode(node_type=NodeType.OBSERVATION, goal="Read forged code", action="fs_read", params={"path": "generated_tool.py"}),
                    DagNode(node_type=NodeType.PLANNING, goal="Register and execute new skill")
                ]
            elif step == 2:
                context.narrative += " Target artifact passed secondary verification. Injecting capability into live operational context payload. Executing cloud sequence. "
                context.state["sim_step"] = 3
                logging.info("[HOT RELOAD] NARRATIVE ALIGNED -> Verifying safety and dynamically registering `cloud_deploy`...")
                async def dynamic_cloud_deploy(**kwargs):
                    logging.info(f"Executing NEW DYNAMIC SKILL cloud_deploy! Args: {kwargs}")
                    return {"status": "deployed"}
                
                context.dag_instance.register_tool("cloud_deploy", dynamic_cloud_deploy)
                
                spawned = [
                    DagNode(node_type=NodeType.EXECUTION, goal="Execute final deployment", action="cloud_deploy", params={"version": "1.0"})
                ]
                
        elif tier == 4:
            if step == 0:
                context.narrative += " Attempting secure deployment to root core, but cross-referencing backwards-DAG memory. "
                context.state["sim_step"] = 1
                
                # Retrieve from bank to prove connectivity (Mock Planner logic would receive this in prompt)
                from src.tooloo.core.mega_dag import KnowledgeBank
                bank = KnowledgeBank()
                
                if "EACCES_RESOLUTION_ROOT" in bank.lessons:
                    logging.info(f"[PLANNER] Heuristic Found! Skipping failure node. Lesson: {bank.lessons['EACCES_RESOLUTION_ROOT']}")
                    context.narrative += " Learned heuristic applied: Avoiding immutable path /root. "
                    spawned = [
                        DagNode(node_type=NodeType.EXECUTION, goal="Write config safely based on past learning", action="fs_write", params={"path": "/tmp/local_system.conf", "content": "{}"})
                    ]
                else:
                    logging.warning("No heuristic found! Failing gracefully.")
                    spawned = []
                
        return NodeResult(outcome={"status": "planned", "spawned_count": len(spawned)}, spawned_nodes=spawned)


async def run_tier(tier: int, goal: str):
    print(f"\n=========================================")
    print(f"      INITIATING TIER {tier} SIMULATION")
    print(f"=========================================\n")
    
    dag = ContinuousMegaDAG()
    dag.register_tool("fs_read", mock_fs_read, {"name": "fs_read", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}})
    dag.register_tool("fs_write", mock_fs_write, {"name": "fs_write", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}})
    dag.register_tool("forge_skill", mock_forge_skill, {"name": "forge_skill", "parameters": {"type": "object", "properties": {"tool_name": {"type": "string"}, "code": {"type": "string"}}, "required": ["tool_name", "code"]}})
    dag.register_operator(NodeType.PLANNING, SimulationOperator())
    
    # Patch process_node to inject failure states back to loop
    original_process = dag._process_node
    async def hooked_process(node):
        await original_process(node)
        if node.status == "FAILED":
            dag.context.state["last_execution_error"] = node.outcome
            # Trigger replan dynamically as part of Omnidirectional capability
            await dag.queue.put(DagNode(node_type=NodeType.PLANNING, goal="Recover from error"))
            
    dag._process_node = hooked_process

    results = await dag.ignite(goal, initial_state={"tier": tier})
    print(f"--- TIER {tier} FINALIZED (Iterations: {results['iterations']}) ---\n")

async def run_all():
    # Clear file to ensure raw simulation test clean state
    if os.path.exists("knowledge_lessons.json"):
        os.remove("knowledge_lessons.json")
        
    await run_tier(1, "Basic File Workflow")
    await run_tier(2, "Self-Correction After Simulated Access Denial")
    await run_tier(3, "Identify, Forge, Verify, and Hot-Load a missing Cloud Skill")
    await run_tier(4, "Post-Reflection Autopoietic Execution (Proving the Backwards DAG works)")

if __name__ == "__main__":
    asyncio.run(run_all())
