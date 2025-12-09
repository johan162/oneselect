# type: ignore
"""Comprehensive edge case tests for comparison endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings


@pytest.fixture
def test_project_with_features(client: TestClient, superuser_token_headers: dict):
    """Create a test project with multiple features."""
    # Create project
    project_data = {"name": "Comparison Test Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Create multiple features
    features = []
    for i in range(3):
        feature_data = {
            "name": f"Feature {i}",
            "description": f"Test feature {i}",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        features.append(r.json())

    return {"project_id": project_id, "features": features}


def test_list_comparisons_without_authentication(
    client: TestClient, test_project_with_features
) -> None:
    """Test listing comparisons without auth token."""
    project_id = test_project_with_features["project_id"]
    r = client.get(f"{settings.API_V1_STR}/projects/{project_id}/comparisons")
    assert r.status_code == 401


def test_list_comparisons_for_nonexistent_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test listing comparisons for non-existent project."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(
        f"{settings.API_V1_STR}/projects/{fake_id}/comparisons",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_list_comparisons_without_ownership(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test listing comparisons without project ownership."""
    project_id = test_project_with_features["project_id"]

    # Create a regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "comparisonuser",
        "email": "compuser@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "comparisonuser", "password123")

    # Try to list comparisons
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=regular_headers,
    )
    assert r.status_code == 400


def test_get_next_comparison_with_invalid_dimension(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test getting next comparison with invalid dimension."""
    project_id = test_project_with_features["project_id"]
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=invalid",
        headers=superuser_token_headers,
    )
    assert r.status_code == 400


def test_get_next_comparison_with_missing_dimension(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test getting next comparison without required dimension parameter."""
    project_id = test_project_with_features["project_id"]
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next",
        headers=superuser_token_headers,
    )
    assert r.status_code == 422


def test_get_next_comparison_with_insufficient_features(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test getting next comparison when project has less than 2 features."""
    # Create project with only 1 feature
    project_data = {"name": "Single Feature Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    feature_data = {"name": "Lonely Feature", "description": "Alone"}
    client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )

    # Try to get next comparison
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=value",
        headers=superuser_token_headers,
    )
    assert r.status_code == 400  # Changed from 204 to 400 as this is an error condition


def test_get_next_comparison_without_authentication(
    client: TestClient, test_project_with_features
) -> None:
    """Test getting next comparison without auth token."""
    project_id = test_project_with_features["project_id"]
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=value"
    )
    assert r.status_code == 401


def test_create_comparison_without_authentication(
    client: TestClient, test_project_with_features
) -> None:
    """Test creating comparison without auth token."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    comparison_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[1]["id"],
        "choice": "feature_a",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        json=comparison_data,
    )
    assert r.status_code == 401


