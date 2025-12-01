from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings


def test_get_access_token(client: TestClient, db: Session) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    tokens = r.json()
    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]


def test_use_access_token(client: TestClient, superuser_token_headers: dict) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/auth/login/test-token", headers=superuser_token_headers
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result
