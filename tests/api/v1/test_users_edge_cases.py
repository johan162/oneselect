"""Edge case tests for user endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_list_users_without_superuser_privileges(client: TestClient) -> None:
    """Test listing users as regular user."""
    # Create and login as regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "regularlistuser",
        "email": "regularlist@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "regularlistuser", "password123")

    r = client.get(f"{settings.API_V1_STR}/users/", headers=regular_headers)
    assert r.status_code == 400  # Doesn't have enough privileges


def test_list_users_without_authentication(client: TestClient) -> None:
    """Test listing users without auth token."""
    r = client.get(f"{settings.API_V1_STR}/users/")
    assert r.status_code == 401


def test_list_users_with_negative_skip(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test pagination with negative skip value."""
    r = client.get(
        f"{settings.API_V1_STR}/users/?skip=-5",
        headers=superuser_token_headers,
    )
    # Should either default to 0 or return validation error
    assert r.status_code in [200, 422]


def test_list_users_with_excessive_limit(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test pagination with very large limit."""
    r = client.get(
        f"{settings.API_V1_STR}/users/?limit=100000",
        headers=superuser_token_headers,
    )
    # Should cap at max value or succeed
    assert r.status_code == 200


def test_create_user_without_superuser_privileges(client: TestClient) -> None:
    """Test creating user as regular user."""
    # Create and login as regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "regularcreateuser",
        "email": "regularcreate@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "regularcreateuser", "password123")

    new_user_data = {
        "username": "attempteduser",
        "email": "attempted@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=regular_headers,
        json=new_user_data,
    )
    assert r.status_code == 400


def test_create_user_with_missing_required_fields(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test creating user without required fields."""
    # Missing username
    user_data = {
        "email": "missingusername@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    assert r.status_code == 422

    # Missing password
    user_data = {
        "username": "missingpassword",
        "email": "missingpassword@example.com",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    assert r.status_code == 422


def test_read_user_by_nonexistent_id(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test reading user with non-existent ID."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(
        f"{settings.API_V1_STR}/users/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_read_user_by_malformed_id(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test reading user with invalid UUID format."""
    r = client.get(
        f"{settings.API_V1_STR}/users/not-a-uuid",
        headers=superuser_token_headers,
    )
    # Returns 404 as malformed UUID won't match any user
    assert r.status_code == 404


def test_read_other_user_without_superuser_privileges(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test reading another user's details as regular user."""
    # Create first user
    user1_data = {
        "username": "user1read",
        "email": "user1read@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user1_data,
    )
    user1_id = r.json()["id"]

    # Create and login as second user
    from tests.utils.utils import get_user_token_headers

    user2_data = {
        "username": "user2read",
        "email": "user2read@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user2_data)
    user2_headers = get_user_token_headers(client, "user2read", "password123")

    # Try to read user1's details
    r = client.get(
        f"{settings.API_V1_STR}/users/{user1_id}",
        headers=user2_headers,
    )
    assert r.status_code == 400


def test_update_user_without_superuser_privileges(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating user as regular user."""
    # Create a user
    user_data = {
        "username": "updatetarget",
        "email": "updatetarget@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    # Try to update as regular user
    from tests.utils.utils import get_user_token_headers

    regular_user_data = {
        "username": "regularupdate",
        "email": "regularupdate@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=regular_user_data)
    regular_headers = get_user_token_headers(client, "regularupdate", "password123")

    update_data = {"email": "hacked@example.com"}
    r = client.put(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=regular_headers,
        json=update_data,
    )
    assert r.status_code == 400


def test_update_nonexistent_user(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating user that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    update_data = {"email": "newemail@example.com"}
    r = client.put(
        f"{settings.API_V1_STR}/users/{fake_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 404


def test_update_user_with_invalid_data_types(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating user with wrong data types."""
    # Create a user
    user_data = {
        "username": "typetestuser",
        "email": "typetest@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    # Try to update with is_active as string instead of boolean
    update_data = {"is_active": "yes"}
    r = client.put(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    # Pydantic may coerce "yes" to true, or reject it
    assert r.status_code in [200, 422]


def test_delete_user_without_superuser_privileges(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test deleting user as regular user."""
    # Create a user to delete
    user_data = {
        "username": "deletetarget",
        "email": "deletetarget@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    # Try to delete as regular user
    from tests.utils.utils import get_user_token_headers

    regular_user_data = {
        "username": "regulardelete",
        "email": "regulardelete@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=regular_user_data)
    regular_headers = get_user_token_headers(client, "regulardelete", "password123")

    r = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=regular_headers,
    )
    assert r.status_code == 400


def test_delete_nonexistent_user(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test deleting user that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.delete(
        f"{settings.API_V1_STR}/users/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_update_user_role_without_superuser_privileges(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating user role as regular user."""
    # Create a user
    user_data = {
        "username": "roletarget",
        "email": "roletarget@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    # Try to update role as regular user
    from tests.utils.utils import get_user_token_headers

    regular_user_data = {
        "username": "regularrole",
        "email": "regularrole@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=regular_user_data)
    regular_headers = get_user_token_headers(client, "regularrole", "password123")

    r = client.patch(
        f"{settings.API_V1_STR}/users/{user_id}/role?role=root",
        headers=regular_headers,
    )
    assert r.status_code == 400


def test_update_user_role_with_invalid_value(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating user role with invalid role value."""
    # Create a user
    user_data = {
        "username": "invalidroletarget",
        "email": "invalidrole@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    # Try to update with invalid role
    r = client.patch(
        f"{settings.API_V1_STR}/users/{user_id}/role?role=invalid_role",
        headers=superuser_token_headers,
    )
    # Should validate role value
    assert r.status_code in [400, 422]


def test_assign_project_to_nonexistent_user(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test assigning project to non-existent user."""
    fake_user_id = "00000000-0000-0000-0000-000000000000"
    fake_project_id = "00000000-0000-0000-0000-000000000001"

    assignment_data = {"project_id": fake_project_id}
    r = client.post(
        f"{settings.API_V1_STR}/users/{fake_user_id}/assignments",
        headers=superuser_token_headers,
        json=assignment_data,
    )
    # Should return 404 for user not found or 422 for validation
    assert r.status_code in [404, 422]


def test_assign_project_without_superuser_privileges(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test assigning project as regular user."""
    # Create a user
    user_data = {
        "username": "assigntarget",
        "email": "assigntarget@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    # Try to assign as regular user
    from tests.utils.utils import get_user_token_headers

    regular_user_data = {
        "username": "regularassign",
        "email": "regularassign@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=regular_user_data)
    regular_headers = get_user_token_headers(client, "regularassign", "password123")

    assignment_data = {"project_id": "00000000-0000-0000-0000-000000000001"}
    r = client.post(
        f"{settings.API_V1_STR}/users/{user_id}/assignments",
        headers=regular_headers,
        json=assignment_data,
    )
    assert r.status_code == 400


def test_get_user_projects_without_authentication(client: TestClient) -> None:
    """Test getting user projects without auth token."""
    fake_user_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"{settings.API_V1_STR}/users/{fake_user_id}/projects")
    assert r.status_code == 401
