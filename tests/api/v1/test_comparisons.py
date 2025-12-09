from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings


def test_create_comparison(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a project first
    project_data = {
        "name": "Comparison Test Project",
        "description": "Test Description",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    feature_data_1 = {"name": "Feature 1", "description": "Desc 1"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data_1,
    )
    feature_1_id = r.json()["id"]

    feature_data_2 = {"name": "Feature 2", "description": "Desc 2"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data_2,
    )
    feature_2_id = r.json()["id"]

    data = {
        "feature_a_id": feature_1_id,
        "feature_b_id": feature_2_id,
        "choice": "feature_a",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 201
    created_comparison = r.json()
    assert created_comparison["project_id"] == project_id
    assert created_comparison["feature_a"]["id"] == feature_1_id
    assert created_comparison["feature_b"]["id"] == feature_2_id
    assert created_comparison["choice"] == "feature_a"
    assert created_comparison["dimension"] == "value"


def test_read_comparisons(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create a project with comparisons first
    project_data = {
        "name": "Comparison Test Read Project",
        "description": "Test Description",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    comparisons = r.json()
    assert isinstance(comparisons, list)


def test_read_comparison(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create project, features, comparison
    project_data = {
        "name": "Comparison Test Project 2",
        "description": "Test Description",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    feature_data_1 = {"name": "Feature 3", "description": "Desc 3"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data_1,
    )
    feature_1_id = r.json()["id"]

    feature_data_2 = {"name": "Feature 4", "description": "Desc 4"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data_2,
    )
    feature_2_id = r.json()["id"]

    data = {
        "feature_a_id": feature_1_id,
        "feature_b_id": feature_2_id,
        "choice": "feature_a",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=data,
    )
    comparison_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    comparison = r.json()
    assert comparison["id"] == comparison_id


def test_update_comparison(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create project, features, comparison
    project_data = {
        "name": "Comparison Test Project 3",
        "description": "Test Description",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    feature_data_1 = {"name": "Feature 5", "description": "Desc 5"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data_1,
    )
    feature_1_id = r.json()["id"]

    feature_data_2 = {"name": "Feature 6", "description": "Desc 6"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data_2,
    )
    feature_2_id = r.json()["id"]

    data = {
        "feature_a_id": feature_1_id,
        "feature_b_id": feature_2_id,
        "choice": "feature_a",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=data,
    )
    comparison_id = r.json()["id"]

    update_data = {"choice": "feature_b"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 200
    updated_comparison = r.json()
    assert updated_comparison["choice"] == "feature_b"


def test_delete_comparison(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    # Create project, features, comparison
    project_data = {
        "name": "Comparison Test Project 4",
        "description": "Test Description",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    feature_data_1 = {"name": "Feature 7", "description": "Desc 7"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data_1,
    )
    feature_1_id = r.json()["id"]

    feature_data_2 = {"name": "Feature 8", "description": "Desc 8"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data_2,
    )
    feature_2_id = r.json()["id"]

    data = {
        "feature_a_id": feature_1_id,
        "feature_b_id": feature_2_id,
        "choice": "feature_a",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=data,
    )
    comparison_id = r.json()["id"]

    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 204

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_get_next_comparison_pair(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test COMP-01: Get next comparison pair."""
    # Create project with features
    project_data = {"name": "Next Pair Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    for i in range(3):
        feature_data = {"name": f"Feature {i}", "description": f"Desc {i}"}
        client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )

    # Get next pair
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code in [200, 204]


def test_get_comparison_estimates(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test COMP-03: Get comparison estimates."""
    project_data = {"name": "Estimates Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/estimates?dimension=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "dimension" in data
    assert "estimates" in data


def test_get_inconsistencies(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test COMP-04: Get inconsistencies."""
    project_data = {"name": "Inconsistencies Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/inconsistencies?dimension=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "cycles" in data


def test_get_comparison_progress(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test COMP-09: Get comparison progress."""
    project_data = {"name": "Progress Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress?dimension=complexity&target_certainty=0.90",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "dimension" in data
    assert "progress_percent" in data


def test_reset_comparisons(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test COMP-06: Reset comparisons."""
    project_data = {"name": "Reset Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    reset_data = {"dimension": "complexity"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/reset",
        json=reset_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "count" in data


def test_undo_comparison(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test COMP-10: Undo last comparison."""
    project_data = {"name": "Undo Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/undo",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    # May return 200 (if there's a comparison) or 404 (if none)
    assert r.status_code in [200, 404]


def test_skip_comparison(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test COMP-11: Skip comparison."""
    project_data = {"name": "Skip Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/skip",
        params={"comparison_id": "fake-id"},
        headers=superuser_token_headers,
    )
    assert r.status_code in [200, 404]


def test_get_resolution_pair(
    client: TestClient, superuser_token_headers: dict, db: Session
) -> None:
    """Test COMP-07: Get resolution pair for inconsistency."""
    project_data = {"name": "Resolution Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/resolve-inconsistency?dimension=complexity",
        headers=superuser_token_headers,
    )
    # Returns 204 if no inconsistencies
    assert r.status_code in [200, 204]
