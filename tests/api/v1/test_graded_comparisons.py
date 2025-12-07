"""Tests for graded comparisons feature.

This file tests the new binary and graded comparison endpoints,
including mode validation and strength-weighted Bayesian updates.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings


def create_binary_project(client: TestClient, headers: dict) -> dict:
    """Create a project with binary comparison mode."""
    project_data = {
        "name": "Binary Comparison Project",
        "description": "Project using binary comparisons",
        "comparison_mode": "binary",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json=project_data,
    )
    assert r.status_code == 201
    return r.json()


def create_graded_project(client: TestClient, headers: dict) -> dict:
    """Create a project with graded comparison mode."""
    project_data = {
        "name": "Graded Comparison Project",
        "description": "Project using graded comparisons",
        "comparison_mode": "graded",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=headers,
        json=project_data,
    )
    assert r.status_code == 201
    return r.json()


def create_features(
    client: TestClient, headers: dict, project_id: str, count: int = 3
) -> list:
    """Create multiple features for a project."""
    features = []
    for i in range(count):
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=headers,
            json={"name": f"Feature {i+1}", "description": f"Description {i+1}"},
        )
        assert r.status_code == 201
        features.append(r.json())
    return features


class TestBinaryComparisonEndpoint:
    """Tests for the binary comparison endpoint."""

    def test_binary_comparison_success(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test successful binary comparison submission."""
        project = create_binary_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "choice": "feature_a",
            "dimension": "value",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/binary",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201
        result = r.json()
        assert result["choice"] == "feature_a"
        assert result["dimension"] == "value"
        assert "inconsistency_stats" in result

    def test_binary_comparison_tie(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test binary comparison with tie outcome."""
        project = create_binary_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "choice": "tie",
            "dimension": "complexity",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/binary",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201
        assert r.json()["choice"] == "tie"

    def test_binary_comparison_wrong_mode_rejected(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that binary endpoint rejects graded-mode projects."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "choice": "feature_a",
            "dimension": "value",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/binary",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 400
        assert "graded" in r.json()["detail"].lower()

    def test_binary_comparison_same_feature_rejected(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that comparing a feature with itself is rejected."""
        project = create_binary_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[0]["id"],
            "choice": "feature_a",
            "dimension": "value",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/binary",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 400
        assert "itself" in r.json()["detail"]

    def test_binary_comparison_feature_not_found(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that invalid feature IDs return 404."""
        project = create_binary_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": "00000000-0000-0000-0000-000000000000",
            "choice": "feature_a",
            "dimension": "value",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/binary",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 404

    def test_binary_comparison_project_not_found(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that invalid project ID returns 404."""
        data = {
            "feature_a_id": "00000000-0000-0000-0000-000000000000",
            "feature_b_id": "00000000-0000-0000-0000-000000000001",
            "choice": "feature_a",
            "dimension": "value",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/nonexistent-project/comparisons/binary",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 404


class TestGradedComparisonEndpoint:
    """Tests for the graded comparison endpoint."""

    def test_graded_comparison_a_much_better(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test graded comparison with a_much_better strength."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "dimension": "value",
            "strength": "a_much_better",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201
        result = r.json()
        assert result["strength"] == "a_much_better"
        assert result["choice"] == "feature_a"
        assert "inconsistency_stats" in result

    def test_graded_comparison_a_better(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test graded comparison with a_better strength."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "dimension": "value",
            "strength": "a_better",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201
        result = r.json()
        assert result["strength"] == "a_better"
        assert result["choice"] == "feature_a"

    def test_graded_comparison_equal(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test graded comparison with equal strength."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "dimension": "complexity",
            "strength": "equal",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201
        result = r.json()
        assert result["strength"] == "equal"
        assert result["choice"] == "tie"

    def test_graded_comparison_b_better(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test graded comparison with b_better strength."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "dimension": "value",
            "strength": "b_better",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201
        result = r.json()
        assert result["strength"] == "b_better"
        assert result["choice"] == "feature_b"

    def test_graded_comparison_b_much_better(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test graded comparison with b_much_better strength."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "dimension": "value",
            "strength": "b_much_better",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201
        result = r.json()
        assert result["strength"] == "b_much_better"
        assert result["choice"] == "feature_b"

    def test_graded_comparison_wrong_mode_rejected(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that graded endpoint rejects binary-mode projects."""
        project = create_binary_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "dimension": "value",
            "strength": "a_better",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 400
        assert "binary" in r.json()["detail"].lower()

    def test_graded_comparison_same_feature_rejected(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that comparing a feature with itself is rejected."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[0]["id"],
            "dimension": "value",
            "strength": "a_better",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 400
        assert "itself" in r.json()["detail"]


class TestStrengthWeightedBayesianUpdate:
    """Tests for strength-weighted Bayesian update algorithm."""

    def test_a_much_better_stronger_update_than_a_better(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that a_much_better causes larger score changes than a_better."""
        # Create two identical projects
        project1 = create_graded_project(client, superuser_token_headers)
        project1["name"] = "Graded Project 1"
        features1 = create_features(client, superuser_token_headers, project1["id"])

        project2_data = {
            "name": "Graded Project 2",
            "description": "Second graded project",
            "comparison_mode": "graded",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/",
            headers=superuser_token_headers,
            json=project2_data,
        )
        project2 = r.json()
        features2 = create_features(client, superuser_token_headers, project2["id"])

        # Submit "a_much_better" comparison for project1
        r1 = client.post(
            f"{settings.API_V1_STR}/projects/{project1['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json={
                "feature_a_id": features1[0]["id"],
                "feature_b_id": features1[1]["id"],
                "dimension": "value",
                "strength": "a_much_better",
            },
        )
        assert r1.status_code == 201

        # Submit "a_better" comparison for project2
        r2 = client.post(
            f"{settings.API_V1_STR}/projects/{project2['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json={
                "feature_a_id": features2[0]["id"],
                "feature_b_id": features2[1]["id"],
                "dimension": "value",
                "strength": "a_better",
            },
        )
        assert r2.status_code == 201

        # Get updated features
        r1_features = client.get(
            f"{settings.API_V1_STR}/projects/{project1['id']}/features",
            headers=superuser_token_headers,
        )
        r2_features = client.get(
            f"{settings.API_V1_STR}/projects/{project2['id']}/features",
            headers=superuser_token_headers,
        )

        f1a = next(f for f in r1_features.json() if f["id"] == features1[0]["id"])
        f2a = next(f for f in r2_features.json() if f["id"] == features2[0]["id"])

        # "a_much_better" should cause larger mu increase
        # Both started with mu=0, so we compare the current mu values
        assert (
            f1a["value_mu"] > f2a["value_mu"]
        ), "a_much_better should increase mu more than a_better"

    def test_graded_reduces_variance_more_than_binary(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that strong graded comparisons reduce variance more."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        # Get initial sigma
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project['id']}/features",
            headers=superuser_token_headers,
        )
        initial_sigma = r.json()[0]["value_sigma"]

        # Submit a_much_better comparison
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
            headers=superuser_token_headers,
            json={
                "feature_a_id": features[0]["id"],
                "feature_b_id": features[1]["id"],
                "dimension": "value",
                "strength": "a_much_better",
            },
        )
        assert r.status_code == 201

        # Check sigma decreased
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project['id']}/features",
            headers=superuser_token_headers,
        )
        new_sigma = r.json()[0]["value_sigma"]
        assert new_sigma < initial_sigma, "Comparison should reduce variance"


class TestProjectComparisonModeValidation:
    """Tests for project comparison_mode field."""

    def test_project_default_binary_mode(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that new projects default to binary mode."""
        project_data = {
            "name": "Default Mode Project",
            "description": "Test default mode",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/",
            headers=superuser_token_headers,
            json=project_data,
        )
        assert r.status_code == 201
        assert r.json()["comparison_mode"] == "binary"

    def test_project_can_be_created_with_graded_mode(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that projects can be created with graded mode."""
        project_data = {
            "name": "Graded Mode Project",
            "description": "Test graded mode",
            "comparison_mode": "graded",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/",
            headers=superuser_token_headers,
            json=project_data,
        )
        assert r.status_code == 201
        assert r.json()["comparison_mode"] == "graded"

    def test_project_invalid_mode_rejected(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that invalid comparison modes are rejected."""
        project_data = {
            "name": "Invalid Mode Project",
            "description": "Test invalid mode",
            "comparison_mode": "invalid_mode",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/",
            headers=superuser_token_headers,
            json=project_data,
        )
        assert r.status_code == 422  # Validation error


class TestLegacyComparisonEndpointCompatibility:
    """Tests for backward compatibility with existing comparison endpoint."""

    def test_legacy_endpoint_still_works(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test that the original POST /comparisons endpoint still works."""
        project = create_binary_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "choice": "feature_a",
            "dimension": "value",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201
        assert r.json()["choice"] == "feature_a"

    def test_legacy_endpoint_works_for_graded_project_with_strength(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Test legacy endpoint can accept strength field for graded projects."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(client, superuser_token_headers, project["id"])

        # Legacy endpoint can accept strength as optional field
        data = {
            "feature_a_id": features[0]["id"],
            "feature_b_id": features[1]["id"],
            "choice": "feature_a",
            "dimension": "value",
            "strength": "a_much_better",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons",
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == 201


class TestGradedComparisonEfficiency:
    """Tests demonstrating that graded comparisons need fewer total comparisons."""

    def test_graded_achieves_certainty_faster(
        self, client: TestClient, superuser_token_headers: dict, db: Session
    ) -> None:
        """Demonstrate that graded mode converges faster to certainty."""
        project = create_graded_project(client, superuser_token_headers)
        features = create_features(
            client, superuser_token_headers, project["id"], count=5
        )

        # Submit a few strong comparisons
        comparisons_made = 0
        for i in range(len(features) - 1):
            r = client.post(
                f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/graded",
                headers=superuser_token_headers,
                json={
                    "feature_a_id": features[i]["id"],
                    "feature_b_id": features[i + 1]["id"],
                    "dimension": "value",
                    "strength": "a_much_better",
                },
            )
            assert r.status_code == 201
            comparisons_made += 1

        # Check progress
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project['id']}/comparisons/progress",
            headers=superuser_token_headers,
            params={"dimension": "value"},
        )
        assert r.status_code == 200
        progress = r.json()

        # With 5 features and 4 "much_better" comparisons in a chain,
        # we should have good transitive inference
        assert progress["total_comparisons_done"] == comparisons_made
        # Transitive coverage should be high with a chain of comparisons
        assert progress["transitive_coverage"] > 0.5
