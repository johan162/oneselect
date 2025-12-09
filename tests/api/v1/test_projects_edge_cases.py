"""Edge case tests for project endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings


def test_create_project_without_authentication(client: TestClient) -> None:
    """Test creating project without auth token."""
    data = {"name": "Test Project", "description": "Test"}
    r = client.post(f"{settings.API_V1_STR}/projects/", json=data)
    assert r.status_code == 401


def test_create_project_with_missing_name(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test creating project without required name field."""
    data = {"description": "Test Description"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 422


def test_create_project_with_empty_name(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test creating project with empty name string."""
    data = {"name": "", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code in [400, 422]


def test_create_project_with_very_long_name(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test creating project with excessively long name."""
    data = {"name": "A" * 500, "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    # Should be rejected or truncated
    assert r.status_code in [201, 400, 422]


def test_create_project_with_xss_in_name(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test creating project with XSS attempt in name."""
    data = {
        "name": "<script>alert('xss')</script>",
        "description": "Test",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    # Should either sanitize or reject
    assert r.status_code in [201, 400, 422]
    if r.status_code == 201:
        # If accepted, script tags should be sanitized
        response_data = r.json()
        assert "<script>" not in response_data["name"]


def test_list_projects_without_authentication(client: TestClient) -> None:
    """Test listing projects without auth token."""
    r = client.get(f"{settings.API_V1_STR}/projects/")
    assert r.status_code == 401


def test_list_projects_with_negative_skip(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test pagination with negative skip value."""
    r = client.get(
        f"{settings.API_V1_STR}/projects/?skip=-5",
        headers=superuser_token_headers,
    )
    # Should either default to 0 or return validation error
    assert r.status_code in [200, 422]


def test_list_projects_with_excessive_limit(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test pagination with very large limit."""
    r = client.get(
        f"{settings.API_V1_STR}/projects/?limit=100000",
        headers=superuser_token_headers,
    )
    # Should cap at max value or succeed
    assert r.status_code == 200


def test_get_project_by_nonexistent_id(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test getting project with ID that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(
        f"{settings.API_V1_STR}/projects/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_get_project_by_malformed_id(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test getting project with invalid UUID format."""
    r = client.get(
        f"{settings.API_V1_STR}/projects/not-a-valid-uuid",
        headers=superuser_token_headers,
    )
    # Returns 404 as malformed UUID won't match any project
    assert r.status_code == 404


def test_get_project_without_ownership(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test accessing another user's project as regular user."""
    # Create a project as superuser
    project_data = {"name": "Superuser Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Create a regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "regularuser",
        "email": "regular@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_user_headers = get_user_token_headers(client, "regularuser", "password123")

    # Try to access superuser's project
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=regular_user_headers,
    )
    assert r.status_code == 400  # Not enough permissions


def test_update_project_without_ownership(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating another user's project."""
    # Create a project as superuser
    project_data = {"name": "Original Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Create a regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "regularuser2",
        "email": "regular2@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_user_headers = get_user_token_headers(client, "regularuser2", "password123")

    # Try to update superuser's project
    update_data = {"name": "Hacked Project"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=regular_user_headers,
        json=update_data,
    )
    assert r.status_code == 400  # Not enough permissions


def test_update_nonexistent_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating project that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    update_data = {"name": "Updated Name"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{fake_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 404


def test_update_project_with_invalid_field_types(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating project with wrong data types."""
    # Create a project first
    project_data = {"name": "Test Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Try to update with number for name field
    update_data = {"name": 12345}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 422


def test_delete_project_without_ownership(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test deleting another user's project."""
    # Create a project as superuser
    project_data = {"name": "Project to Delete", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Create a regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "regularuser3",
        "email": "regular3@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_user_headers = get_user_token_headers(client, "regularuser3", "password123")

    # Try to delete superuser's project
    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=regular_user_headers,
    )
    assert r.status_code == 400  # Not enough permissions


def test_delete_nonexistent_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test deleting project that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.delete(
        f"{settings.API_V1_STR}/projects/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_delete_project_twice(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test deleting same project twice (double delete)."""
    # Create a project
    project_data = {"name": "Project to Double Delete", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Delete once
    r1 = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=superuser_token_headers,
    )
    assert r1.status_code == 200

    # Try to delete again
    r2 = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=superuser_token_headers,
    )
    assert r2.status_code == 404


def test_get_summary_of_nonexistent_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test getting summary for non-existent project."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(
        f"{settings.API_V1_STR}/projects/{fake_id}/summary",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_get_collaborators_without_authentication(client: TestClient) -> None:
    """Test getting collaborators without auth token."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"{settings.API_V1_STR}/projects/{fake_id}/collaborators")
    assert r.status_code == 401


def test_get_activity_with_invalid_pagination(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test activity log with invalid pagination values."""
    # Create a project first
    project_data = {"name": "Activity Test Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Try with negative page and zero per_page
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/activity?page=-1&per_page=0",
        headers=superuser_token_headers,
    )
    # Should either handle gracefully or return validation error
    assert r.status_code in [200, 422]
