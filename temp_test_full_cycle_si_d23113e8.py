import pytest
from full_cycle_si_d23113e8 import ComponentInput, ComponentOutput, process_request

# Define a test case for successful processing
def test_process_request_success():
    input_data = ComponentInput(data={'key1': 'value1', 'key2': 123})
    output = process_request(input_data)
    assert isinstance(output, ComponentOutput)
    assert output.result['message'] == 'Processing complete'
    assert 'original_data_keys' in output.result
    assert set(output.result['original_data_keys']) == {'key1', 'key2'}

# Define a test case for empty input
def test_process_request_empty_input():
    input_data = ComponentInput(data={})
    output = process_request(input_data)
    assert isinstance(output, ComponentOutput)
    assert output.result['message'] == 'Processing complete'
    assert 'original_data_keys' in output.result
    assert output.result['original_data_keys'] == []

# Add more focused tests here based on potential vulnerabilities identified by SOTA signals.
# For example, tests for Broken Object-Level Authorization would require simulating
# different user contexts or access tokens, which are not yet defined in this simple component.
