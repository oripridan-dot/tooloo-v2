# `engine/config.py` Reference

This document details the configuration options for the TooLoo V2 engine, managed via Pydantic v2 models.

## `ToolooConfig` Model

```python
from pydantic import BaseModel

class ToolooConfig(BaseModel):
    """Configuration for the TooLoo V2 engine."""
    dag_execution_strategy: str = "sequential"
    max_concurrent_branches: int = 10
    log_level: str = "INFO"
```

*   **`dag_execution_strategy`**: Defines how the DAG is executed. Options may include `"sequential"` (tasks run one after another) or `"parallel"` (tasks with satisfied dependencies run concurrently). Default is `"sequential"`.
*   **`max_concurrent_branches`**: Sets the maximum number of parallel branches (tasks) that can run concurrently. This parameter is relevant when `dag_execution_strategy` is set to `"parallel"`. Default is `10`.
*   **`log_level`**: Controls the verbosity of the system logs. Accepts standard logging levels such as `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`. Default is `"INFO"`.

## Loading Configuration

Configuration is loaded at runtime. Ensure `engine/config.py` is present in the project root or accessible via the Python path.

```python
# Example of loading config in your application:
from engine.config import get_config

config = get_config()
print(f"DAG execution strategy: {config.dag_execution_strategy}")
```
