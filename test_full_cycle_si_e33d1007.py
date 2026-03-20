import pytest
from full_cycle_si_e33d1007 import process_data, InputData
from pydantic import ValidationError

def test_process_data_string():
    # Test with Pydantic validation
    with pytest.raises(TypeError):
        process_data("not a dict")
    assert process_data({"name": "value"}) == {"name": "VALUE"}

def test_process_data_int():
    assert process_data({"count": 10}) == {"count": 20}

def test_process_data_mixed():
    data = {"name": "test", "count": 5, "active": True}
    expected = {"name": "TEST", "count": 10, "active": True}
    assert process_data(data) == expected

def test_process_data_empty():
    assert process_data({}) == {}

def test_pydantic_validation_missing_field():
    with pytest.raises(ValidationError):
        InputData(count=10) # missing 'name' and 'active'

def test_pydantic_validation_invalid_type():
    with pytest.raises(ValidationError):
        InputData(name="test", count="not an int")
