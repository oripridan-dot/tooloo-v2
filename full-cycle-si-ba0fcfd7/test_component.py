import pytest
from full_cycle_si_ba0fcfd7.component import create_user, get_user, update_user, delete_user, list_of_users

# Reset mock data before each test to ensure isolation
@pytest.fixture(autouse=True)
def reset_users():
    global list_of_users
    list_of_users = [
        {"id": 1, "username": "alice", "email": "alice@example.com", "status": "active"},
        {"id": 2, "username": "bob", "email": "bob@example.com", "status": "inactive"},
    ]

def test_create_user():
    new_user = {"username": "charlie", "email": "charlie@example.com"}
    created = create_user(new_user)
    assert created["id"] == 3
    assert created["username"] == "charlie"
    assert len(list_of_users) == 3

def test_get_user_existing():
    user = get_user(1)
    assert user is not None
    assert user["username"] == "alice"

def test_get_user_nonexistent():
    user = get_user(99)
    assert user is None

def test_update_user_existing():
    updates = {"status": "pending"}
    updated_user = update_user(1, updates)
    assert updated_user["status"] == "pending"
    assert get_user(1)["status"] == "pending"

def test_update_user_nonexistent():
    updates = {"status": "pending"}
    updated_user = update_user(99, updates)
    assert updated_user is None

def test_delete_user_existing():
    deleted = delete_user(1)
    assert deleted is True
    assert get_user(1) is None
    assert len(list_of_users) == 1

def test_delete_user_nonexistent():
    deleted = delete_user(99)
    assert deleted is False
    assert len(list_of_users) == 2
