# How to Define a DAG in TooLoo V2

This guide explains how to define a Directed Acyclic Graph (DAG) for TooLoo V2. DAGs specify the workflow, dependencies, and execution order of tasks.

## DAG Structure

A DAG is typically represented as a list of tasks, where each task has a unique identifier, a reference to a processor (a Python function or class), and a list of dependencies (identifiers of tasks that must complete before this task can start).

## Example DAG Definition (Python)

```python
from typing import List, Dict, Any

class Task:
    id: str
    processor: str  # e.g., "my_module.my_function"
    dependencies: List[str]
    args: Dict[str, Any]

class DAG:
    tasks: List[Task]

# Example DAG instance:
my_dag = DAG(
    tasks=[
        Task(id="task_a", processor="utils.fetch_data", dependencies=[], args={...}),
        Task(id="task_b", processor="utils.process_data", dependencies=["task_a"], args={...}),
        Task(id="task_c", processor="utils.generate_report", dependencies=["task_b"], args={...})
    ]
)
```

## Task Processors

Task processors are stateless Python functions or methods. They should be importable by their string identifier (e.g., `"my_module.my_function"`).

## Dependencies

The `dependencies` field specifies the `id` of tasks that must have successfully completed before the current task can begin execution.

## Configuration

DAG execution parameters, such as execution strategy (sequential/parallel) and concurrency limits, are defined in `engine/config.py`.
