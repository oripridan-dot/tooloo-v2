#!/usr/bin/env python
import pytest
from typing import Dict, Any
from pydantic import BaseModel, Field
import os
import sys

# Ensure test modules are not imported directly
def ensure_test_isolation():
    # Placeholder for process isolation logic.
    # In a real scenario, this might involve setting up a new Python interpreter or subprocess.
    pass

ensure_test_isolation()

class InputData(BaseModel):
    name: str = Field(default="")
    count: int = Field(default=0)
    active: bool = Field(default=False)

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Processes input data and returns transformed data."""
    # Add basic input validation for Pydantic compatibility and security
    if not isinstance(data, dict):
        raise TypeError("Input must be a dictionary.")
    
    # Validate input data using Pydantic model
    input_model = InputData(**data)
    validated_data = input_model.model_dump()

    processed_data = {}
    for key, value in validated_data.items():
        if isinstance(value, str):
            processed_data[key] = value.upper()
        elif isinstance(value, int):
            processed_data[key] = value * 2
        else:
            processed_data[key] = value
    return processed_data

def main():
    sample_data = {"name": "test", "count": 5, "active": True}
    result = process_data(sample_data)
    print(result)

if __name__ == "__main__":
    main()
