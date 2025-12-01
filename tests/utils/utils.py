import random
import string
from typing import Dict

from fastapi.testclient import TestClient

from app.core.config import settings


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def get_superuser_token_headers(client: TestClient) -> Dict[str, str]:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    if r.status_code != 200:
        print(f"Login failed with status {r.status_code}: {r.text}")
        raise ValueError(f"Login failed: {r.status_code} - {r.text}")
    tokens = r.json()
    if "access_token" not in tokens:
        print(f"No access_token in response: {tokens}")
        raise ValueError(f"No access_token in response: {tokens}")
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers


def get_user_token_headers(
    client: TestClient, username: str, password: str
) -> Dict[str, str]:
    """Login as a regular user and return auth headers."""
    login_data = {
        "username": username,
        "password": password,
    }
    r = client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    if r.status_code != 200:
        print(f"Login failed with status {r.status_code}: {r.text}")
        raise ValueError(f"Login failed: {r.status_code} - {r.text}")
    tokens = r.json()
    if "access_token" not in tokens:
        print(f"No access_token in response: {tokens}")
        raise ValueError(f"No access_token in response: {tokens}")
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers
