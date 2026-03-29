# TooLoo V2 DAG Pipeline Architecture

TooLoo V2 operates as a Directed Acyclic Graph (DAG) of cognitive processes.

## Core Components

*   **Branches:** Represent individual execution units, each with a `BranchSpec` defining its `parent_branch_id`, `branch_type`, `intent`, `mandate`, and `target`.
*   **Nodes:** Each node in the DAG is defined by `PipelineNode`, specifying its unique `node_id`, the `processor` (e.g., a Python function or microservice) it executes, and its `inputs` and `outputs` schemas.
*   **DAG Specification:** The overall pipeline structure is defined by `DAGSpec`, which contains a dictionary of `nodes` and a dictionary of `edges`. Edges define the dependencies between nodes, specifying how outputs from one node connect to inputs of another.

## Execution Flow

The pipeline executes in a dataflow manner. Each node processes its inputs, generates outputs, and passes these outputs to subsequent nodes as defined by the DAG's edges. This ensures a controlled, deterministic execution order.

## SOTA Principles Applied

*   **Documentation:** The Diátaxis framework guides documentation structure (tutorials, how-tos, reference, explanation).
*   **Diagramming:** Mermaid.js v11 is utilized for inline diagrams, ensuring broad compatibility.
*   **Observability:** FastAPI + Pydantic v2 for async services, OpenTelemetry for distributed tracing, and structured JSON logging with correlation IDs are standard.
*   **Compliance:** LLM-generated runbooks require mandatory human review per SOX/ISO-27001.

## Data Models

All data structures adhere to Pydantic v2 for robust validation and clear schema definition.

```python
# core/dag.py
from pydantic import BaseModel
from typing import Dict, Any

class BranchSpec(BaseModel):
    parent_branch_id: str
    branch_type: str
    intent: str
    mandate: str
    target: str

class PipelineNode(BaseModel):
    node_id: str
    processor: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]

class DAGSpec(BaseModel):
    nodes: Dict[str, PipelineNode]
    edges: Dict[str, Dict[str, str]] # from_node -> to_node: output_key -> input_key
```
