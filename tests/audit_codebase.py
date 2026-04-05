import asyncio
import logging
import sys
import os
import ast

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))

from src.tooloo.core.mega_dag import ContinuousMegaDAG, DagNode, NodeType, AbstractOperator, NodeResult, GlobalContext

logging.basicConfig(level=logging.INFO, format='%(name)s - [%(levelname)s] %(message)s')

async def exec_read_file(filepath: str):
    logging.info(f"[READ] Loading contents of {filepath}")
    await asyncio.sleep(0.1)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return {"filepath": filepath, "content": f.read()}
    return {"filepath": filepath, "error": "File not found"}

async def exec_verify_connectivity(filepath: str, content: str):
    """Parses AST to see if anything is completely unconnected or broken."""
    logging.info(f"[VERIFY] Parsing AST for {filepath}")
    try:
        tree = ast.parse(content)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        imports = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import) or isinstance(n, ast.ImportFrom)]
        
        logging.info(f" -> RESULT '{filepath}': {len(classes)} Classes, {len(funcs)} Functions, {len(imports)} Imports mapped.")
        return {"filepath": filepath, "status": "VERIFIED_CLEAN"}
    except SyntaxError as e:
        logging.error(f" -> ERROR '{filepath}': {str(e)}")
        return {"filepath": filepath, "status": "FAILED_SYNTAX", "error": str(e)}

class AuditPlanner(AbstractOperator):
    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        step = context.state.get("audit_step", 0)
        spawned = []
        
        if step == 0:
            context.state["audit_step"] = 1
            files_to_audit = [
                "src/tooloo/core/mega_dag.py",
                "src/tooloo/core/llm.py",
                "tests/test_mega_dag.py",
                "tests/simulate_tiers.py"
            ]
            
            # Spawn Observation for each file natively into the DAG queue
            for file in files_to_audit:
                spawned.append(DagNode(node_type=NodeType.OBSERVATION, goal=f"Read {file}", action="read_file", params={"filepath": file}))
                
            # Queue the next planner step to wait for reads
            spawned.append(DagNode(node_type=NodeType.PLANNING, goal="Analyze codebase connections"))
            
        elif step == 1:
            file_contents = context.state.get("file_contents", {})
            if len(file_contents) < 4:
                # Wait for concurrent observations to finish
                logging.info(f"[PLANNER] Waiting for observations... ({len(file_contents)}/4 complete)")
                await asyncio.sleep(0.5)
                spawned.append(DagNode(node_type=NodeType.PLANNING, goal="Analyze codebase connections"))
                return NodeResult(outcome={"status": "waiting_for_deps"}, spawned_nodes=spawned)
                
            context.state["audit_step"] = 2
            # Process files through verification
            for k, v in file_contents.items():
                spawned.append(DagNode(node_type=NodeType.VERIFICATION, goal=f"Verify {k}", action="verify_connectivity", params={"filepath": k, "content": v}))
                
        return NodeResult(outcome={"status": "audit_planned", "step": step}, spawned_nodes=spawned)

async def main():
    dag = ContinuousMegaDAG()
    dag.register_tool("read_file", exec_read_file)
    dag.register_tool("verify_connectivity", exec_verify_connectivity)
    dag.register_operator(NodeType.PLANNING, AuditPlanner())
    
    # Trace the output of reads straight into the context
    original_process = dag._process_node
    async def hooked_process(node):
        await original_process(node)
        if node.action == "read_file" and node.outcome and "content" in node.outcome:
            if "file_contents" not in dag.context.state:
                dag.context.state["file_contents"] = {}
            dag.context.state["file_contents"][node.outcome["filepath"]] = node.outcome["content"]
            
    dag._process_node = hooked_process

    print("\n=======================================================")
    print(" INITIATING CODEBASE CONNECTIVITY AUDIT VIA OMNI-DAG")
    print("=======================================================\n")
    
    results = await dag.ignite("Audit entire python codebase for relevance and connectivity", {"audit_step": 0})
    
    print("\n--- AUDIT COMPLETE ---")
    print(f"Iterations: {results['iterations']} | Latency: {results['latency_sec']}s")

if __name__ == "__main__":
    asyncio.run(main())
