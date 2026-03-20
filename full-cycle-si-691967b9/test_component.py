import pytest
from full_cycle_si_691967b9.component import ResourceManager

def test_get_sensitive_data_unauthorized_access():
    resource_manager = ResourceManager()
    # Attempt to access sensitive data for a user who is NOT the owner of the resource
    # User 103 (Charlie) tries to access data for resource 1 (owned by 101)
    with pytest.raises(PermissionError):
        resource_manager.get_sensitive_data(user_id=103, resource_id=1)

def test_get_sensitive_data_authorized_access():
    resource_manager = ResourceManager()
    # Access sensitive data for a user who IS the owner of the resource
    # User 101 (Alice) accesses data for resource 1
    data = resource_manager.get_sensitive_data(user_id=101, resource_id=1)
    assert "secret_data" in data
    assert data["user_id"] == 101
    assert data["resource_id"] == 1
