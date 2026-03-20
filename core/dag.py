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