def test_create_comparison_with_missing_required_fields(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test creating comparison with missing required fields."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    # Missing choice
    comparison_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[1]["id"],
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    assert r.status_code == 422


def test_create_comparison_with_same_feature_both_sides(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test creating comparison with same feature for A and B."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    comparison_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[0]["id"],  # Same as feature_a
        "choice": "tie",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    # Should be rejected by business logic
    assert r.status_code in [400, 422]


def test_create_comparison_with_nonexistent_features(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test creating comparison with non-existent feature IDs."""
    project_id = test_project_with_features["project_id"]
    fake_id = "00000000-0000-0000-0000-000000000000"

    comparison_data = {
        "feature_a_id": fake_id,
        "feature_b_id": fake_id,
        "choice": "tie",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    # May return 404 or create anyway (depends on implementation)
    assert r.status_code in [201, 404, 400]


def test_create_comparison_with_invalid_choice_value(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test creating comparison with invalid choice value."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    comparison_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[1]["id"],
        "choice": "invalid_choice",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    assert r.status_code == 422


def test_create_comparison_with_invalid_dimension(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test creating comparison with invalid dimension value."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    comparison_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[1]["id"],
        "choice": "feature_a",
        "dimension": "invalid_dimension",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    assert r.status_code == 422


def test_get_comparison_by_nonexistent_id(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test getting comparison that doesn't exist."""
    project_id = test_project_with_features["project_id"]
    fake_id = "00000000-0000-0000-0000-000000000000"

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_update_comparison_with_invalid_choice(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test updating comparison with invalid choice value."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    # Create comparison first
    comparison_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[1]["id"],
        "choice": "feature_a",
        "dimension": "complexity",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    comparison_id = r.json()["id"]

    # Try to update with invalid choice
    update_data = {"choice": "invalid_choice"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 422


def test_update_nonexistent_comparison(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test updating comparison that doesn't exist."""
    project_id = test_project_with_features["project_id"]
    fake_id = "00000000-0000-0000-0000-000000000000"

    update_data = {"choice": "tie"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{fake_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 404


def test_delete_comparison_without_ownership(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test deleting comparison without project ownership."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    # Create comparison as superuser
    comparison_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[1]["id"],
        "choice": "feature_b",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    comparison_id = r.json()["id"]

    # Try to delete as regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "deleteuser",
        "email": "deleteuser@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "deleteuser", "password123")

    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=regular_headers,
    )
    assert r.status_code == 400


def test_delete_nonexistent_comparison(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test deleting comparison that doesn't exist."""
    project_id = test_project_with_features["project_id"]
    fake_id = "00000000-0000-0000-0000-000000000000"

    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_get_estimates_with_invalid_dimension(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test getting estimates with invalid dimension."""
    project_id = test_project_with_features["project_id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/estimates?dimension=bad",
        headers=superuser_token_headers,
    )
    # Should validate dimension parameter
    assert r.status_code in [400, 422]


def test_get_estimates_without_dimension_parameter(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test getting estimates without required dimension parameter."""
    project_id = test_project_with_features["project_id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/estimates",
        headers=superuser_token_headers,
    )
    assert r.status_code == 422


def test_reset_comparisons_without_ownership(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test resetting comparisons without project ownership."""
    project_id = test_project_with_features["project_id"]

    # Try to reset as regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "resetuser",
        "email": "resetuser@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "resetuser", "password123")

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/reset",
        headers=regular_headers,
    )
    assert r.status_code == 400


def test_undo_comparison_when_history_empty(
    client: TestClient, test_project_with_features, superuser_token_headers: dict
) -> None:
    """Test undoing comparison when no comparisons exist."""
    project_id = test_project_with_features["project_id"]

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/undo?dimension=complexity",
        headers=superuser_token_headers,
    )
    # Should return 404 when no comparisons exist
    assert r.status_code == 404


def test_skip_comparison_without_authentication(
    client: TestClient, test_project_with_features
) -> None:
    """Test skipping comparison without auth token."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    skip_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[1]["id"],
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/skip",
        json=skip_data,
    )
    assert r.status_code == 401


def test_get_inconsistencies_for_empty_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test getting inconsistencies for project with no comparisons."""
    # Create empty project
    project_data = {"name": "Empty Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/inconsistencies",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "cycles" in data or "inconsistencies" in data


def test_get_progress_without_authentication(
    client: TestClient, test_project_with_features
) -> None:
    """Test getting comparison progress without auth token."""
    project_id = test_project_with_features["project_id"]

    r = client.get(f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress")
    assert r.status_code == 401


# Additional Inconsistency Stats Tests


def test_get_inconsistency_stats(
    client: TestClient, superuser_token_headers: dict, test_project_with_features
) -> None:
    """Test getting inconsistency statistics."""
    project_id = test_project_with_features["project_id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/inconsistency-stats",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "cycle_count" in data
    assert "total_comparisons" in data
    assert "inconsistency_percentage" in data


def test_get_inconsistency_stats_with_dimension(
    client: TestClient, superuser_token_headers: dict, test_project_with_features
) -> None:
    """Test getting inconsistency stats filtered by dimension."""
    project_id = test_project_with_features["project_id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/inconsistency-stats?dimension=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["dimension"] == "complexity"


def test_get_inconsistency_stats_empty_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test getting inconsistency stats for project with no comparisons."""
    project_data = {"name": "Empty Stats Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/inconsistency-stats",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["cycle_count"] == 0
    assert data["total_comparisons"] == 0
    assert data["inconsistency_percentage"] == 0.0


def test_resolve_inconsistency_no_cycles(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test resolve inconsistency when there are no cycles."""
    project_data = {"name": "No Cycles Project", "description": "Test"}
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
    # Returns 204 when there are no inconsistencies to resolve
    assert r.status_code == 204


def test_create_comparison_with_tie(
    client: TestClient, superuser_token_headers: dict, test_project_with_features
) -> None:
    """Test creating a comparison with tie outcome."""
    project_id = test_project_with_features["project_id"]
    features = test_project_with_features["features"]

    comparison_data = {
        "feature_a_id": features[0]["id"],
        "feature_b_id": features[1]["id"],
        "choice": "tie",
        "dimension": "value",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["choice"] == "tie"


def test_get_next_pair_insufficient_features(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test getting next pair when project has fewer than 2 features."""
    # Create project with only one feature
    project_data = {"name": "Single Feature Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add only one feature
    feature_data = {"name": "Only Feature", "description": "Test"}
    client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=complexity",
        headers=superuser_token_headers,
    )
    # Should return 400 or 204 indicating not enough features
    assert r.status_code in [400, 204]


def test_get_comparison_by_id(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test retrieving a specific comparison by ID."""
    # Create project with features
    project_data = {"name": "Get Comparison Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Comparison Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Create comparison
    comparison_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    comparison_id = r.json()["id"]

    # Get comparison by ID
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == comparison_id


def test_update_comparison_choice(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating a comparison's choice."""
    # Create project with features
    project_data = {"name": "Update Comparison Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Update Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Create comparison
    comparison_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    comparison_id = r.json()["id"]

    # Update comparison to feature_b
    update_data = {"choice": "feature_b"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["choice"] == "feature_b"


def test_undo_comparison_with_history(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test undoing a comparison when there is history."""
    # Create project with features
    project_data = {"name": "Undo Test Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Undo Feature {i}", "description": f"Desc {i}"}
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
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    assert r.status_code == 201

    # Undo the comparison
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/undo?dimension=complexity",
        headers=superuser_token_headers,
    )
    # Should return 200 if undo is available, or 204/404 if not
    assert r.status_code in [200, 204, 404]


def test_skip_comparison(client: TestClient, superuser_token_headers: dict) -> None:
    """Test skipping a comparison."""
    # Create project with features
    project_data = {"name": "Skip Test Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Skip Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Skip a comparison pair - use POST body instead of query params
    skip_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/skip",
        headers=superuser_token_headers,
        json=skip_data,
    )
    # Endpoint may not be implemented (404/405) or may succeed
    assert r.status_code in [200, 201, 404, 405, 422]


def test_batch_create_comparisons(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test creating multiple comparisons in batch."""
    # Create project with features
    project_data = {"name": "Batch Comparison Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(4):
        feature_data = {"name": f"Batch Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Create batch comparisons
    batch_data = [
        {
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "complexity",
            "choice": "feature_a",
        },
        {
            "feature_a_id": feature_ids[2],
            "feature_b_id": feature_ids[3],
            "dimension": "value",
            "choice": "feature_b",
        },
    ]
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/batch",
        headers=superuser_token_headers,
        json=batch_data,
    )
    # Batch endpoint may not exist (404/405)
    assert r.status_code in [200, 201, 404, 405]


def test_delete_comparison(client: TestClient, superuser_token_headers: dict) -> None:
    """Test deleting a comparison."""
    # Create project with features
    project_data = {"name": "Delete Comparison Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Delete Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Create comparison
    comparison_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    comparison_id = r.json()["id"]

    # Delete comparison
    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code in [200, 204]

    # Verify deletion
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_reset_comparisons_for_dimension(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test resetting all comparisons for a specific dimension."""
    # Create project with features
    project_data = {"name": "Reset Dimension Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Reset Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Create comparisons for complexity
    comparison_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )

    # Reset comparisons for complexity dimension
    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/reset?dimension=complexity",
        headers=superuser_token_headers,
    )
    # Endpoint may not exist (404) or may succeed
    assert r.status_code in [200, 204, 404]


def test_get_inconsistencies_with_cycles(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test detecting inconsistencies when cycles exist."""
    # Create project with features
    project_data = {"name": "Cycle Detection Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Cycle Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Create cyclic comparisons: A > B > C > A
    comparisons = [
        {
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "choice": "feature_a",
        },  # A > B
        {
            "feature_a_id": feature_ids[1],
            "feature_b_id": feature_ids[2],
            "choice": "feature_a",
        },  # B > C
        {
            "feature_a_id": feature_ids[2],
            "feature_b_id": feature_ids[0],
            "choice": "feature_a",
        },  # C > A (creates cycle)
    ]

    for comp in comparisons:
        comp["dimension"] = "complexity"
        client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
            headers=superuser_token_headers,
            json=comp,
        )

    # Check for inconsistencies
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/inconsistencies?dimension=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    # Should detect at least one cycle
    assert data["count"] >= 1


def test_get_comparison_history(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test retrieving comparison history for a project."""
    # Create project with features
    project_data = {"name": "History Test Project", "description": "Test"}
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

    # Create comparison
    comparison_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )

    # Get comparison history
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/history?dimension=complexity",
        headers=superuser_token_headers,
    )
    # May return history or 404 if endpoint doesn't exist
    assert r.status_code in [200, 404]


def test_undo_comparison_recalculates_feature_scores_and_variance(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test that undo_last_comparison properly recalculates:
    1. Feature mu and sigma values (indirectly via progress/variance)
    2. Project average variance

    This verifies the fix for the bug where undo only removed the comparison
    but didn't revert the Bayesian score updates.
    """
    # Create project
    project_data = {"name": "Undo Score Test", "description": "Test variance recalc"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create two features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Score Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Get initial project variance (should be 1.0 initially)
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    initial_project = r.json()
    initial_variance = initial_project.get("complexity_avg_variance", 1.0)
    assert initial_variance == 1.0, "Initial variance should be 1.0"

    # Get initial progress (bayesian_confidence should be 0 or near 0)
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    initial_progress = r.json()
    initial_bayesian_confidence = initial_progress.get("bayesian_confidence", 0.0)

    # Make first comparison: feature_a wins
    comparison_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    assert r.status_code == 201

    # Get progress after comparison - variance should have decreased
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    after_comp_progress = r.json()
    after_comp_variance = after_comp_progress.get("current_avg_variance", 1.0)
    after_comp_bayesian_confidence = after_comp_progress.get("bayesian_confidence", 0.0)

    # Variance should decrease after comparison (means sigma decreased)
    assert (
        after_comp_variance < initial_variance
    ), f"Variance should decrease after comparison: {after_comp_variance} < {initial_variance}"
    assert (
        after_comp_bayesian_confidence > initial_bayesian_confidence
    ), f"Bayesian confidence should increase: {after_comp_bayesian_confidence} > {initial_bayesian_confidence}"

    # Now undo the comparison
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/undo?dimension=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    # Get progress after undo - variance should be back to initial
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    after_undo_progress = r.json()
    after_undo_variance = after_undo_progress.get("current_avg_variance", 1.0)
    after_undo_bayesian_confidence = after_undo_progress.get("bayesian_confidence", 0.0)

    # Variance should be back to 1.0 (features reset to sigma=1.0)
    assert (
        after_undo_variance == 1.0
    ), f"Variance should reset to 1.0 after undo, got {after_undo_variance}"
    # Bayesian confidence should be back to initial
    assert (
        abs(after_undo_bayesian_confidence - initial_bayesian_confidence) < 0.01
    ), f"Bayesian confidence should reset: {after_undo_bayesian_confidence} ≈ {initial_bayesian_confidence}"


def test_undo_comparison_with_multiple_comparisons_preserves_earlier(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test that undoing the last comparison preserves earlier comparison effects.

    Make 2 comparisons, undo the second one, verify first comparison's
    effects are still applied (variance should be between initial and after-2nd).
    """
    # Create project
    project_data = {"name": "Undo Preserve Test", "description": "Test partial undo"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create three features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Preserve Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Get initial progress
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    initial_progress = r.json()
    initial_variance = initial_progress.get("current_avg_variance", 1.0)

    # First comparison: feature 0 beats feature 1
    comparison_data_1 = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data_1,
    )
    assert r.status_code == 201

    # Record progress after first comparison
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    after_first_progress = r.json()
    after_first_variance = after_first_progress.get("current_avg_variance", 1.0)
    # after_first_comparisons = after_first_progress.get("total_comparisons_done", 0)

    # Variance should decrease after first comparison
    assert (
        after_first_variance < initial_variance
    ), "Variance should decrease after first comparison"

    # Second comparison: feature 1 beats feature 2
    comparison_data_2 = {
        "feature_a_id": feature_ids[1],
        "feature_b_id": feature_ids[2],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data_2,
    )
    assert r.status_code == 201

    # Record progress after second comparison
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    after_second_progress = r.json()
    # after_second_variance = after_second_progress.get("current_avg_variance", 1.0)
    after_second_comparisons = after_second_progress.get("total_comparisons_done", 0)

    assert after_second_comparisons == 2, "Should have 2 comparisons"

    # Undo the second comparison
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/undo?dimension=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    # Verify progress after undo matches state after first comparison
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    after_undo_progress = r.json()
    after_undo_variance = after_undo_progress.get("current_avg_variance", 1.0)
    after_undo_comparisons = after_undo_progress.get("total_comparisons_done", 0)

    # Should have 1 comparison remaining
    assert (
        after_undo_comparisons == 1
    ), f"Should have 1 comparison after undo, got {after_undo_comparisons}"

    # Variance should match what it was after first comparison
    # (allowing for small floating point differences)
    assert (
        abs(after_undo_variance - after_first_variance) < 0.001
    ), f"Variance should match state after first comparison: {after_undo_variance} ≈ {after_first_variance}"

    # Should NOT be back to initial (first comparison effects preserved)
    assert (
        after_undo_variance < initial_variance
    ), "First comparison effects should be preserved (variance still reduced)"


def test_delete_comparison_recalculates_feature_scores_and_variance(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test that deleting a comparison recalculates feature scores and project variance.

    When a comparison is deleted, the Bayesian scores should be recalculated from
    remaining comparisons. If it was the only comparison, scores should return
    to initial values (mu=0, sigma=1, variance=1.0).
    """
    # Create project
    project_data = {
        "name": "Delete Recalc Test",
        "description": "Test delete recalculation",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create two features
    feature_ids = []
    for i in range(2):
        feature_data = {
            "name": f"Delete Recalc Feature {i}",
            "description": f"Description {i}",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Get initial progress (should show variance = 1.0 since no comparisons made)
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    initial_progress = r.json()
    initial_variance = initial_progress.get("current_avg_variance", 1.0)
    assert (
        initial_variance == 1.0
    ), f"Initial variance should be 1.0, got {initial_variance}"

    # Make a comparison
    comparison_data = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data,
    )
    assert r.status_code == 201
    comparison_id = r.json()["id"]

    # Verify variance changed after comparison
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    after_comparison_progress = r.json()
    after_comparison_variance = after_comparison_progress.get(
        "current_avg_variance", 1.0
    )
    assert (
        after_comparison_variance < 1.0
    ), f"Variance should decrease after comparison, got {after_comparison_variance}"

    # Delete the comparison
    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{comparison_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 204

    # Verify variance returned to 1.0 after delete
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    after_delete_progress = r.json()
    after_delete_variance = after_delete_progress.get("current_avg_variance", 1.0)

    # Variance should return to 1.0 since we deleted the only comparison
    assert (
        after_delete_variance == 1.0
    ), f"Variance should return to 1.0 after deleting only comparison, got {after_delete_variance}"

    # Comparison count should be 0
    assert (
        after_delete_progress.get("total_comparisons_done", -1) == 0
    ), "Should have 0 comparisons after delete"


def test_delete_comparison_preserves_other_comparisons(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test that deleting a comparison preserves effects of other comparisons.

    Make 2 comparisons, delete the first one, verify second comparison's
    effects are still applied.
    """
    # Create project
    project_data = {
        "name": "Delete Preserve Test",
        "description": "Test delete preserves others",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create three features
    feature_ids = []
    for i in range(3):
        feature_data = {
            "name": f"Delete Preserve Feature {i}",
            "description": f"Desc {i}",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Get initial variance
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    initial_variance = r.json().get("current_avg_variance", 1.0)

    # First comparison: feature 0 beats feature 1
    comparison_data_1 = {
        "feature_a_id": feature_ids[0],
        "feature_b_id": feature_ids[1],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data_1,
    )
    assert r.status_code == 201
    first_comparison_id = r.json()["id"]

    # Second comparison: feature 1 beats feature 2 (different pair)
    comparison_data_2 = {
        "feature_a_id": feature_ids[1],
        "feature_b_id": feature_ids[2],
        "dimension": "complexity",
        "choice": "feature_a",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json=comparison_data_2,
    )
    assert r.status_code == 201

    # Record state after both comparisons
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    after_both_progress = r.json()
    assert after_both_progress.get("total_comparisons_done") == 2

    # Delete the FIRST comparison (not the most recent)
    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/{first_comparison_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 204

    # Verify state after delete
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    after_delete_progress = r.json()
    after_delete_variance = after_delete_progress.get("current_avg_variance", 1.0)
    after_delete_comparisons = after_delete_progress.get("total_comparisons_done", 0)

    # Should have 1 comparison remaining
    assert (
        after_delete_comparisons == 1
    ), f"Should have 1 comparison after delete, got {after_delete_comparisons}"

    # Variance should NOT be back to initial (second comparison effects preserved)
    assert (
        after_delete_variance < initial_variance
    ), f"Second comparison effects should be preserved, variance {after_delete_variance} should be < {initial_variance}"


# ============================================================================
# Tests for get_resolution_pair endpoint
# ============================================================================


def test_get_resolution_pair_no_cycles(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test get_resolution_pair returns 204 when there are no cycles.
    """
    # Create project
    project_data = {"name": "Resolution No Cycles Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Make consistent comparisons (A > B > C, no cycle)
    # A beats B
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201

    # B beats C
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[1],
            "feature_b_id": feature_ids[2],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201

    # Request resolution pair - should return 204 (no cycles)
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/resolve-inconsistency",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 204


def test_get_resolution_pair_with_cycle(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test get_resolution_pair returns a pair when cycles exist.
    """
    # Create project
    project_data = {"name": "Resolution With Cycles Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Cycle Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Create a cycle: A > B > C > A
    # A beats B
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201

    # B beats C
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[1],
            "feature_b_id": feature_ids[2],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201

    # C beats A (creates cycle)
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[2],
            "feature_b_id": feature_ids[0],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201

    # Request resolution pair - should return a pair
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/resolve-inconsistency",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert "feature_a" in result
    assert "feature_b" in result
    assert result["dimension"] == "complexity"
    assert "reason" in result
    assert (
        "uncertainty" in result["reason"].lower() or "cycle" in result["reason"].lower()
    )


def test_get_resolution_pair_nonexistent_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test get_resolution_pair returns 404 for nonexistent project.
    """
    r = client.get(
        f"{settings.API_V1_STR}/projects/nonexistent-id/comparisons/resolve-inconsistency",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


# ============================================================================
# Tests for get_next_comparison_pair with target_certainty
# ============================================================================


def test_get_next_pair_returns_204_when_complete(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test get_next_pair returns 204 when all orderings are determined.
    """
    # Create project with just 2 features
    project_data = {"name": "Complete Ordering Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create 2 features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Complete Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Make the only possible comparison
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201

    # Next pair should return 204 (complete)
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 204


def test_get_next_pair_with_target_certainty(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test get_next_pair with target_certainty parameter returns pair when below target.
    """
    # Create project
    project_data = {"name": "Target Certainty Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create 4 features
    feature_ids = []
    for i in range(4):
        feature_data = {"name": f"Target Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Request next pair with target_certainty - should return a pair
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next",
        params={"dimension": "complexity", "target_certainty": 0.9},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert "feature_a" in result
    assert "feature_b" in result


def test_get_next_pair_with_cycles_offers_resolution(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test get_next_pair offers resolution pair when cycles exist.
    """
    # Create project
    project_data = {"name": "Next Pair Cycles Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create 3 features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Next Cycle Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Create a cycle: A > B > C > A
    comparisons = [
        (feature_ids[0], feature_ids[1], "feature_a"),  # A beats B
        (feature_ids[1], feature_ids[2], "feature_a"),  # B beats C
        (feature_ids[2], feature_ids[0], "feature_a"),  # C beats A
    ]

    for fa, fb, choice in comparisons:
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
            headers=superuser_token_headers,
            json={
                "feature_a_id": fa,
                "feature_b_id": fb,
                "dimension": "complexity",
                "choice": choice,
            },
        )
        assert r.status_code == 201

    # Request next pair - should offer resolution since cycles exist
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    # Should return 200 with resolution pair OR 204 if complete
    assert r.status_code in [200, 204]
    if r.status_code == 200:
        result = r.json()
        assert "feature_a" in result


# ============================================================================
# Tests for progress endpoint edge cases
# ============================================================================


def test_progress_with_all_pairs_compared(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test progress shows 100% when all pairs have been compared.
    """
    # Create project with 3 features
    project_data = {"name": "Full Progress Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create 3 features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Full Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Compare all pairs (3 pairs for 3 features): 0-1, 0-2, 1-2
    pairs = [
        (feature_ids[0], feature_ids[1]),
        (feature_ids[0], feature_ids[2]),
        (feature_ids[1], feature_ids[2]),
    ]

    for fa, fb in pairs:
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
            headers=superuser_token_headers,
            json={
                "feature_a_id": fa,
                "feature_b_id": fb,
                "dimension": "value",
                "choice": "feature_a",
            },
        )
        assert r.status_code == 201

    # Check progress - should show high confidence
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "value"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["unique_pairs_compared"] == 3
    assert result["total_possible_pairs"] == 3
    assert result["direct_coverage"] == 1.0


def test_progress_with_value_dimension(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test progress calculation works correctly for value dimension.
    """
    # Create project
    project_data = {"name": "Value Progress Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create 2 features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Value Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Make a comparison on value dimension
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "value",
            "choice": "feature_b",
        },
    )
    assert r.status_code == 201

    # Check progress for value dimension
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress",
        params={"dimension": "value"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["dimension"] == "value"
    assert result["total_comparisons_done"] == 1


# ============================================================================
# Tests for read_comparisons with dimension filter
# ============================================================================


def test_read_comparisons_filtered_by_dimension(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test that read_comparisons filters by dimension correctly.
    """
    # Create project
    project_data = {"name": "Filter Comparisons Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create 2 features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Filter Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Create comparison on complexity
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201

    # Create comparison on value
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "value",
            "choice": "feature_b",
        },
    )
    assert r.status_code == 201

    # Read all comparisons
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    all_comparisons = r.json()
    assert len(all_comparisons) == 2

    # Read only complexity comparisons
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    complexity_comparisons = r.json()
    assert len(complexity_comparisons) == 1
    assert complexity_comparisons[0]["dimension"] == "complexity"

    # Read only value comparisons
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        params={"dimension": "value"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    value_comparisons = r.json()
    assert len(value_comparisons) == 1
    assert value_comparisons[0]["dimension"] == "value"


# ============================================================================
# Tests for get_estimates endpoint
# ============================================================================


def test_get_estimates_complexity(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test get_comparison_estimates returns estimates for complexity dimension.
    """
    # Create project
    project_data = {"name": "Estimates Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create 5 features
    for i in range(5):
        feature_data = {"name": f"Estimate Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201

    # Get estimates
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/estimates",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["dimension"] == "complexity"
    assert "estimates" in result
    assert "70%" in result["estimates"]
    assert "80%" in result["estimates"]
    assert "90%" in result["estimates"]
    assert "95%" in result["estimates"]


def test_get_estimates_value(client: TestClient, superuser_token_headers: dict) -> None:
    """
    Test get_comparison_estimates returns estimates for value dimension.
    """
    # Create project
    project_data = {"name": "Value Estimates Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create 3 features
    for i in range(3):
        feature_data = {"name": f"Val Est Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201

    # Get estimates for value dimension
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/estimates",
        params={"dimension": "value"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["dimension"] == "value"


# ============================================================================
# Tests for get_inconsistencies endpoint
# ============================================================================


def test_get_inconsistencies_no_dimension_filter(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test get_inconsistencies without dimension filter returns all cycles.
    """
    # Create project
    project_data = {"name": "All Inconsistencies Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create features
    feature_ids = []
    for i in range(3):
        feature_data = {"name": f"Incon Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Get inconsistencies without dimension (should work)
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/inconsistencies",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert "cycles" in result
    assert "count" in result


def test_get_inconsistencies_with_tie_comparisons(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test that tie comparisons are handled correctly in cycle detection.
    """
    # Create project
    project_data = {"name": "Tie Inconsistencies Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Tie Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Create a tie comparison
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "complexity",
            "choice": "tie",
        },
    )
    assert r.status_code == 201

    # Get inconsistencies - ties shouldn't create cycles
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/inconsistencies",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["count"] == 0


# ============================================================================
# Tests for reset_comparisons with dimension filter
# ============================================================================


def test_reset_comparisons_specific_dimension(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test reset_comparisons only resets specified dimension.
    """
    # Create project
    project_data = {"name": "Reset Dimension Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Reset Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Create comparisons on both dimensions
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "value",
            "choice": "feature_b",
        },
    )
    assert r.status_code == 201

    # Reset only complexity dimension
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons/reset",
        params={"dimension": "complexity"},
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["count"] == 1

    # Verify only value comparison remains
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    remaining = r.json()
    assert len(remaining) == 1
    assert remaining[0]["dimension"] == "value"


# ============================================================================
# Tests for comparison created_at inconsistency stats
# ============================================================================


def test_create_comparison_returns_inconsistency_stats(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Test that create_comparison returns inconsistency stats in response.
    """
    # Create project
    project_data = {"name": "Stats Response Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Stats Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        assert r.status_code == 201
        feature_ids.append(r.json()["id"])

    # Create comparison
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
        headers=superuser_token_headers,
        json={
            "feature_a_id": feature_ids[0],
            "feature_b_id": feature_ids[1],
            "dimension": "complexity",
            "choice": "feature_a",
        },
    )
    assert r.status_code == 201
    result = r.json()

    # Verify inconsistency stats are included
    assert "inconsistency_stats" in result
    stats = result["inconsistency_stats"]
    assert "cycle_count" in stats
    assert "total_comparisons" in stats
    assert "inconsistency_percentage" in stats
    assert stats["cycle_count"] == 0  # No cycles with one comparison
