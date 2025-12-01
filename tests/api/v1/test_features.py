from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings


def test_create_feature(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a project first
    project_data = {"name": "Feature Test Project", "description": "Test Description"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    data = {"name": "Test Feature", "description": "Test Feature Description"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 201
    created_feature = r.json()
    assert created_feature["name"] == data["name"]
    assert created_feature["project_id"] == project_id


def test_read_features(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a project and feature first
    project_data = {"name": "Feature Test Project 2", "description": "Test Description"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    data = {"name": "Test Feature 2", "description": "Test Feature Description 2"}
    client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=data,
    )

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    features = r.json()
    assert len(features) >= 1


def test_read_feature(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a project and feature first
    project_data = {"name": "Feature Test Project 3", "description": "Test Description"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    data = {"name": "Test Feature 3", "description": "Test Feature Description 3"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=data,
    )
    feature_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{feature_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    feature = r.json()
    assert feature["name"] == data["name"]
    assert feature["id"] == feature_id


def test_update_feature(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a project and feature first
    project_data = {"name": "Feature Test Project 4", "description": "Test Description"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    data = {"name": "Test Feature 4", "description": "Test Feature Description 4"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=data,
    )
    feature_id = r.json()["id"]

    update_data = {"name": "Updated Feature 4"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{feature_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 200
    updated_feature = r.json()
    assert updated_feature["name"] == update_data["name"]


def test_delete_feature(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a project and feature first
    project_data = {"name": "Feature Test Project 5", "description": "Test Description"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    data = {"name": "Test Feature 5", "description": "Test Feature Description 5"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=data,
    )
    feature_id = r.json()["id"]

    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{feature_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 204

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{feature_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_bulk_create_features(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test FEAT-03: Bulk add features."""
    # Create a project
    project_data = {"name": "Bulk Test Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Bulk add features
    features_data = [
        {"name": "Bulk Feature 1", "description": "Desc 1"},
        {"name": "Bulk Feature 2", "description": "Desc 2"},
        {"name": "Bulk Feature 3", "description": "Desc 3"},
    ]
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk",
        headers=superuser_token_headers,
        json=features_data,
    )
    assert r.status_code == 201
    data = r.json()
    assert "count" in data
    assert data["count"] == 3
    assert "ids" in data
    assert len(data["ids"]) == 3


def test_bulk_delete_features(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test FEAT-06: Bulk delete features."""
    # Create a project
    project_data = {"name": "Bulk Delete Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Create features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Delete Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Bulk delete
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk-delete",
        headers=superuser_token_headers,
        json=feature_ids,
    )
    assert r.status_code == 200
    data = r.json()
    assert "deleted_count" in data
    assert data["deleted_count"] == 3


def test_list_features_paginated(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test FEAT-01: List features with pagination."""
    # Create a project
    project_data = {"name": "Pagination Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    for i in range(5):
        feature_data = {"name": f"Page Feature {i}", "description": f"Desc {i}"}
        client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )

    # List with pagination
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/features?page=1&per_page=2",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    features = r.json()
    assert isinstance(features, list)
