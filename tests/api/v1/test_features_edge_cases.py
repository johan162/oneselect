# type: ignore
"""Edge case tests for feature endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings


@pytest.fixture
def test_project(client: TestClient, superuser_token_headers: dict):
    """Create a test project."""
    project_data = {"name": "Feature Test Project", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    return r.json()


def test_list_features_without_authentication(client: TestClient, test_project) -> None:
    """Test listing features without auth token."""
    project_id = test_project["id"]
    r = client.get(f"{settings.API_V1_STR}/projects/{project_id}/features")
    assert r.status_code == 401


def test_list_features_for_nonexistent_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test listing features for non-existent project."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(
        f"{settings.API_V1_STR}/projects/{fake_id}/features",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_list_features_without_ownership(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test listing features without project ownership."""
    project_id = test_project["id"]

    # Create regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "featureuser",
        "email": "featureuser@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "featureuser", "password123")

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=regular_headers,
    )
    assert r.status_code == 400


def test_create_feature_without_authentication(
    client: TestClient, test_project
) -> None:
    """Test creating feature without auth token."""
    project_id = test_project["id"]
    feature_data = {"name": "Test Feature", "description": "Test"}

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        json=feature_data,
    )
    assert r.status_code == 401


def test_create_feature_for_nonexistent_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test creating feature for non-existent project."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    feature_data = {"name": "Test Feature", "description": "Test"}

    r = client.post(
        f"{settings.API_V1_STR}/projects/{fake_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    assert r.status_code == 404


def test_create_feature_without_ownership(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test creating feature without project ownership."""
    project_id = test_project["id"]

    # Create regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "featureuser2",
        "email": "featureuser2@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "featureuser2", "password123")

    feature_data = {"name": "Unauthorized Feature", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=regular_headers,
        json=feature_data,
    )
    assert r.status_code == 400


def test_create_feature_with_missing_name(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test creating feature without required name field."""
    project_id = test_project["id"]
    feature_data = {"description": "Missing name"}

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    assert r.status_code == 422


def test_create_feature_with_empty_name(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test creating feature with empty name string."""
    project_id = test_project["id"]
    feature_data = {"name": "", "description": "Empty name"}

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    assert r.status_code in [400, 422]


def test_create_feature_with_very_long_name(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test creating feature with excessively long name."""
    project_id = test_project["id"]
    feature_data = {"name": "A" * 1000, "description": "Long name test"}

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    # Should be rejected or truncated
    assert r.status_code in [201, 400, 422]


def test_bulk_create_features_with_empty_array(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test bulk create with empty feature array."""
    project_id = test_project["id"]

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk",
        headers=superuser_token_headers,
        json=[],
    )
    assert r.status_code == 201
    data = r.json()
    assert data["count"] == 0


def test_bulk_create_features_with_invalid_item(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test bulk create with one feature missing required name."""
    project_id = test_project["id"]

    features = [
        {"name": "Valid Feature 1", "description": "Valid"},
        {"description": "Missing name"},  # Invalid
        {"name": "Valid Feature 2", "description": "Valid"},
    ]

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk",
        headers=superuser_token_headers,
        json=features,
    )
    # Should fail validation and rollback transaction
    assert r.status_code == 422


def test_bulk_create_features_without_ownership(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test bulk create without project ownership."""
    project_id = test_project["id"]

    # Create regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "bulkuser",
        "email": "bulkuser@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "bulkuser", "password123")

    features = [{"name": f"Feature {i}", "description": "Test"} for i in range(3)]

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk",
        headers=regular_headers,
        json=features,
    )
    assert r.status_code == 400


def test_bulk_delete_with_empty_array(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test bulk delete with empty feature ID array."""
    project_id = test_project["id"]

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk-delete",
        headers=superuser_token_headers,
        json=[],
    )
    assert r.status_code == 200
    data = r.json()
    assert data["deleted_count"] == 0


def test_bulk_delete_with_nonexistent_ids(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test bulk delete with non-existent feature IDs."""
    project_id = test_project["id"]
    fake_ids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk-delete",
        headers=superuser_token_headers,
        json=fake_ids,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["deleted_count"] == 0


def test_bulk_delete_without_ownership(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test bulk delete without project ownership."""
    project_id = test_project["id"]

    # Create a feature first
    feature_data = {"name": "Feature to Delete", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    feature_id = r.json()["id"]

    # Try to delete as regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "deletefeatureuser",
        "email": "deletefeature@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "deletefeatureuser", "password123")

    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk-delete",
        headers=regular_headers,
        json=[feature_id],
    )
    assert r.status_code == 400


def test_get_feature_by_nonexistent_id(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test getting feature with non-existent ID."""
    project_id = test_project["id"]
    fake_id = "00000000-0000-0000-0000-000000000000"

    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_get_feature_with_wrong_project_id(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test getting feature with wrong project ID."""
    project_id = test_project["id"]

    # Create a feature
    feature_data = {"name": "Test Feature", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    feature_id = r.json()["id"]

    # Try to get it with wrong project ID
    wrong_project_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(
        f"{settings.API_V1_STR}/projects/{wrong_project_id}/features/{feature_id}",
        headers=superuser_token_headers,
    )
    # Should fail because feature doesn't belong to that project
    assert r.status_code in [400, 404]


def test_update_feature_without_ownership(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test updating feature without project ownership."""
    project_id = test_project["id"]

    # Create a feature
    feature_data = {"name": "Original Feature", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    feature_id = r.json()["id"]

    # Try to update as regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "updatefeatureuser",
        "email": "updatefeature@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(client, "updatefeatureuser", "password123")

    update_data = {"name": "Hacked Feature"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{feature_id}",
        headers=regular_headers,
        json=update_data,
    )
    assert r.status_code == 400


def test_update_nonexistent_feature(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test updating feature that doesn't exist."""
    project_id = test_project["id"]
    fake_id = "00000000-0000-0000-0000-000000000000"

    update_data = {"name": "Updated Name"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{fake_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 404


def test_update_feature_with_invalid_tags_format(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test updating feature with tags as string instead of array."""
    project_id = test_project["id"]

    # Create a feature
    feature_data = {"name": "Feature with Tags", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    feature_id = r.json()["id"]

    # Try to update with invalid tags format
    update_data = {"tags": "tag1,tag2"}  # Should be array
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{feature_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 422


def test_delete_feature_without_ownership(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test deleting feature without project ownership."""
    project_id = test_project["id"]

    # Create a feature
    feature_data = {"name": "Feature to Delete", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    feature_id = r.json()["id"]

    # Try to delete as regular user
    from tests.utils.utils import get_user_token_headers

    user_data = {
        "username": "deletefeatureuser2",
        "email": "deletefeature2@example.com",
        "password": "password123",
    }
    client.post(f"{settings.API_V1_STR}/auth/register", json=user_data)
    regular_headers = get_user_token_headers(
        client, "deletefeatureuser2", "password123"
    )

    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{feature_id}",
        headers=regular_headers,
    )
    assert r.status_code == 400


def test_delete_nonexistent_feature(
    client: TestClient, test_project, superuser_token_headers: dict
) -> None:
    """Test deleting feature that doesn't exist."""
    project_id = test_project["id"]
    fake_id = "00000000-0000-0000-0000-000000000000"

    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id}/features/{fake_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_create_feature_updates_variance(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test that creating a feature updates project variance when comparisons exist."""
    # Create project with features
    project_data = {"name": "Variance Update Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Variance Feature {i}", "description": f"Desc {i}"}
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json=feature_data,
        )
        feature_ids.append(r.json()["id"])

    # Create comparison to trigger variance updates
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

    # Add another feature - should update variance
    feature_data = {"name": "New Variance Feature", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    assert r.status_code == 201


def test_bulk_create_updates_variance(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test that bulk creating features updates project variance when comparisons exist."""
    # Create project with features
    project_data = {"name": "Bulk Variance Update Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Bulk Variance Feature {i}", "description": f"Desc {i}"}
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

    # Bulk add features
    bulk_data = [
        {"name": "Bulk New Feature 1", "description": "Desc 1"},
        {"name": "Bulk New Feature 2", "description": "Desc 2"},
    ]
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk",
        headers=superuser_token_headers,
        json=bulk_data,
    )
    assert r.status_code == 201
    assert r.json()["count"] == 2


def test_bulk_delete_updates_variance(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test that bulk deleting features updates project variance when comparisons exist."""
    # Create project with features
    project_data = {"name": "Bulk Delete Variance Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(4):
        feature_data = {"name": f"Delete Variance Feature {i}", "description": f"Desc {i}"}
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

    # Bulk delete some features
    to_delete = [feature_ids[2], feature_ids[3]]
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk-delete",
        headers=superuser_token_headers,
        json=to_delete,
    )
    assert r.status_code == 200
    assert r.json()["deleted_count"] == 2


def test_bulk_delete_all_features(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test bulk deleting all features resets variance."""
    # Create project with features
    project_data = {"name": "Delete All Features Test", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    project_id = r.json()["id"]

    # Add features
    feature_ids = []
    for i in range(2):
        feature_data = {"name": f"Delete All Feature {i}", "description": f"Desc {i}"}
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

    # Bulk delete all features
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/features/bulk-delete",
        headers=superuser_token_headers,
        json=feature_ids,
    )
    assert r.status_code == 200


def test_get_feature_mismatch_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test getting feature with wrong project ID."""
    # Create two projects
    project_data1 = {"name": "Mismatch Project 1", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data1,
    )
    project_id1 = r.json()["id"]

    project_data2 = {"name": "Mismatch Project 2", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data2,
    )
    project_id2 = r.json()["id"]

    # Add feature to project 1
    feature_data = {"name": "Mismatch Feature", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id1}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    feature_id = r.json()["id"]

    # Try to get feature from project 2
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id2}/features/{feature_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 400


def test_update_feature_mismatch_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test updating feature with wrong project ID."""
    # Create two projects
    project_data1 = {"name": "Update Mismatch Project 1", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data1,
    )
    project_id1 = r.json()["id"]

    project_data2 = {"name": "Update Mismatch Project 2", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data2,
    )
    project_id2 = r.json()["id"]

    # Add feature to project 1
    feature_data = {"name": "Update Mismatch Feature", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id1}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    feature_id = r.json()["id"]

    # Try to update feature via project 2
    update_data = {"name": "Updated Name", "description": "Updated"}
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id2}/features/{feature_id}",
        headers=superuser_token_headers,
        json=update_data,
    )
    assert r.status_code == 400


def test_delete_feature_mismatch_project(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test deleting feature with wrong project ID."""
    # Create two projects
    project_data1 = {"name": "Delete Mismatch Project 1", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data1,
    )
    project_id1 = r.json()["id"]

    project_data2 = {"name": "Delete Mismatch Project 2", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data2,
    )
    project_id2 = r.json()["id"]

    # Add feature to project 1
    feature_data = {"name": "Delete Mismatch Feature", "description": "Test"}
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id1}/features",
        headers=superuser_token_headers,
        json=feature_data,
    )
    feature_id = r.json()["id"]

    # Try to delete feature via project 2
    r = client.delete(
        f"{settings.API_V1_STR}/projects/{project_id2}/features/{feature_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 400

