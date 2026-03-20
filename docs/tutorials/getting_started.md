# TooLoo V2 Getting Started Tutorial

This tutorial guides you through the basic steps of using TooLoo V2 to build and run an autonomous cognitive pipeline.

## 1. Project Setup

Ensure you have a Python environment with TooLoo V2 installed. Your project structure should include:

```
my_tooloo_project/
├── engine/
│   └── config.py
├── processors/
│   └── __init__.py
│   └── data_processing.py
├── dag_definitions/
│   └── __init__.py
│   └── my_first_dag.py
└── main.py
```

## 2. Configure the Engine

Edit `engine/config.py` to set your desired configuration. For instance:

```python
# engine/config.py
from pydantic import BaseModel

class ToolooConfig(BaseModel):
    dag_execution_strategy: str = "sequential"
    max_concurrent_branches: int = 5
    log_level: str = "DEBUG"

def get_config() -> ToolooConfig:
    return ToolooConfig()
```

## 3. Define Processors

Create your stateless processor functions in the `processors/` directory. For example, `processors/data_processing.py`:

```python
# processors/data_processing.py
def fetch_sample_data(api_url: str) -> dict:
    """Fetches sample data from a given API."""
    print(f"Fetching data from {api_url}...")
    # Simulate API call
    return {"data": [1, 2, 3], "source": api_url}

def transform_data(input_data: dict) -> dict:
    """Transforms the input data."""
    print("Transforming data...")
    transformed = {"processed_items": [x * 2 for x in input_data.get("data", [])]}
    return transformed
```

## 4. Define Your DAG

Create a DAG definition file, e.g., `dag_definitions/my_first_dag.py`. Use the structure outlined in the DAG definition guide.

```python
# dag_definitions/my_first_dag.py
from typing import List, Dict, Any

class Task:
    id: str
    processor: str
    dependencies: List[str]
    args: Dict[str, Any]

class DAG:
    tasks: List[Task]

my_dag = DAG(
    tasks=[
        Task(
            id="fetch_data",
            processor="processors.data_processing.fetch_sample_data",
            dependencies=[],
            args={"api_url": "https://api.example.com/data"}
        ),
        Task(
            id="transform_data",
            processor="processors.data_processing.transform_data",
            dependencies=["fetch_data"],
            args={}
        )
    ]
)
```

## 5. Run the Pipeline

Create a `main.py` script to load and execute your DAG:

```python
# main.py
import importlib
from engine.config import get_config

def load_dag(module_name: str, dag_variable_name: str):
    """Dynamically loads a DAG object from a Python module."""
    try:
        module = importlib.import_module(module_name)
        dag = getattr(module, dag_variable_name)
        return dag
    except (ImportError, AttributeError) as e:
        print(f"Error loading DAG: {e}")
        return None

def main():
    config = get_config()
    print(f"Starting TooLoo V2 with strategy: {config.dag_execution_strategy}")

    # Load the DAG
    dag = load_dag("dag_definitions.my_first_dag", "my_dag")

    if dag:
        print(f"Loaded DAG with {len(dag.tasks)} tasks.")
        # In a real TooLoo engine, you would pass this DAG to the execution engine.
        # For this tutorial, we'll just print the task structure.
        for task in dag.tasks:
            print(f"- Task ID: {task.id}, Processor: {task.processor}, Dependencies: {task.dependencies}")
    else:
        print("Failed to load DAG.")

if __name__ == "__main__":
    main()
```

Run your `main.py` script:

```bash
python main.py
```

This tutorial covers the foundational aspects of building a TooLoo V2 pipeline. Refer to other documentation sections for advanced topics like error handling, observability, and complex DAG patterns.
