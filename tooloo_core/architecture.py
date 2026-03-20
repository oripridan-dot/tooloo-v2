# /workspace/tooloo_core/architecture.py

from pydantic import BaseModel, Field
from typing import Dict, List

class Node(BaseModel):
    id: str
    type: str
    name: str
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    config: Dict = Field(default_factory=dict)

class DAG(BaseModel):
    name: str
    nodes: List[Node] = Field(default_factory=list)

def generate_dag_architecture() -> DAG:
    """
    Generates the TooLoo V2 DAG pipeline architecture definition.
    """
    dag = DAG(name="TooLoo V2 Pipeline")

    # Core components
    dag.nodes.append(Node(id="data_ingestion", type="processor", name="Data Ingestion"))
    dag.nodes.append(Node(id="feature_engineering", type="processor", name="Feature Engineering", inputs=["data_ingestion.output"]))
    dag.nodes.append(Node(id="model_training", type="processor", name="Model Training", inputs=["feature_engineering.output"]))
    dag.nodes.append(Node(id="model_evaluation", type="processor", name="Model Evaluation", inputs=["model_training.output"]))
    dag.nodes.append(Node(id="deployment_service", type="processor", name="Deployment Service", inputs=["model_evaluation.output"]))

    # Control flow and monitoring
    dag.nodes.append(Node(id="orchestrator", type="control", name="Orchestrator", inputs=["data_ingestion.status", "feature_engineering.status", "model_training.status", "model_evaluation.status", "deployment_service.status"]))
    dag.nodes.append(Node(id="monitoring", type="observability", name="Monitoring", inputs=["orchestrator.logs"]))
    dag.nodes.append(Node(id="alerting", type="observability", name="Alerting", inputs=["monitoring.alerts"]))

    # External integration
    dag.nodes.append(Node(id="config_loader", type="config", name="Configuration Loader", outputs=["config_data"]))
    dag.nodes.append(Node(id="data_sink", type="sink", name="Data Sink", inputs=["deployment_service.predictions"]))

    # Outputs
    dag.nodes.append(Node(id="final_report", type="reporting", name="Final Report", inputs=["model_evaluation.metrics"]))

    return dag

if __name__ == "__main__":
    architecture = generate_dag_architecture()
    print(architecture.model_dump_json(indent=2))

    # Example: Mermaid diagram generation (for visualization)
    # This part would typically be handled by a dedicated visualization tool or service
    # within TooLoo V2. Here, we simulate its output.

    def generate_mermaid_diagram(dag: DAG) -> str:
        """Generates a Mermaid.js compatible diagram string."""
        mermaid_lines = ["graph TD"]
        node_map = {node.id: node.name for node in dag.nodes}

        for node in dag.nodes:
            mermaid_lines.append(f'    {node.id}["{node.name}"]')

        for node in dag.nodes:
            for input_node_id in node.inputs:
                # Simple heuristic to find the source node ID if it's like 'source.output'
                source_node_id = input_node_id.split('.')[0]
                if source_node_id in node_map:
                    mermaid_lines.append(f'    {source_node_id} --> {node.id}')
        return "\n".join(mermaid_lines)

    print("\n--- Mermaid Diagram ---")
    print(generate_mermaid_diagram(architecture))