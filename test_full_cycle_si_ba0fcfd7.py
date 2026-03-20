import os
import pytest

# Mocking external dependencies

class MockExternalService:
    def call_external_service(self, user_id: int, data: dict) -> str:
        if user_id == 3 and 'simulate_error' in data:
            raise ConnectionError("Failed to connect to external service")
        return f"Mocked processed data for user {user_id} with payload: {data}"

# Apply mocks to the original module
import sys
# Assuming the module name is derived from the filename.
# If the actual module name differs, this needs adjustment.
module_name = 'full_cycle_si_ba0fcfd7'

# Dynamically import the module to patch it.
# This requires the module to be importable by its name.
# If it's run directly as a script, this part might need refinement.
try:
    import full_cycle_si_ba0fcfd7
except ImportError:
    # If the module isn't importable by name, we might need to add its directory to sys.path
    # or handle it differently if it's not designed to be imported.
    # For this example, we'll assume it's importable or can be patched in-place.
    pass


@pytest.fixture(autouse=True)
def mock_external_service_fixture():
    # This fixture replaces the actual call_external_service with a mock
    # We need to access the module dynamically and patch its function.
    # The exact mechanism might depend on how the original code imports/uses it.
    
    # Store original function
    original_function = None
    if hasattr(full_cycle_si_ba0fcfd7, 'call_external_service'):
        original_function = full_cycle_si_ba0fcfd7.call_external_service
        
    def mocked_service(user_id: int, data: dict) -> str:
        mock_service = MockExternalService()
        return mock_service.call_external_service(user_id, data)
    
    # Patch the function
    if hasattr(full_cycle_si_ba0fcfd7, 'call_external_service'):
        full_cycle_si_ba0fcfd7.call_external_service = mocked_service
    else:
        # If the function doesn't exist, this test might fail or need adjustment.
        # Log a warning or raise an error if expected.
        pass

    yield
    
    # Restore original function
    if original_function is not None and hasattr(full_cycle_si_ba0fcfd7, 'call_external_service'):
        full_cycle_si_ba0fcfd7.call_external_service = original_function



def test_process_data_success(mock_external_service_fixture):
    # Test case for successful data processing with valid user and data.
    # Expecting a successful response.
    response = full_cycle_si_ba0fcfd7.process_data(1, {"payload": "some data", "sensitive_info": "confidential"})
    assert response["status"] == "success"
    assert "Mocked processed data for user 1" in response["data"]

def test_process_data_invalid_user(mock_external_service_fixture):
    # Test case for an invalid user ID.
    # Expecting a PermissionError.
    with pytest.raises(PermissionError, match="Invalid user ID"):
        full_cycle_si_ba0fcfd7.process_data(5, {"payload": "some data"})

def test_process_data_unauthorized_sensitive_info(mock_external_service_fixture):
    # Test case for unauthorized access to sensitive information.
    # Expecting a PermissionError.
    with pytest.raises(PermissionError, match="Access denied to sensitive information"):
        full_cycle_si_ba0fcfd7.process_data(2, {"payload": "some data", "sensitive_info": "confidential"})

def test_process_data_external_service_error(mock_external_service_fixture):
    # Test case for an error originating from the external service.
    # Expecting a generic error message.
    response = full_cycle_si_ba0fcfd7.process_data(3, {"payload": "some data", "simulate_error": True})
    assert response["status"] == "error"
    assert response["message"] == "An internal error occurred."

def test_process_data_missing_sensitive_info_access(mock_external_service_fixture):
    # Test case where sensitive info is present but user lacks explicit access.
    # This is covered by test_process_data_unauthorized_sensitive_info, but explicit test for clarity.
    response = full_cycle_si_ba0fcfd7.process_data(2, {"payload": "normal data", "sensitive_info": "hidden"})
    assert response["status"] == "error"
    assert response["message"] == "An internal error occurred."

def test_process_data_authorized_sensitive_info(mock_external_service_fixture):
    # Test case for authorized access to sensitive information by user 1.
    response = full_cycle_si_ba0fcfd7.process_data(1, {"payload": "normal data", "sensitive_info": "hidden"})
    assert response["status"] == "success"
    assert "Mocked processed data for user 1" in response["data"]
