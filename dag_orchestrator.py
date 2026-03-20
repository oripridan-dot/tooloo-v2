from dag_nodes import DataIngestionNode, ProcessingNode, AnalysisNode, OutputNode

class DAGOrchestrator:
    def __init__(self):
        # Define DAG structure (nodes and dependencies)
        self.nodes = {
            "ingest_data": DataIngestionNode("ingest_data"),
            "process_data": ProcessingNode("process_data"),
            "analyze_data": AnalysisNode("analyze_data"),
            "generate_output": OutputNode("generate_output")
        }
        self.dependencies = {
            "ingest_data": [],
            "process_data": ["ingest_data"],
            "analyze_data": ["process_data"],
            "generate_output": ["analyze_data"]
        }
        self.execution_order = [
            "ingest_data",
            "process_data",
            "analyze_data",
            "generate_output"
        ] # Explicitly ordered for clarity, matching the 4 waves

    def run_pipeline(self):
        node_results = {}
        for node_id in self.execution_order:
            node = self.nodes[node_id]
            # Resolve dependencies: collect results from parent nodes
            parent_results = []
            for dep_id in self.dependencies[node_id]:
                if dep_id in node_results:
                    parent_results.append(node_results[dep_id])
                else:
                    # This should not happen in a correctly defined DAG
                    raise ValueError(f"Dependency {dep_id} not found for node {node_id}")
            
            # Execute node, passing parent results as arguments
            # This is a simplified argument passing mechanism; real scenarios might need more sophisticated mapping
            result = node.execute(*parent_results)
            node_results[node_id] = result
        print("DAG pipeline execution complete.")
