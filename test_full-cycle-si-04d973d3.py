# test_full-cycle-si-04d973d3.py

import pytest
from full_cycle_si_04d973d3 import process_data, validate_input_parameters


def test_process_data_valid_input():
    user_id = 123
    data = {
        'valid_key1': 'value1',
        'valid_key2': 123,
        'resource_id': 'resource-abc'
    }
    expected_output = {
        'valid_key1': 'value1',
        'valid_key2': 123,
        'user_id': 123
    }
    # Mocking is_resource_owner to always return True for this test case
    # In a real scenario, you might mock based on specific resource_id.
    import sys
    sys.modules["full_cycle_si_04d973d3"].is_resource_owner = lambda uid, rid: True

    result = process_data(user_id, data)
    assert result == expected_output


def test_process_data_invalid_user_id():
    with pytest.raises(ValueError, match="user_id must be a positive integer."):
        process_data(0, {'valid_key': 'value', 'resource_id': 'abc'})
    with pytest.raises(ValueError, match="user_id must be a positive integer."):
        process_data(-5, {'valid_key': 'value', 'resource_id': 'abc'})


def test_process_data_invalid_data_type():
    with pytest.raises(TypeError, match="data must be a dictionary."):
        process_data(456, "not a dict")


def test_process_data_unauthorized_access():
    user_id = 789
    data = {
        'valid_key': 'value',
        'resource_id': 'unauthorized-resource'
    }
    # Mocking is_resource_owner to return False for this specific resource_id
    import sys
    sys.modules["full_cycle_si_04d973d3"].is_resource_owner = lambda uid, rid: False

    with pytest.raises(PermissionError, match="User does not have permission to access this resource."):
        process_data(user_id, data)


def test_validate_input_parameters_valid():
    try:
        validate_input_parameters(1, {"resource_id": "abc"})
    except Exception as e:
        pytest.fail(f"Validation failed unexpectedly: {e}")


def test_validate_input_parameters_invalid_user_id():
    with pytest.raises(ValueError, match="user_id must be a positive integer."):
        validate_input_parameters(0, {"resource_id": "abc"})
    with pytest.raises(ValueError, match="user_id must be a positive integer."):
        validate_input_parameters(-1, {"resource_id": "abc"})

def test_validate_input_parameters_invalid_data_type():
    with pytest.raises(TypeError, match="data must be a dictionary."):
        validate_input_parameters(1, "not a dict")

