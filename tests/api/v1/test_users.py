from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from app import crud
from app.core.config import settings


def test_create_user(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    username = "testuser"
    password = "testpassword"
    email = "testuser@example.com"
    data = {"username": username, "password": password, "email": email}
    r = client.post(
        f"{settings.API_V1_STR}/users/", headers=superuser_token_headers, json=data
    )
    assert r.status_code == 200
    created_user = r.json()
    assert created_user["email"] == email
    assert "id" in created_user

    user = crud.user.get_by_email(db, email=email)
    assert user
    assert user.email == email


def test_read_users(client: TestClient, superuser_token_headers: dict) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/", headers=superuser_token_headers)
    assert r.status_code == 200
    users = r.json()
    assert len(users) >= 1


def test_read_user_by_id(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a user first to read
    user_data = {
        "username": "readuser",
        "email": "readuser@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/", headers=superuser_token_headers, json=user_data
    )
    user_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}", headers=superuser_token_headers
    )
    assert r.status_code == 200
    user_dict = r.json()
    assert user_dict["email"] == user_data["email"]


def test_update_user(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a user first to update
    user_data = {
        "username": "updateuser",
        "email": "updateuser@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/", headers=superuser_token_headers, json=user_data
    )
    user_id = r.json()["id"]

    data = {"is_active": True}
    r = client.put(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    user_dict = r.json()
    assert user_dict["is_active"] is True


def test_delete_user(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test USER-03: Delete user."""
    # Create a user to delete
    user_data = {
        "username": "deleteme",
        "email": "deleteme@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    # Delete the user
    r = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 204

    # Verify user is deleted
    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_update_user_role(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test USER-04: Update user role."""
    # Create a regular user with unique username
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "username": f"regularuser_{unique_id}",
        "email": f"regular_{unique_id}@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    assert r.status_code in [200, 201]
    user_id = r.json()["id"]

    # Update role to root
    role_data = {"role": "root"}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{user_id}/role",
        headers=superuser_token_headers,
        json=role_data,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["is_superuser"] is True


def test_assign_project_to_user(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test USER-02: Assign project to user."""
    # Create a user
    user_data = {
        "username": "projectuser",
        "email": "projectuser@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    # Create a project
    project_data = {"name": "Assignment Test", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Assign project to user
    assignment_data = {"projectId": project_id}
    r = client.post(
        f"{settings.API_V1_STR}/users/{user_id}/assignments",
        json=assignment_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "message" in data


def test_get_user_projects(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test PROJ-06: List user projects."""
    # Create a user
    user_data = {
        "username": "projectowner",
        "email": "projectowner@example.com",
        "password": "password123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=user_data,
    )
    user_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}/projects",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
