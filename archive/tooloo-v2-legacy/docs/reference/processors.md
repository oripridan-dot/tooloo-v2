# Processor Reference

Processors are the fundamental building blocks of TooLoo V2's DAGs. They represent individual, stateless computational steps.

## Definition

Processors are typically Python functions or methods. They must be: 

1.  **Stateless**: Processors should not maintain internal state between invocations. Any required state should be passed as arguments or retrieved from external, persistent storage.
2.  **Idempotent (where possible)**: For robustness, processors should ideally produce the same output given the same inputs, even if executed multiple times. This is not always strictly required but is a best practice.
3.  **Importable**: Processors must be importable by their fully qualified Python path string (e.g., `"my_module.sub_module.my_function"`).

## Example Processor (`processors/data_processing.py`)

```python
# processors/data_processing.py

def fetch_sample_data(api_url: str) -> dict:
    """Fetches sample data from a given API."""
    print(f"Fetching data from {api_url}...")
    # In a real scenario, this would involve an HTTP request.
    # For demonstration, we return static data.
    return {"data": [10, 20, 30], "source": api_url}

def transform_data(input_data: dict) -> dict:
    """Transforms the input data by doubling each item."""
    print("Transforming data...")
    processed_items = [item * 2 for item in input_data.get("data", [])]
    return {"processed_items": processed_items}

# Example of a processor that might have side effects (e.g., writing to a file)
# Note: Such processors should be carefully managed within the DAG.
def save_processed_data(processed_data: dict, output_path: str):
    """Saves processed data to a file."""
    print(f"Saving processed data to {output_path}...")
    import json
    with open(output_path, 'w') as f:
        json.dump(processed_data, f)
    print("Data saved successfully.")
```

## Processor Arguments

Arguments for processors are defined in the DAG task configuration (`args` field). The TooLoo execution engine will pass these arguments to the processor function when it is invoked.

## Error Handling

Processors should handle potential errors gracefully, either by returning specific error indicators or by raising exceptions that the TooLoo execution engine can catch and manage according to the DAG's error handling strategy.
