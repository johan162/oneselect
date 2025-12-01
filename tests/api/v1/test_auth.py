"""Tests for authentication endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_login(client: TestClient) -> None:
    """Test AUTH-01: Login endpoint."""
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    tokens = r.json()
    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]


def test_login_invalid_credentials(client: TestClient) -> None:
    """Test login with invalid credentials."""
    login_data = {
        "username": "invalid_user",
        "password": "wrong_password",
    }
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert r.status_code == 401


def test_register(client: TestClient) -> None:
    """Test AUTH-02: Register endpoint."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "strongpassword123",
    }
    r = client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "id" in data


def test_register_duplicate_email(client: TestClient) -> None:
    """Test register with duplicate email."""
    user_data = {
        "username": "anotheruser",
        "email": settings.FIRST_SUPERUSER,
        "password": "password123",
    }
    r = client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    assert r.status_code == 400


def test_get_current_user(client: TestClient, superuser_token_headers: dict) -> None:
    """Test AUTH-05: Get current user profile."""
    r = client.get(f"{settings.API_V1_STR}/auth/me", headers=superuser_token_headers)
    assert r.status_code == 200
    data = r.json()
    assert "email" in data
    assert "username" in data


def test_get_current_user_no_auth(client: TestClient) -> None:
    """Test get current user without authentication."""
    r = client.get(f"{settings.API_V1_STR}/auth/me")
    assert r.status_code == 401


def test_update_profile(client: TestClient, superuser_token_headers: dict) -> None:
    """Test AUTH-07: Update user profile."""
    update_data = {
        "email": "updated@example.com",
        "display_name": "Updated Name",
    }
    r = client.patch(
        f"{settings.API_V1_STR}/auth/me",
        json=update_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == update_data["email"]


def test_change_password(client: TestClient, superuser_token_headers: dict) -> None:
    """Test AUTH-06: Change password endpoint."""
    password_data = {
        "current_password": settings.FIRST_SUPERUSER_PASSWORD,
        "new_password": "newstrongpassword123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/auth/change-password",
        params=password_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 204

    # Change password back to original for other tests
    password_data_reset = {
        "current_password": "newstrongpassword123",
        "new_password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(
        f"{settings.API_V1_STR}/auth/change-password",
        params=password_data_reset,
        headers=superuser_token_headers,
    )
    assert r.status_code == 204


def test_change_password_wrong_current(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test change password with wrong current password."""
    password_data = {
        "current_password": "wrongpassword",
        "new_password": "newstrongpassword123",
    }
    r = client.post(
        f"{settings.API_V1_STR}/auth/change-password",
        params=password_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 401


def test_logout(client: TestClient, superuser_token_headers: dict) -> None:
    """Test AUTH-04: Logout endpoint."""
    r = client.post(
        f"{settings.API_V1_STR}/auth/logout", headers=superuser_token_headers
    )
    assert r.status_code == 204


def test_refresh_token(client: TestClient) -> None:
    """Test AUTH-03: Refresh token endpoint (placeholder)."""
    refresh_data = {"refresh_token": "fake_token"}
    r = client.post(f"{settings.API_V1_STR}/auth/refresh", params=refresh_data)
    # Currently returns 501 as it's a placeholder
    assert r.status_code == 501
