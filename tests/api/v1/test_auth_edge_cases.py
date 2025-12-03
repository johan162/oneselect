"""Edge case tests for authentication endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_login_with_missing_username(client: TestClient) -> None:
    """Test login without username field."""
    login_data = {"password": "somepassword"}
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert r.status_code == 422


def test_login_with_missing_password(client: TestClient) -> None:
    """Test login without password field."""
    login_data = {"username": "someuser"}
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert r.status_code == 422


def test_login_with_empty_credentials(client: TestClient) -> None:
    """Test login with empty strings."""
    login_data = {"username": "", "password": ""}
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    # 422 is returned because Pydantic validation rejects empty strings
    # This is valid FastAPI behavior for invalid form data
    assert r.status_code in [401, 422]


def test_login_with_sql_injection_attempt(client: TestClient) -> None:
    """Test login with SQL injection patterns."""
    login_data = {
        "username": "admin' OR '1'='1",
        "password": "' OR '1'='1",
    }
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert r.status_code == 401


def test_register_with_missing_username(client: TestClient) -> None:
    """Test register without username field."""
    user_data = {
        "email": "test@example.com",
        "password": "password123",
    }
    r = client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    assert r.status_code == 422


def test_register_with_missing_password(client: TestClient) -> None:
    """Test register without password field."""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
    }
    r = client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    assert r.status_code == 422


def test_register_with_invalid_email_format(client: TestClient) -> None:
    """Test register with invalid email formats."""
    invalid_emails = ["notanemail", "test@", "@example.com", "test@.com"]

    for email in invalid_emails:
        user_data = {
            "username": f"user_{email}",
            "email": email,
            "password": "password123",
        }
        r = client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
        # Should be 422 for validation error
        assert r.status_code in [400, 422], f"Email {email} should be rejected"


def test_register_with_very_long_username(client: TestClient) -> None:
    """Test register with username exceeding reasonable length."""
    user_data = {
        "username": "a" * 300,  # 300 characters
        "email": "longusertest@example.com",
        "password": "password123",
    }
    r = client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    # Should be rejected or truncated
    assert r.status_code in [400, 422]


def test_register_with_special_characters_in_username(client: TestClient) -> None:
    """Test register with special characters in username."""
    special_usernames = [
        "<script>alert('xss')</script>",
        "../admin",
        "user@domain",
        "user;DROP TABLE users;--",
    ]

    for username in special_usernames:
        user_data = {
            "username": username,
            "email": f"{username.replace('@', '')}@example.com",
            "password": "password123",
        }
        r = client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
        # Should either accept (sanitized) or reject - just shouldn't crash
        assert r.status_code in [201, 400, 422]


def test_change_password_without_authentication(client: TestClient) -> None:
    """Test change password without auth token."""
    password_data = {
        "current_password": "oldpass",
        "new_password": "newpass",
    }
    r = client.post(
        f"{settings.API_V1_STR}/auth/change-password",
        params=password_data,
    )
    assert r.status_code == 401


def test_change_password_with_wrong_current_password(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test change password with incorrect current password."""
    password_data = {
        "current_password": "wrongpassword",
        "new_password": "newstrongpassword456",
    }
    r = client.post(
        f"{settings.API_V1_STR}/auth/change-password",
        params=password_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 401


def test_update_profile_without_authentication(client: TestClient) -> None:
    """Test update profile without auth token."""
    update_data = {"email": "newemail@example.com"}
    r = client.patch(f"{settings.API_V1_STR}/auth/me", json=update_data)
    assert r.status_code == 401


def test_update_profile_with_existing_email(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test update profile with email already used by another user."""
    # First create another user
    new_user_data = {
        "username": "existinguser",
        "email": "existing@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=new_user_data)

    # Try to update superuser's email to the existing one
    update_data = {"email": "existing@example.com"}
    r = client.patch(
        f"{settings.API_V1_STR}/auth/me",
        json=update_data,
        headers=superuser_token_headers,
    )
    # Should fail due to duplicate email
    assert r.status_code == 400


def test_login_test_token_without_auth(client: TestClient) -> None:
    """Test token validation without auth header."""
    r = client.post(f"{settings.API_V1_STR}/auth/login/test-token")
    assert r.status_code == 401


def test_login_test_token_with_invalid_token(client: TestClient) -> None:
    """Test token validation with malformed token."""
    r = client.post(
        f"{settings.API_V1_STR}/auth/login/test-token",
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    assert r.status_code == 403


def test_logout_without_authentication(client: TestClient) -> None:
    """Test logout without auth token."""
    r = client.post(f"{settings.API_V1_STR}/auth/logout")
    assert r.status_code == 401


def test_register_with_duplicate_username(client: TestClient) -> None:
    """Test register with username that already exists."""
    # Create first user
    user1_data = {
        "username": "duplicatetest",
        "email": "user1@example.com",
        "password": "password123",
    }
    r1 = client.post(f"{settings.API_V1_STR}/auth/register", json=user1_data)
    assert r1.status_code == 201

    # Try to create second user with same username but different email
    user2_data = {
        "username": "duplicatetest",
        "email": "user2@example.com",
        "password": "password123",
    }
    r2 = client.post(f"{settings.API_V1_STR}/auth/register", json=user2_data)
    # Should fail due to duplicate username (if username has unique constraint)
    assert r2.status_code in [400, 409], "Duplicate username should be rejected"
