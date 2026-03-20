import pytest
from unittest.mock import MagicMock

# Assuming full_cycle_si_8fc01eae.py is in the same directory or PYTHONPATH is set
# If not, adjust the import path accordingly
from full_cycle_si_8fc01eae import SIWorkflow


@pytest.fixture
def mock_api_client():
    return MagicMock()


def test_si_workflow_compliant(mock_api_client):
    api_client = mock_api_client

    # Mocking dependencies
    api_client.log = MagicMock()
    mock_service = MagicMock()
    mock_model = MagicMock()
    mock_database = MagicMock()
    mock_exceptions = MagicMock()

    # Patching the SIWorkflow class's internal components for testing
    # This is a simplified approach. In a more complex scenario, one might inject mocks.
    # For this example, we assume SIWorkflow can be instantiated and its attributes can be mocked/patched.
    workflow = SIWorkflow(api_client)
    workflow.service = mock_service
    workflow.model = mock_model
    workflow.database = mock_database
    workflow.exceptions = mock_exceptions

    # Mocking the behavior for a compliant scenario
    mock_model.validate_request.return_value = True
    mock_database.get_policy.return_value = {"id": "policy1", "rules": []}
    mock_database.get_resource.return_value = {"id": "resource1", "attributes": {}}
    mock_model.is_relevant_event.return_value = True
    mock_service.evaluate_policy.return_value = {"compliant": True}

    request = {"policy_id": "policy1", "resource_id": "resource1", "event_type": "create"}

    result = workflow.run_workflow(request)

    assert result["status"] == "compliant"
    api_client.log.assert_any_call("INFO", f"Received SI workflow request: {request}")
    mock_model.validate_request.assert_called_once_with(request)
    mock_database.get_policy.assert_called_once_with("policy1")
    mock_database.get_resource.assert_called_once_with("resource1")
    mock_model.is_relevant_event.assert_called_once_with({"id": "policy1", "rules": []}, "create")
    mock_service.evaluate_policy.assert_called_once_with({"id": "policy1", "rules": []}, {"id": "resource1", "attributes": {}}, request)


def test_si_workflow_violated(mock_api_client):
    api_client = mock_api_client
    workflow = SIWorkflow(api_client)

    # Mocking dependencies similarly to the compliant test
    mock_service = MagicMock()
    mock_model = MagicMock()
    mock_database = MagicMock()
    mock_exceptions = MagicMock()
    workflow.service = mock_service
    workflow.model = mock_model
    workflow.database = mock_database
    workflow.exceptions = mock_exceptions
    api_client.log = MagicMock()

    # Mocking the behavior for a violated scenario
    mock_model.validate_request.return_value = True
    mock_database.get_policy.return_value = {"id": "policy1", "rules": []}
    mock_database.get_resource.return_value = {"id": "resource1", "attributes": {}}
    mock_model.is_relevant_event.return_value = True
    mock_service.evaluate_policy.return_value = {"compliant": False}
    mock_service.get_remediation_actions.return_value = ["action1", "action2"]

    request = {"policy_id": "policy1", "resource_id": "resource1", "event_type": "update"}

    result = workflow.run_workflow(request)

    assert result["status"] == "violated"
    assert result["remediation_actions"] == ["action1", "action2"]
    mock_service.get_remediation_actions.assert_called_once_with({"id": "policy1", "rules": []}, {"id": "resource1", "attributes": {}}, request)

def test_si_workflow_invalid_request(mock_api_client):
    api_client = mock_api_client
    workflow = SIWorkflow(api_client)

    # Mocking dependencies
    mock_service = MagicMock()
    mock_model = MagicMock()
    mock_database = MagicMock()
    mock_exceptions = MagicMock()
    workflow.service = mock_service
    workflow.model = mock_model
    workflow.database = mock_database
    workflow.exceptions = mock_exceptions
    api_client.log = MagicMock()

    # Mocking the behavior for an invalid request
    mock_model.validate_request.return_value = False
    mock_exceptions.InvalidRequestError = Exception # Temporarily override mock exception for this test

    request = {"policy_id": "policy1", "resource_id": "resource1", "event_type": "create"}

    result = workflow.run_workflow(request)

    assert result["status"] == "error"
    assert "Invalid request payload." in result["message"]
    mock_model.validate_request.assert_called_once_with(request)
    # Ensure other calls that depend on validation are not made
    mock_database.get_policy.assert_not_called()

    # Restore original mock exception
    mock_exceptions.InvalidRequestError = mock_exceptions.InvalidRequestError

