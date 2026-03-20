# test_full_cycle_si_d874c9dc.py

import pytest
from full_cycle_si_d874c9dc import process_data, DataProcessor
import logging

# Mocking logging to prevent interference with test output
@pytest.fixture(autouse=True)
def mock_logger(monkeypatch):
    mock_log = logging.getLogger("__main__")
    mock_log.info = lambda msg, *args, **kwargs: None
    mock_log.error = lambda msg, *args, **kwargs: None
    mock_log.exception = lambda msg, *args, **kwargs: None
    return mock_log


def test_process_data_success():
    """Test successful data processing."""
    input_data = {"id": "1", "payload": "test_payload"}
    expected_output = input_data.copy()
    expected_output.update({"status": "processed"})
    
    # Check if timestamp is present and is a number
    result = process_data(input_data)
    assert result["status"] == "processed"
    assert isinstance(result["timestamp"], float)
    assert result["id"] == "1"
    assert result["payload"] == "test_payload"

def test_process_data_error_condition():
    """Test data processing with an explicit error condition."""
    input_data = {"id": "2", "payload": "error_payload", "error_condition": True}
    with pytest.raises(ValueError, match="Simulated processing error"):
        process_data(input_data)

def test_data_processor_init():
    """Test DataProcessor initialization."""
    config = {"retries": 5}
    processor = DataProcessor(config)
    assert processor.config == config

def test_data_processor_run_cycle_success():
    """Test DataProcessor run_cycle method success."""
    config = {"timeout": 60}
    processor = DataProcessor(config)
    input_data = {"id": "3", "payload": "cycle_payload"}
    
    result = processor.run_cycle(input_data)
    
    assert result["status"] == "processed"
    assert isinstance(result["timestamp"], float)
    assert result["id"] == "3"
    assert result["payload"] == "cycle_payload"

def test_data_processor_run_cycle_error():
    """Test DataProcessor run_cycle method when process_data raises an error."""
    config = {"timeout": 60}
    processor = DataProcessor(config)
    input_data = {"id": "4", "payload": "cycle_error_payload", "error_condition": True}
    
    with pytest.raises(ValueError, match="Simulated processing error"):
        processor.run_cycle(input_data)

# Consider adding tests for: 
# - Edge cases in input data types/formats
# - Longer payloads or IDs
# - Interaction with external systems (if applicable in a real scenario)
# - Configuration validation within DataProcessor
