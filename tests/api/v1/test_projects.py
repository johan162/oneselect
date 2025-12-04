from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings


def test_create_project(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    data = {"name": "Test Project", "description": "Test Description"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 201
    created_project = r.json()
    assert created_project["name"] == data["name"]
    assert created_project["description"] == data["description"]
    assert "id" in created_project
    assert "owner_id" in created_project


def test_read_projects(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a project first
    data = {"name": "Test Project 2", "description": "Test Description 2"}
    client.post(
        f"{settings.API_V1_STR}/projects/", headers=superuser_token_headers, json=data
    )

    r = client.get(f"{settings.API_V1_STR}/projects/", headers=superuser_token_headers)
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) >= 1


def test_read_project(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    data = {"name": "Test Project 3", "description": "Test Description 3"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/", headers=superuser_token_headers, json=data
    )
    created_project = r.json()
    project_id = created_project["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}", headers=superuser_token_headers
    )
    assert r.status_code == 200
    project = r.json()
    assert project["name"] == data["name"]
    assert project["id"] == project_id


def test_update_project(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    data = {"name": "Test Project 4", "description": "Test Description 4"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/", headers=superuser_token_headers, json=data
    )
    created_project = r.json()
    project_id = created_project["id"]

    update_data = {"name": "Updated Project 4"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 200
    updated_project = r.json()
    assert updated_project["name"] == update_data["name"]
    assert updated_project["description"] == data["description"]


def test_delete_project(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    data = {"name": "Test Project 5", "description": "Test Description 5"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/", headers=superuser_token_headers, json=data
    )
    created_project = r.json()
    project_id = created_project["id"]

    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}", headers=superuser_token_headers
    )
    assert r.status_code == 200
    deleted_project = r.json()
    assert deleted_project["id"] == project_id

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}", headers=superuser_token_headers
    )
    assert r.status_code == 404


def test_get_project_summary(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test PROJ-07: Get project summary."""
    # Create project
    data = {"name": "Summary Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    project_id = r.json()["id"]

    # Get summary
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/summary",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    summary = r.json()
    assert "project" in summary
    assert "feature_count" in summary
    assert "comparisons" in summary
    assert "average_variance" in summary
    assert "inconsistency_count" in summary


def test_get_project_collaborators(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test PROJ-08: Get project collaborators."""
    # Create project
    data = {"name": "Collaborators Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    project_id = r.json()["id"]

    # Get collaborators
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/collaborators",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    collaborators = r.json()
    assert isinstance(collaborators, list)
    assert len(collaborators) >= 1  # At least the owner


def test_get_project_activity(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test PROJ-09: Get project activity log."""
    # Create project
    data = {"name": "Activity Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    project_id = r.json()["id"]

    # Get activity
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/activity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    activity = r.json()
    assert "items" in activity
    assert "total" in activity


def test_get_project_activity_paginated(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test PROJ-09: Get paginated activity log."""
    # Create project
    data = {"name": "Paginated Activity", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    project_id = r.json()["id"]

    # Get paginated activity
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/activity?page=1&per_page=10",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200


def test_get_project_last_modified(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test PROJ-10: Get last modified timestamp."""
    # Create project
    data = {"name": "Last Modified Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    project_id = r.json()["id"]

    # Get last modified
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/last-modified",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "last_modified" in data
    assert "modified_by" in data


def test_get_project_history(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test PROJ-11: Get project comparison history."""
    # Create project
    data = {"name": "History Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=data,
    )
    project_id = r.json()["id"]

    # Get history
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/history",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "project" in data
    assert "comparisons" in data
    assert "deleted_comparisons" in data


def test_get_project_history_with_comparisons(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test PROJ-11: Get history with actual comparisons."""
    # Create project
    project_data = {"name": "History With Data", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"History Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Create a comparison
    comparison_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "choice": "feature_a",
        "dimension": "complexity",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    assert r.status_code == 201

    # Get history - should have one comparison
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/history",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["comparisons"]) >= 1
    assert len(data["deleted_comparisons"]) == 0