def test_si_workflow_policy_not_found(mock_api_client):
    api_client = mock_api_client
    workflow = SIWorkflow(api_client)

    # Mocking dependencies
    mock_service = MagicMock()
    mock_model = MagicMock()
    mock_database = MagicMock()
    mock_exceptions = MagicMock()
    workflow.service = mock_service
    workflow.model = mock_model
    workflow.database = mock_database
    workflow.exceptions = mock_exceptions
    api_client.log = MagicMock()

    # Mocking the behavior for policy not found
    mock_model.validate_request.return_value = True
    mock_database.get_policy.return_value = None
    mock_exceptions.NotFoundError = Exception # Temporarily override mock exception

    request = {"policy_id": "nonexistent_policy", "resource_id": "resource1", "event_type": "create"}

    result = workflow.run_workflow(request)

    assert result["status"] == "error"
    assert "Policy not found." in result["message"]
    mock_database.get_policy.assert_called_once_with("nonexistent_policy")
    # Ensure subsequent calls are not made
    mock_database.get_resource.assert_not_called()

    # Restore original mock exception
    mock_exceptions.NotFoundError = mock_exceptions.NotFoundError

def test_si_workflow_resource_not_found(mock_api_client):
    api_client = mock_api_client
    workflow = SIWorkflow(api_client)

    # Mocking dependencies
    mock_service = MagicMock()
    mock_model = MagicMock()
    mock_database = MagicMock()
    mock_exceptions = MagicMock()
    workflow.service = mock_service
    workflow.model = mock_model
    workflow.database = mock_database
    workflow.exceptions = mock_exceptions
    api_client.log = MagicMock()

    # Mocking the behavior for resource not found
    mock_model.validate_request.return_value = True
    mock_database.get_policy.return_value = {"id": "policy1", "rules": []}
    mock_database.get_resource.return_value = None
    mock_exceptions.NotFoundError = Exception # Temporarily override mock exception

    request = {"policy_id": "policy1", "resource_id": "nonexistent_resource", "event_type": "create"}

    result = workflow.run_workflow(request)

    assert result["status"] == "error"
    assert "Resource not found." in result["message"]
    mock_database.get_policy.assert_called_once_with("policy1")
    mock_database.get_resource.assert_called_once_with("nonexistent_resource")
    # Ensure subsequent calls are not made
    mock_model.is_relevant_event.assert_not_called()

    # Restore original mock exception
    mock_exceptions.NotFoundError = mock_exceptions.NotFoundError

def test_si_workflow_irrelevant_event(mock_api_client):
    api_client = mock_api_client
    workflow = SIWorkflow(api_client)

    # Mocking dependencies
    mock_service = MagicMock()
    mock_model = MagicMock()
    mock_database = MagicMock()
    mock_exceptions = MagicMock()
    workflow.service = mock_service
    workflow.model = mock_model
    workflow.database = mock_database
    workflow.exceptions = mock_exceptions
    api_client.log = MagicMock()

    # Mocking the behavior for an irrelevant event
    mock_model.validate_request.return_value = True
    mock_database.get_policy.return_value = {"id": "policy1", "rules": []}
    mock_database.get_resource.return_value = {"id": "resource1", "attributes": {}}
    mock_model.is_relevant_event.return_value = False

    request = {"policy_id": "policy1", "resource_id": "resource1", "event_type": "delete"}

    result = workflow.run_workflow(request)

    assert result["status"] == "skipped"
    assert result["message"] == "Event type not relevant to policy."
    mock_model.is_relevant_event.assert_called_once_with({"id": "policy1", "rules": []}, "delete")
    # Ensure policy evaluation is not triggered
    mock_service.evaluate_policy.assert_not_called()

def test_si_workflow_unexpected_error(mock_api_client):
    api_client = mock_api_client
    workflow = SIWorkflow(api_client)

    # Mocking dependencies
    mock_service = MagicMock()
    mock_model = MagicMock()
    mock_database = MagicMock()
    mock_exceptions = MagicMock()
    workflow.service = mock_service
    workflow.model = mock_model
    workflow.database = mock_database
    workflow.exceptions = mock_exceptions
    api_client.log = MagicMock()

    # Mocking an unexpected error during policy evaluation
    mock_model.validate_request.return_value = True
    mock_database.get_policy.return_value = {"id": "policy1", "rules": []}
    mock_database.get_resource.return_value = {"id": "resource1", "attributes": {}}
    mock_model.is_relevant_event.return_value = True
    mock_service.evaluate_policy.side_effect = Exception("Simulated unexpected error")

    request = {"policy_id": "policy1", "resource_id": "resource1", "event_type": "create"}

    result = workflow.run_workflow(request)

    assert result["status"] == "error"
    assert "An internal server error occurred." in result["message"]
    mock_service.evaluate_policy.assert_called_once_with({"id": "policy1", "rules": []}, {"id": "resource1", "attributes": {}}, request)
    # Ensure subsequent remediation actions are not attempted
    mock_service.get_remediation_actions.assert_not_called()
