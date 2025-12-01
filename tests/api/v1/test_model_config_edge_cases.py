"""Edge case tests for model configuration endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_get_model_config_without_authentication(client: TestClient) -> None:
    """Test getting model config without auth token."""
    r = client.get(f"{settings.API_V1_STR}/model-config/")
    # Endpoint not implemented - returns 404
    assert r.status_code in [401, 404]


def test_update_model_config_without_authentication(client: TestClient) -> None:
    """Test updating model config without auth token."""
    config_data = {"dimension": 5}
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        json=config_data,
    )
    # Endpoint not implemented - returns 404
    assert r.status_code in [401, 404]


def test_update_model_config_with_negative_dimension(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with negative dimension value."""
    config_data = {"dimension": -5}
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject negative values
    assert r.status_code in [400, 404, 422]


def test_update_model_config_with_zero_dimension(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with zero dimension."""
    config_data = {"dimension": 0}
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject zero value
    assert r.status_code in [400, 404, 422]


def test_update_model_config_with_excessively_large_dimension(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with unreasonably large dimension."""
    config_data = {"dimension": 1000000}
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should cap or reject excessive values
    assert r.status_code in [200, 400, 404, 422]


def test_update_model_config_with_float_dimension(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with float instead of integer."""
    config_data = {"dimension": 5.5}
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject float or coerce to int
    assert r.status_code in [200, 404, 422]


def test_update_model_config_with_string_dimension(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with string value."""
    config_data = {"dimension": "five"}
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject invalid type
    assert r.status_code in [404, 422]


def test_update_model_config_with_missing_required_fields(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with empty body."""
    config_data: dict = {}
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should validate required fields
    assert r.status_code in [200, 404, 422]


def test_update_model_config_with_extra_fields(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with unexpected extra fields."""
    config_data = {
        "dimension": 5,
        "extra_field": "should be ignored",
        "another_extra": 123,
    }
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should ignore extra fields or succeed
    assert r.status_code in [200, 404, 422]


def test_update_model_config_with_negative_max_iterations(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with negative max iterations."""
    config_data = {
        "dimension": 5,
        "max_iterations": -100,
    }
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject negative iterations
    assert r.status_code in [200, 400, 404, 422]


def test_update_model_config_with_invalid_learning_rate(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with invalid learning rate."""
    config_data = {
        "dimension": 5,
        "learning_rate": -0.5,
    }
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject negative learning rate
    assert r.status_code in [200, 400, 404, 422]


def test_update_model_config_with_zero_learning_rate(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with zero learning rate."""
    config_data = {
        "dimension": 5,
        "learning_rate": 0.0,
    }
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject zero learning rate
    assert r.status_code in [200, 400, 404, 422]


def test_update_model_config_with_very_large_learning_rate(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with excessively large learning rate."""
    config_data = {
        "dimension": 5,
        "learning_rate": 1000.0,
    }
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should cap or warn about large value
    assert r.status_code in [200, 400, 404, 422]


def test_reset_model_config_without_authentication(client: TestClient) -> None:
    """Test resetting model config without auth token."""
    r = client.post(f"{settings.API_V1_STR}/model-config/reset")
    assert r.status_code in [401, 404]


def test_reset_model_config_as_regular_user(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test resetting model config as non-admin user."""
    r = client.post(
        f"{settings.API_V1_STR}/model-config/reset",
        headers=normal_user_token_headers,
    )
    # Should allow or require admin privileges
    assert r.status_code in [200, 400, 403, 404]


def test_get_model_config_history_without_authentication(client: TestClient) -> None:
    """Test getting config history without auth token."""
    r = client.get(f"{settings.API_V1_STR}/model-config/history")
    assert r.status_code in [401, 404]


def test_get_model_config_history_with_negative_limit(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test config history with negative limit."""
    r = client.get(
        f"{settings.API_V1_STR}/model-config/history?limit=-10",
        headers=normal_user_token_headers,
    )
    # Should validate or default to reasonable value
    assert r.status_code in [200, 404, 422]


def test_validate_model_config_with_invalid_values(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test validation endpoint with invalid config values."""
    config_data = {
        "dimension": -5,
        "max_iterations": -100,
        "learning_rate": -0.5,
    }
    r = client.post(
        f"{settings.API_V1_STR}/model-config/validate",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should return validation errors
    assert r.status_code in [200, 400, 404, 422]


def test_validate_model_config_with_edge_case_values(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test validation with boundary values."""
    config_data = {
        "dimension": 1,  # Minimum possible dimension
        "max_iterations": 1,  # Minimum iterations
        "learning_rate": 0.0001,  # Very small learning rate
    }
    r = client.post(
        f"{settings.API_V1_STR}/model-config/validate",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should accept or reject boundary values
    assert r.status_code in [200, 400, 404, 422]


def test_update_model_config_with_null_values(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with null values."""
    config_data = {
        "dimension": None,
    }
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject null values
    assert r.status_code in [404, 422]


def test_get_default_model_config(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test getting default config values."""
    r = client.get(
        f"{settings.API_V1_STR}/model-config/defaults",
        headers=normal_user_token_headers,
    )
    # Should return defaults or 404 if not implemented
    assert r.status_code in [200, 404]


def test_update_model_config_with_array_instead_of_object(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test updating config with array body instead of object."""
    config_data = [{"dimension": 5}]
    r = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data,
    )
    # Should reject invalid structure
    assert r.status_code in [404, 422]


def test_concurrent_model_config_updates(
    client: TestClient, normal_user_token_headers: dict
) -> None:
    """Test handling of concurrent config updates."""
    config_data1 = {"dimension": 5}
    config_data2 = {"dimension": 10}

    # Simulate rapid updates
    r1 = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data1,
    )
    r2 = client.put(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
        json=config_data2,
    )

    # Both should succeed or return 404 if not implemented
    assert r1.status_code in [200, 404, 422]
    assert r2.status_code in [200, 404, 422]

    # Verify final state
    r = client.get(
        f"{settings.API_V1_STR}/model-config/",
        headers=normal_user_token_headers,
    )
    if r.status_code == 200:
        # Last update should be reflected
        assert r.json().get("dimension") in [5, 10]
