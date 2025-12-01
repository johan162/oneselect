"""Tests for statistics and results endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_get_project_statistics(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test STAT-01: Get project statistics."""
    # Create a project first
    project_data = {
        "name": "Stats Test Project",
        "description": "Test project for statistics",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Get statistics
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/statistics",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "total_features" in data
    assert "comparisons_count" in data
    assert "average_variance" in data


def test_get_feature_scores(client: TestClient, superuser_token_headers: dict) -> None:
    """Test STAT-02: Get feature scores."""
    # Create a project
    project_data = {"name": "Scores Test Project", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Add a feature
    feature_data = {"name": "Test Feature", "description": "Test feature"}
    client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        json=feature_data,
        headers=superuser_token_headers,
    )

    # Get scores
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/statistics/scores",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_get_ranked_results(client: TestClient, superuser_token_headers: dict) -> None:
    """Test RES-01: Get ranked results."""
    # Create project
    project_data = {"name": "Results Test Project", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Get results
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/results",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_get_ranked_results_with_sort(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test RES-01: Get ranked results with sort parameter."""
    # Create project
    project_data = {"name": "Sort Test Project", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Get results sorted by complexity
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/results?sort_by=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200


def test_get_quadrant_analysis(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test RES-02: Get quadrant analysis."""
    # Create project
    project_data = {"name": "Quadrant Test Project", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Get quadrant analysis
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/results/quadrants",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "quick_wins" in data
    assert "strategic" in data
    assert "fill_ins" in data
    assert "avoid" in data


def test_export_results_json(client: TestClient, superuser_token_headers: dict) -> None:
    """Test RES-03: Export results as JSON."""
    # Create project
    project_data = {"name": "Export Test Project", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Export as JSON
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/results/export?format=json",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200


def test_export_results_csv(client: TestClient, superuser_token_headers: dict) -> None:
    """Test RES-03: Export results as CSV."""
    # Create project
    project_data = {"name": "CSV Export Project", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Export as CSV
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/results/export?format=csv",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
