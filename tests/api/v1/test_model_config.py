"""Tests for model configuration endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_get_model_config(client: TestClient, superuser_token_headers: dict) -> None:
    """Test MODEL-01: Get model configuration."""
    # Create project
    project_data = {"name": "Model Config Test", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Get model config
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/model-config",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "dimensions" in data
    assert "complexity" in data["dimensions"]
    assert "value" in data["dimensions"]
    assert "selection_strategy" in data
    assert "max_parallel_pairs" in data


def test_update_model_config(client: TestClient, superuser_token_headers: dict) -> None:
    """Test MODEL-02: Update model configuration."""
    # Create project
    project_data = {"name": "Update Config Test", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Update config
    config_data = {
        "dimensions": {
            "complexity": {
                "prior_mean": 0.5,
                "prior_variance": 1.0,
                "logistic_scale": 0.1,
                "target_variance": 0.05,
                "tie_tolerance": 0.1,
            }
        },
        "selection_strategy": "entropy",
        "max_parallel_pairs": 5,
    }
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/model-config",
        json=config_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "message" in data


def test_update_model_config_invalid(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test MODEL-02: Update with invalid configuration."""
    # Create project
    project_data = {"name": "Invalid Config Test", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Try to update with invalid data
    config_data = {
        "selection_strategy": "invalid_strategy",  # Invalid value
    }
    r = client.put(
        f"{settings.API_V1_STR}/projects/{project_id}/model-config",
        json=config_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 400


def test_preview_model_config_impact(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """Test MODEL-03: Preview configuration impact."""
    # Create project
    project_data = {"name": "Preview Test", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Preview impact
    config_data = {
        "dimensions": {
            "complexity": {
                "prior_mean": 0.5,
                "prior_variance": 1.0,
            }
        }
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/model-config/preview",
        json=config_data,
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "complexity" in data or "value" in data


def test_reset_model_config(client: TestClient, superuser_token_headers: dict) -> None:
    """Test MODEL-04: Reset model configuration to defaults."""
    # Create project
    project_data = {"name": "Reset Config Test", "description": "Test project"}
    r = client.post(
        f"{settings.API_V1_STR}/projects",
        json=project_data,
        headers=superuser_token_headers,
    )
    project_id = r.json()["id"]

    # Reset config
    r = client.post(
        f"{settings.API_V1_STR}/projects/{project_id}/model-config/reset",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "defaults" in data


def test_model_config_unauthorized(client: TestClient) -> None:
    """Test model config endpoints without authentication."""
    project_id = "fake-project-id"

    r = client.get(f"{settings.API_V1_STR}/projects/{project_id}/model-config")
    assert r.status_code == 401
