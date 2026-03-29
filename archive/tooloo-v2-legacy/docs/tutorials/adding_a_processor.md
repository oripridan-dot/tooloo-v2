# Tutorial: Adding a New Processor

This tutorial explains how to create and integrate a new processor into your TooLoo V2 DAG.

## 1. Understand Processor Requirements

As detailed in the Processor Reference, processors must be:

*   **Stateless**: No instance variables or global state that persists across calls.
*   **Importable**: Accessible via a string path (e.g., `"my_module.my_function"`).

## 2. Create the Processor File

Let's say we want a processor that calculates the sum of a list of numbers. Create a new file, for example, `processors/calculations.py`.

```python
# processors/calculations.py
from typing import List

def sum_list(numbers: List[float]) -> float:
    """Calculates the sum of a list of numbers."""
    print(f"Calculating sum for: {numbers}")
    return sum(numbers)
```

## 3. Update DAG Definition

Now, modify your DAG definition file (`dag_definitions/my_first_dag.py` or a new one) to include a task that uses this new processor.

First, ensure your DAG definition class is available (it might be in a separate `dag_definitions/base.py` file or directly in the DAG file if simple):

```python
# dag_definitions/my_first_dag.py (or a new DAG file)
from typing import List, Dict, Any

class Task:
    id: str
    processor: str
    dependencies: List[str]
    args: Dict[str, Any]

class DAG:
    tasks: List[Task]

# Assuming you have a 'transform_data' task from previous steps,
# we'll add a new task that depends on it.
my_dag = DAG(
    tasks=[
        # ... (previous tasks like fetch_data, transform_data) ...
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
        ),
        Task(
            id="calculate_sum",
            processor="processors.calculations.sum_list", # <-- New processor
            dependencies=["transform_data"], # <-- Depends on transformed data
            args={"numbers": "{{ transform_data.output.processed_items }}"} # <-- Dynamic arg passing example
        )
    ]
)
```

**Note on Dynamic Arguments:** The `"{{ transform_data.output.processed_items }}"` syntax is a placeholder for how TooLoo might support dynamic argument passing, referencing the output of a previous task. The exact mechanism will depend on the execution engine's implementation.

## 4. Run the Pipeline

Execute your `main.py` script (or the script that loads and runs your DAG). The `calculate_sum` task will now be executed after `transform_data` completes, using its output as input.

Running `python main.py` should now reflect the new task in the execution flow.

This process demonstrates how easily new computational capabilities can be added to TooLoo V2 by defining new stateless processors and integrating them into DAGs.
