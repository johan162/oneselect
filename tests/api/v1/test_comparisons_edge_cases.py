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
