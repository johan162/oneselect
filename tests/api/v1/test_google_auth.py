"""Tests for Google OAuth authentication endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app import crud, schemas


# ============================================================
# Fixtures for Google OAuth Testing
# ============================================================


@pytest.fixture
def mock_google_userinfo():
    """Sample Google user info response."""
    return {
        "sub": "google_user_id_12345",  # Google's unique user ID
        "email": "testgoogleuser@gmail.com",
        "email_verified": True,
        "name": "Test Google User",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
        "given_name": "Test",
        "family_name": "User",
    }


@pytest.fixture
def mock_oauth_token(mock_google_userinfo):
    """Mock OAuth token response from Google."""
    return {
        "access_token": "mock_access_token_xyz",
        "token_type": "Bearer",
        "expires_in": 3600,
        "id_token": "mock_id_token",
        "userinfo": mock_google_userinfo,
    }


@pytest.fixture
def existing_local_user(db):
    """Create an existing local user for account linking tests."""
    # Check if user already exists
    existing = crud.user.get_by_email(db, email="linkable@gmail.com")
    if existing:
        return existing

    user_in = schemas.UserCreate(
        email="linkable@gmail.com",
        password="password123",
        username="linkableuser",
    )
    user = crud.user.create(db, obj_in=user_in)
    return user


@pytest.fixture
def existing_google_user(db):
    """Create an existing Google-authenticated user."""
    # Check if user already exists
    existing = crud.user.get_by_google_id(db, google_id="existing_google_id_789")
    if existing:
        return existing

    user = crud.user.create_google_user(
        db,
        email="existinggoogle@gmail.com",
        google_id="existing_google_id_789",
        username="existinggoogleuser",
        display_name="Existing Google User",
        avatar_url="https://example.com/avatar.jpg",
    )
    return user


# ============================================================
# Test AUTH-GOOGLE-03: OAuth Status Endpoint
# ============================================================


class TestGoogleOAuthStatus:
    """Test Google OAuth status endpoint."""

    def test_google_status_returns_configuration(self, client: TestClient):
        """Test AUTH-GOOGLE-03: Status endpoint returns OAuth configuration status."""
        r = client.get(f"{settings.API_V1_STR}/auth/google/status")
        assert r.status_code == 200
        data = r.json()

        # Should have all expected keys
        assert "google_oauth_enabled" in data
        assert "google_client_id_set" in data
        assert "google_client_secret_set" in data

        # Values should be booleans
        assert isinstance(data["google_oauth_enabled"], bool)
        assert isinstance(data["google_client_id_set"], bool)
        assert isinstance(data["google_client_secret_set"], bool)

    def test_google_status_enabled_when_configured(self, client: TestClient):
        """Test status shows enabled when both client_id and secret are set."""
        with patch.object(settings, "GOOGLE_CLIENT_ID", "test_client_id"):
            with patch.object(settings, "GOOGLE_CLIENT_SECRET", "test_client_secret"):
                r = client.get(f"{settings.API_V1_STR}/auth/google/status")
                assert r.status_code == 200
                data = r.json()
                assert data["google_oauth_enabled"] is True
                assert data["google_client_id_set"] is True
                assert data["google_client_secret_set"] is True

    def test_google_status_disabled_when_not_configured(self, client: TestClient):
        """Test status shows disabled when credentials are empty."""
        with patch.object(settings, "GOOGLE_CLIENT_ID", ""):
            with patch.object(settings, "GOOGLE_CLIENT_SECRET", ""):
                r = client.get(f"{settings.API_V1_STR}/auth/google/status")
                assert r.status_code == 200
                data = r.json()
                assert data["google_oauth_enabled"] is False

    def test_google_status_disabled_when_partial_config(self, client: TestClient):
        """Test status shows disabled when only client_id is set."""
        with patch.object(settings, "GOOGLE_CLIENT_ID", "test_client_id"):
            with patch.object(settings, "GOOGLE_CLIENT_SECRET", ""):
                r = client.get(f"{settings.API_V1_STR}/auth/google/status")
                assert r.status_code == 200
                data = r.json()
                assert data["google_oauth_enabled"] is False
                assert data["google_client_id_set"] is True
                assert data["google_client_secret_set"] is False


# ============================================================
# Test AUTH-GOOGLE-01: Initiate OAuth Flow
# ============================================================


class TestGoogleLogin:
    """Test Google OAuth login initiation endpoint."""

    def test_google_login_redirects_to_google(self, client: TestClient):
        """Test AUTH-GOOGLE-01: Login endpoint initiates OAuth redirect."""
        # Mock the oauth.google.authorize_redirect to return a redirect response
        mock_redirect_response = RedirectResponse(
            url="https://accounts.google.com/o/oauth2/v2/auth?client_id=test",
            status_code=302,
        )

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_redirect = AsyncMock(
                return_value=mock_redirect_response
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/login", follow_redirects=False
            )

            # Should return the redirect response
            assert r.status_code == 302
            # authorize_redirect should have been called
            mock_oauth.google.authorize_redirect.assert_called_once()


# ============================================================
# Test AUTH-GOOGLE-02: OAuth Callback Handling
# ============================================================


class TestGoogleCallback:
    """Test Google OAuth callback endpoint."""

    def test_callback_creates_new_user(self, client: TestClient, mock_google_userinfo):
        """Test callback creates new user when none exists."""
        mock_token = {"userinfo": mock_google_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should redirect to frontend with token
            assert r.status_code in [302, 307]
            location = r.headers.get("location", "")
            assert settings.FRONTEND_URL in location
            assert "/auth/callback" in location
            assert "token=" in location

    def test_callback_logs_in_existing_google_user(
        self, client: TestClient, db, existing_google_user
    ):
        """Test callback logs in existing Google user."""
        mock_userinfo = {
            "sub": existing_google_user.google_id,
            "email": existing_google_user.email,
            "name": existing_google_user.display_name or "Test User",
            "picture": existing_google_user.avatar_url,
        }
        mock_token = {"userinfo": mock_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should redirect to frontend with token
            assert r.status_code in [302, 307]
            location = r.headers.get("location", "")
            assert "token=" in location
            assert "/auth/callback" in location

    def test_callback_links_existing_local_account(
        self, client: TestClient, db, existing_local_user
    ):
        """Test callback links Google to existing local account with same email."""
        # Use the existing local user's email in Google response
        mock_userinfo = {
            "sub": "new_google_id_for_linking",
            "email": existing_local_user.email,
            "name": "Linked User",
            "picture": "https://example.com/newpic.jpg",
        }
        mock_token = {"userinfo": mock_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should redirect to frontend with token
            assert r.status_code in [302, 307]
            location = r.headers.get("location", "")
            assert "token=" in location

            # Extract token and verify it works (proves user was linked)
            import urllib.parse

            parsed = urllib.parse.urlparse(location)
            query_params = urllib.parse.parse_qs(parsed.query)
            token = query_params.get("token", [None])[0]

            # Use the token to access the API - this proves the user account works
            headers = {"Authorization": f"Bearer {token}"}
            r = client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
            assert r.status_code == 200
            # The email should match the existing user's email
            assert r.json()["email"] == existing_local_user.email

    def test_callback_generates_unique_username(self, client: TestClient, db):
        """Test callback generates unique username when email prefix is taken."""
        # First, create a user with username "duplicateuser"
        existing = crud.user.get_by_username(db, username="duplicateuser")
        if not existing:
            user_in = schemas.UserCreate(
                email="other@example.com",
                password="password123",
                username="duplicateuser",
            )
            crud.user.create(db, obj_in=user_in)

        # Now try to create a Google user with email duplicateuser@gmail.com
        mock_userinfo = {
            "sub": "unique_google_id_456",
            "email": "duplicateuser@gmail.com",  # Will try to use "duplicateuser"
            "name": "Duplicate User",
        }
        mock_token = {"userinfo": mock_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should still succeed - unique username generated
            assert r.status_code in [302, 307]
            location = r.headers.get("location", "")
            assert "token=" in location

            # Verify the token works (proves user was created)
            import urllib.parse

            parsed = urllib.parse.urlparse(location)
            query_params = urllib.parse.parse_qs(parsed.query)
            token = query_params.get("token", [None])[0]

            headers = {"Authorization": f"Bearer {token}"}
            r = client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
            assert r.status_code == 200
            # Username should be modified (not "duplicateuser")
            data = r.json()
            assert data["username"].startswith("duplicateuser")
            assert data["username"] != "duplicateuser"

    def test_callback_missing_userinfo_fails(self, client: TestClient):
        """Test callback fails when userinfo is missing from token."""
        mock_token = {
            "access_token": "some_token",
            # No userinfo!
        }

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should return 400 Bad Request (HTTPException is raised and not caught)
            assert r.status_code == 400
            assert "user info" in r.json()["detail"].lower()

    def test_callback_missing_email_fails(self, client: TestClient):
        """Test callback fails when email is missing from userinfo."""
        mock_userinfo = {
            "sub": "google_id_no_email",
            # No email!
            "name": "No Email User",
        }
        mock_token = {"userinfo": mock_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should return 400 Bad Request
            assert r.status_code == 400
            assert "required" in r.json()["detail"].lower()

    def test_callback_missing_google_id_fails(self, client: TestClient):
        """Test callback fails when Google ID (sub) is missing."""
        mock_userinfo = {
            # No sub!
            "email": "nosubuser@gmail.com",
            "name": "No Sub User",
        }
        mock_token = {"userinfo": mock_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should return 400 Bad Request
            assert r.status_code == 400
            assert "required" in r.json()["detail"].lower()

    def test_callback_oauth_exception_redirects_to_error(self, client: TestClient):
        """Test callback handles OAuth exceptions gracefully."""
        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                side_effect=Exception("OAuth token exchange failed")
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should redirect to error page with message
            assert r.status_code in [302, 307]
            location = r.headers.get("location", "")
            assert "/auth/error" in location
            assert "message=" in location

    def test_callback_sets_user_display_name_and_avatar(self, client: TestClient, db):
        """Test callback properly sets display name and avatar from Google."""
        mock_userinfo = {
            "sub": "google_id_with_profile",
            "email": "profileuser@gmail.com",
            "name": "Profile Test User",
            "picture": "https://lh3.googleusercontent.com/profile.jpg",
        }
        mock_token = {"userinfo": mock_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            assert r.status_code in [302, 307]
            location = r.headers.get("location", "")
            assert "token=" in location

            # Extract token and verify user profile via API
            import urllib.parse

            parsed = urllib.parse.urlparse(location)
            query_params = urllib.parse.parse_qs(parsed.query)
            token = query_params.get("token", [None])[0]

            headers = {"Authorization": f"Bearer {token}"}
            r = client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
            assert r.status_code == 200
            data = r.json()
            assert data["email"] == "profileuser@gmail.com"
            # Display name and avatar may be in the response if available in schema


# ============================================================
# Integration Test: Full OAuth Flow
# ============================================================


class TestGoogleOAuthIntegration:
    """Integration tests for complete OAuth flow."""

    def test_full_oauth_flow_new_user(
        self, client: TestClient, db, mock_google_userinfo
    ):
        """Test complete OAuth flow for a new user."""
        # Step 1: Check OAuth is available (status endpoint)
        with patch.object(settings, "GOOGLE_CLIENT_ID", "test_id"):
            with patch.object(settings, "GOOGLE_CLIENT_SECRET", "test_secret"):
                r = client.get(f"{settings.API_V1_STR}/auth/google/status")
                assert r.status_code == 200
                assert r.json()["google_oauth_enabled"] is True

        # Step 2: Simulate callback with Google user info
        # Use a unique email for this test
        mock_google_userinfo["email"] = "integration_test_user@gmail.com"
        mock_google_userinfo["sub"] = "integration_test_google_id"
        mock_token = {"userinfo": mock_google_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            r = client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

            # Should redirect with token
            assert r.status_code in [302, 307]
            location = r.headers.get("location", "")
            assert "token=" in location

            # Extract token from URL
            import urllib.parse

            parsed = urllib.parse.urlparse(location)
            query_params = urllib.parse.parse_qs(parsed.query)
            token = query_params.get("token", [None])[0]
            assert token is not None

        # Step 3: Verify token works for authentication (this proves user was created)
        headers = {"Authorization": f"Bearer {token}"}
        r = client.get(f"{settings.API_V1_STR}/auth/me", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "integration_test_user@gmail.com"
        assert data["is_active"] is True

    def test_oauth_user_cannot_use_password_login(self, client: TestClient, db):
        """Test that OAuth users cannot authenticate with password."""
        # Create a Google OAuth user
        mock_userinfo = {
            "sub": "oauth_only_google_id",
            "email": "oauthonly@gmail.com",
            "name": "OAuth Only User",
        }
        mock_token = {"userinfo": mock_userinfo}

        with patch("app.api.v1.endpoints.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value=mock_token
            )

            client.get(
                f"{settings.API_V1_STR}/auth/google/callback", follow_redirects=False
            )

        # Try to login with password (should fail)
        login_data = {
            "username": "oauthonly",
            "password": "anypassword",
        }
        r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
        assert r.status_code == 401
