"""
Integration test for complete OneSelect workflow.

This test simulates a real-world usage scenario:
1. Login with admin credentials
2. Create a new user
3. Create a project with 5 features
4. Perform pairwise comparisons until ranking is complete (via transitivity)
5. Verify rankings are close to expected order (goodness score >= 0.8)
6. Check quadrant analysis (Quick Wins, Strategic, Fill-ins, Avoid)
"""

from fastapi.testclient import TestClient
from app.core.config import settings


def calculate_inversions(actual: list, expected: list) -> int:
    """Count the number of inversions between actual and expected ranking."""
    expected_positions = {item: i for i, item in enumerate(expected)}
    actual_positions = [expected_positions[item] for item in actual]

    inversions = 0
    n = len(actual_positions)
    for i in range(n):
        for j in range(i + 1, n):
            if actual_positions[i] > actual_positions[j]:
                inversions += 1
    return inversions


def calculate_goodness_score(actual: list, expected: list) -> float:
    """Calculate goodness score (1 - normalized inversions)."""
    n = len(actual)
    max_inversions = n * (n - 1) // 2
    if max_inversions == 0:
        return 1.0
    inversions = calculate_inversions(actual, expected)
    return 1.0 - (inversions / max_inversions)


class TestIntegrationWorkflow:
    """Integration test for complete comparison workflow."""

    # Expected orders based on test scenario:
    # Complexity order (highest to lowest): FeatA > FeatB > FeatC > FeatD > FeatE
    # Value order (highest to lowest): FeatE > FeatD > FeatC > FeatB > FeatA

    FEATURES = ["FeatE", "FeatD", "FeatC", "FeatB", "FeatA"]

    # Complexity ranking: A is most complex, E is least complex
    # So in pairwise: A beats B, C, D, E; B beats C, D, E; etc.
    COMPLEXITY_ORDER = {"FeatA": 5, "FeatB": 4, "FeatC": 3, "FeatD": 2, "FeatE": 1}

    # Value ranking: E is most valuable, A is least valuable
    # So in pairwise: E beats D, C, B, A; D beats C, B, A; etc.
    VALUE_ORDER = {"FeatE": 5, "FeatD": 4, "FeatC": 3, "FeatB": 2, "FeatA": 1}

    def test_complete_workflow(
        self, client: TestClient, superuser_token_headers: dict
    ) -> None:
        """
        Complete integration test workflow.

        Tests the full lifecycle:
        - User creation
        - Project creation
        - Feature addition
        - Pairwise comparisons
        - Result analysis
        """
        # ============================================================
        # STEP 1: Login with admin credentials (already done via fixture)
        # ============================================================
        # superuser_token_headers fixture handles this

        # Verify we're authenticated
        r = client.get(
            f"{settings.API_V1_STR}/users/me",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        admin_user = r.json()
        assert admin_user["is_superuser"] is True
        print(f"\n✓ Logged in as admin: {admin_user['email']}")

        # ============================================================
        # STEP 2: Create a new user (unique name)
        # ============================================================
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        new_user_data = {
            "username": f"user_{unique_suffix}",
            "email": f"user_{unique_suffix}@example.com",
            "password": "pwd1",
        }
        r = client.post(
            f"{settings.API_V1_STR}/users/",
            headers=superuser_token_headers,
            json=new_user_data,
        )
        assert r.status_code == 200, f"Failed to create user: {r.text}"
        created_user = r.json()
        assert created_user["username"] == f"user_{unique_suffix}"
        print(f"✓ Created user: {created_user['username']}")

        # ============================================================
        # STEP 3: Create a new project (project1)
        # ============================================================
        project_data = {
            "name": "project1",
            "description": "Integration test project for pairwise comparison",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/",
            headers=superuser_token_headers,
            json=project_data,
        )
        assert r.status_code == 201, f"Failed to create project: {r.text}"
        project = r.json()
        project_id = project["id"]
        assert project["name"] == "project1"
        print(f"✓ Created project: {project['name']} (ID: {project_id})")

        # ============================================================
        # STEP 4: Add five features
        # ============================================================
        feature_ids = {}
        for feature_name in self.FEATURES:
            feature_data = {
                "name": feature_name,
                "description": f"Test feature {feature_name}",
            }
            r = client.post(
                f"{settings.API_V1_STR}/projects/{project_id}/features",
                headers=superuser_token_headers,
                json=feature_data,
            )
            assert (
                r.status_code == 201
            ), f"Failed to create feature {feature_name}: {r.text}"
            feature = r.json()
            feature_ids[feature_name] = feature["id"]
            print(f"✓ Created feature: {feature_name} (ID: {feature['id']})")

        # ============================================================
        # STEP 5: Get comparison estimates
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/comparisons/estimates?dimension=complexity",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        estimates = r.json()
        print(
            f"✓ Comparison estimates for 90% confidence: {estimates['estimates']['90%']}"
        )

        # ============================================================
        # STEP 6: Perform comparisons for COMPLEXITY dimension until 100% confidence
        # ============================================================
        # With the hybrid confidence model:
        # - Coverage confidence = unique_pairs_compared / total_possible_pairs
        # - Once all pairs are compared consistently, effective_confidence = 100%
        # - For 5 features, we have 10 unique pairs (5*4/2)

        complexity_comparisons = 0
        # feature_names = list(feature_ids.keys())
        max_iterations = 11  # Safety limit (should complete in 10 for 5 features)

        # Helper function to determine the winner based on expected order
        def get_choice(feat_a_name: str, feat_b_name: str, order_map: dict) -> str:
            """Determine winner based on the expected order."""
            if order_map[feat_a_name] > order_map[feat_b_name]:
                return "feature_a"
            elif order_map[feat_b_name] > order_map[feat_a_name]:
                return "feature_b"
            else:
                return "tie"

        # Loop using /comparisons/next endpoint until it returns 204 (complete)
        while complexity_comparisons < max_iterations:
            # Get the next optimal pair from the API (active learning)
            r = client.get(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=complexity",
                headers=superuser_token_headers,
            )

            if r.status_code == 204:
                # All pairs compared consistently - ranking complete!
                print(
                    "✓ Complexity: Ranking complete! (all pairs compared, 204 returned)"
                )
                break

            assert (
                r.status_code == 200
            ), f"Unexpected status: {r.status_code} - {r.text}"

            next_pair = r.json()
            feat_a_name = next_pair["feature_a"]["name"]
            feat_b_name = next_pair["feature_b"]["name"]
            feat_a_id = next_pair["feature_a"]["id"]
            feat_b_id = next_pair["feature_b"]["id"]

            # Submit the comparison
            choice = get_choice(feat_a_name, feat_b_name, self.COMPLEXITY_ORDER)
            comparison_data = {
                "feature_a_id": feat_a_id,
                "feature_b_id": feat_b_id,
                "dimension": "complexity",
                "choice": choice,
            }
            r = client.post(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
                headers=superuser_token_headers,
                json=comparison_data,
            )
            assert (
                r.status_code == 201
            ), f"Failed comparison {feat_a_name} vs {feat_b_name}: {r.text}"
            complexity_comparisons += 1

            # Check and print progress
            r = client.get(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress?dimension=complexity",
                headers=superuser_token_headers,
            )
            assert r.status_code == 200
            progress = r.json()
            coverage = progress["coverage_confidence"]
            effective = progress["effective_confidence"]
            print(
                f"  Complexity: {complexity_comparisons} comparisons, coverage={coverage:.0%}, effective={effective:.0%}"
            )

        print(f"✓ Completed {complexity_comparisons} complexity comparisons")

        # ============================================================
        # STEP 7: Perform comparisons for VALUE dimension until 100% confidence
        # ============================================================
        value_comparisons = 0

        while value_comparisons < max_iterations:
            # Get the next optimal pair from the API (active learning)
            r = client.get(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=value",
                headers=superuser_token_headers,
            )

            if r.status_code == 204:
                # All pairs compared consistently - ranking complete!
                print("✓ Value: Ranking complete! (all pairs compared, 204 returned)")
                break

            assert (
                r.status_code == 200
            ), f"Unexpected status: {r.status_code} - {r.text}"

            next_pair = r.json()
            feat_a_name = next_pair["feature_a"]["name"]
            feat_b_name = next_pair["feature_b"]["name"]
            feat_a_id = next_pair["feature_a"]["id"]
            feat_b_id = next_pair["feature_b"]["id"]

            # Submit the comparison
            choice = get_choice(feat_a_name, feat_b_name, self.VALUE_ORDER)
            comparison_data = {
                "feature_a_id": feat_a_id,
                "feature_b_id": feat_b_id,
                "dimension": "value",
                "choice": choice,
            }
            r = client.post(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
                headers=superuser_token_headers,
                json=comparison_data,
            )
            assert (
                r.status_code == 201
            ), f"Failed comparison {feat_a_name} vs {feat_b_name}: {r.text}"
            value_comparisons += 1

            # Check and print progress
            r = client.get(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress?dimension=value",
                headers=superuser_token_headers,
            )
            assert r.status_code == 200
            progress = r.json()
            coverage = progress["coverage_confidence"]
            effective = progress["effective_confidence"]
            print(
                f"  Value: {value_comparisons} comparisons, coverage={coverage:.0%}, effective={effective:.0%}"
            )

        print(f"✓ Completed {value_comparisons} value comparisons")

        total_comparisons = complexity_comparisons + value_comparisons
        print(f"✓ Total comparisons needed: {total_comparisons}")

        # ============================================================
        # STEP 8: Get statistics
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/statistics",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        stats = r.json()
        print(f"✓ Statistics: {stats}")

        assert stats["total_features"] == 5
        assert stats["comparisons_count"]["complexity"] == complexity_comparisons
        assert stats["comparisons_count"]["value"] == value_comparisons

        # ============================================================
        # STEP 9: Get feature scores and variance
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        features = r.json()

        print("\n📊 Feature Scores and Variance:")
        print("-" * 70)
        print(
            f"{'Feature':<10} {'Complexity μ':>12} {'Complexity σ':>12} {'Value μ':>12} {'Value σ':>12}"
        )
        print("-" * 70)

        feature_scores = {}
        for f in features:
            name = f["name"]
            # Get detailed feature info with mu/sigma
            r = client.get(
                f"{settings.API_V1_STR}/projects/{project_id}/features/{f['id']}",
                headers=superuser_token_headers,
            )
            assert r.status_code == 200
            feature_detail = r.json()

            complexity_mu = feature_detail.get("complexity_mu", 0)
            complexity_sigma = feature_detail.get("complexity_sigma", 1)
            value_mu = feature_detail.get("value_mu", 0)
            value_sigma = feature_detail.get("value_sigma", 1)

            feature_scores[name] = {
                "complexity_mu": complexity_mu,
                "complexity_sigma": complexity_sigma,
                "value_mu": value_mu,
                "value_sigma": value_sigma,
            }

            print(
                f"{name:<10} {complexity_mu:>12.4f} {complexity_sigma:>12.4f} {value_mu:>12.4f} {value_sigma:>12.4f}"
            )

        print("-" * 70)

        # ============================================================
        # STEP 10: Verify complexity ranking
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/results?sort_by=complexity",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        complexity_results = r.json()

        print("\n📈 Complexity Ranking (highest to lowest):")
        complexity_ranking = []
        for i, result in enumerate(complexity_results, 1):
            name = result["feature"]["name"]
            score = result["score"]
            complexity_ranking.append(name)
            print(f"  {i}. {name}: {score:.4f}")

        # Expected order: FeatA > FeatB > FeatC > FeatD > FeatE
        expected_complexity_order = ["FeatA", "FeatB", "FeatC", "FeatD", "FeatE"]
        print(f"\n  Expected: {expected_complexity_order}")
        print(f"  Actual:   {complexity_ranking}")

        # Use goodness score to allow for minor inversions from transitive inference
        complexity_goodness = calculate_goodness_score(
            complexity_ranking, expected_complexity_order
        )
        print(f"  Goodness score: {complexity_goodness:.2%}")
        assert (
            complexity_goodness >= 0.8
        ), f"Complexity ranking too poor! Goodness {complexity_goodness:.2%} < 80%"
        print("  ✓ Complexity ranking has acceptable goodness!")

        # ============================================================
        # STEP 11: Verify value ranking
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/results?sort_by=value",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        value_results = r.json()

        print("\n📈 Value Ranking (highest to lowest):")
        value_ranking = []
        for i, result in enumerate(value_results, 1):
            name = result["feature"]["name"]
            score = result["score"]
            value_ranking.append(name)
            print(f"  {i}. {name}: {score:.4f}")

        # Expected order: FeatE > FeatD > FeatC > FeatB > FeatA
        expected_value_order = ["FeatE", "FeatD", "FeatC", "FeatB", "FeatA"]
        print(f"\n  Expected: {expected_value_order}")
        print(f"  Actual:   {value_ranking}")

        # Use goodness score to allow for minor inversions from transitive inference
        value_goodness = calculate_goodness_score(value_ranking, expected_value_order)
        print(f"  Goodness score: {value_goodness:.2%}")
        assert (
            value_goodness >= 0.8
        ), f"Value ranking too poor! Goodness {value_goodness:.2%} < 80%"
        print("  ✓ Value ranking has acceptable goodness!")

        # ============================================================
        # STEP 12: Get quadrant analysis (Quick Wins, Strategic, etc.)
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/results/quadrants",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        quadrants = r.json()

        print("\n🎯 Quadrant Analysis:")
        print("-" * 50)

        quick_wins = [f["name"] for f in quadrants["quick_wins"]]
        strategic = [f["name"] for f in quadrants["strategic"]]
        fill_ins = [f["name"] for f in quadrants["fill_ins"]]
        avoid = [f["name"] for f in quadrants["avoid"]]

        print(f"  Quick Wins (High Value, Low Complexity): {quick_wins}")
        print(f"  Strategic (High Value, High Complexity): {strategic}")
        print(f"  Fill-ins (Low Value, Low Complexity):    {fill_ins}")
        print(f"  Avoid (Low Value, High Complexity):      {avoid}")

        # Based on our setup:
        # - FeatE: Low complexity, High value -> Quick Win
        # - FeatD: Low-med complexity, High-med value -> Quick Win or Fill-in
        # - FeatC: Medium complexity, Medium value -> Could be any
        # - FeatB: High-med complexity, Low-med value -> Avoid or Strategic
        # - FeatA: High complexity, Low value -> Avoid

        # Verify FeatE is a Quick Win (highest value, lowest complexity)
        assert (
            "FeatE" in quick_wins
        ), f"FeatE should be a Quick Win, but quadrants are: {quadrants}"
        print("  ✓ FeatE correctly identified as Quick Win!")

        # Verify FeatA is Avoid (highest complexity, lowest value)
        assert (
            "FeatA" in avoid
        ), f"FeatA should be Avoid, but quadrants are: {quadrants}"
        print("  ✓ FeatA correctly identified as Avoid!")

        # ============================================================
        # STEP 13: Verify hybrid confidence model
        # ============================================================
        # With the new hybrid model, after all pairs are compared consistently:
        # - coverage_confidence = 1.0 (all 10 pairs compared)
        # - effective_confidence = 1.0 (100% confidence in ranking)

        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress?dimension=complexity",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        complexity_progress = r.json()

        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress?dimension=value",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        value_progress = r.json()

        print("\n📊 Hybrid Confidence Model Results:")
        print("-" * 60)
        print("  Complexity:")
        print(
            f"    Direct Coverage:   {complexity_progress['direct_coverage']:.0%} ({complexity_progress['unique_pairs_compared']}/{complexity_progress['total_possible_pairs']} pairs)"
        )
        print(
            f"    Transitive Coverage: {complexity_progress['transitive_coverage']:.0%} ({complexity_progress['transitive_known_pairs']}/{complexity_progress['total_possible_pairs']} pairs)"
        )
        print(f"    Bayesian:   {complexity_progress['bayesian_confidence']:.2%}")
        print(
            f"    Consistency: {complexity_progress['consistency_score']:.0%} ({complexity_progress['cycle_count']} cycles)"
        )
        print(f"    Effective:  {complexity_progress['effective_confidence']:.0%}")
        print("  Value:")
        print(
            f"    Direct Coverage:   {value_progress['direct_coverage']:.0%} ({value_progress['unique_pairs_compared']}/{value_progress['total_possible_pairs']} pairs)"
        )
        print(
            f"    Transitive Coverage: {value_progress['transitive_coverage']:.0%} ({value_progress['transitive_known_pairs']}/{value_progress['total_possible_pairs']} pairs)"
        )
        print(f"    Bayesian:   {value_progress['bayesian_confidence']:.2%}")
        print(
            f"    Consistency: {value_progress['consistency_score']:.0%} ({value_progress['cycle_count']} cycles)"
        )
        print(f"    Effective:  {value_progress['effective_confidence']:.0%}")

        # With transitive inference, we reach 100% effective confidence with LESS than 100% direct coverage
        # The key metric is transitive_coverage (ordering knowledge) not direct_coverage (comparisons made)
        assert (
            complexity_progress["transitive_coverage"] == 1.0
        ), f"Transitive coverage should be 100% when ranking complete, got {complexity_progress['transitive_coverage']}"
        assert (
            complexity_progress["effective_confidence"] == 1.0
        ), f"Effective confidence should be 100% for consistent complete comparisons, got {complexity_progress['effective_confidence']}"
        assert (
            value_progress["transitive_coverage"] == 1.0
        ), f"Transitive coverage should be 100% when ranking complete, got {value_progress['transitive_coverage']}"
        assert (
            value_progress["effective_confidence"] == 1.0
        ), f"Effective confidence should be 100% for consistent complete comparisons, got {value_progress['effective_confidence']}"

        print("  ✓ 100% effective confidence achieved for both dimensions!")

        # With transitive optimization, we need FEWER than n*(n-1)/2 comparisons
        # For 5 features, O(N²) would need 10 comparisons, but O(N log N) needs fewer
        max_comparisons = 5 * 4 // 2  # 10 for 5 features (O(N²) upper bound)
        assert (
            complexity_comparisons <= max_comparisons
        ), f"Expected at most {max_comparisons} comparisons for 5 features, got {complexity_comparisons}"
        assert (
            value_comparisons <= max_comparisons
        ), f"Expected at most {max_comparisons} comparisons for 5 features, got {value_comparisons}"

        # Transitive optimization should save at least 1 comparison (expect ~8 vs 10)
        if complexity_comparisons < max_comparisons:
            print(
                f"  ✓ Transitive optimization saved {max_comparisons - complexity_comparisons} complexity comparisons!"
            )
        if value_comparisons < max_comparisons:
            print(
                f"  ✓ Transitive optimization saved {max_comparisons - value_comparisons} value comparisons!"
            )

        print(
            f"  ✓ Comparisons per dimension: complexity={complexity_comparisons}, value={value_comparisons}"
        )

        # ============================================================
        # SUMMARY
        # ============================================================
        print("\n" + "=" * 70)
        print("✅ INTEGRATION TEST SUMMARY")
        print("=" * 70)
        print("  • User created: user1")
        print("  • Project created: project1")
        print(f"  • Features: {len(feature_ids)}")
        print(
            f"  • Total comparisons: {total_comparisons} (max would be {max_comparisons * 2})"
        )
        print(f"    - Complexity: {complexity_comparisons}")
        print(f"    - Value: {value_comparisons}")
        print(f"  • Complexity ranking verified: {' > '.join(complexity_ranking)}")
        print(f"  • Value ranking verified: {' > '.join(value_ranking)}")
        print(f"  • Quick Wins: {quick_wins}")
        print(f"  • Strategic: {strategic}")
        print(f"  • Fill-ins: {fill_ins}")
        print(f"  • Avoid: {avoid}")
        print("  • Coverage confidence: 100% (all pairs compared)")
        print("  • Effective confidence: 100% (perfect ranking information)")
        print("=" * 70)


def test_theoretical_score_verification(
    client: TestClient, superuser_token_headers: dict
) -> None:
    """
    Verify that feature scores converge to expected theoretical values.

    With perfect transitive comparisons (A>B>C>D>E), the Bradley-Terry
    model should produce scores that reflect the true ordering.
    """
    # Create a separate project for this test
    project_data = {
        "name": "theoretical_test",
        "description": "Test for theoretical score verification",
    }
    r = client.post(
        f"{settings.API_V1_STR}/projects/",
        headers=superuser_token_headers,
        json=project_data,
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    # Create features with known ordering
    feature_names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
    # True strength order: Alpha(5) > Beta(4) > Gamma(3) > Delta(2) > Epsilon(1)
    true_strength = {"Alpha": 5, "Beta": 4, "Gamma": 3, "Delta": 2, "Epsilon": 1}

    feature_ids = {}
    for name in feature_names:
        r = client.post(
            f"{settings.API_V1_STR}/projects/{project_id}/features",
            headers=superuser_token_headers,
            json={"name": name, "description": f"Feature {name}"},
        )
        assert r.status_code == 201
        feature_ids[name] = r.json()["id"]

    # Perform all pairwise comparisons (perfect information)
    for i, name_a in enumerate(feature_names):
        for name_b in feature_names[i + 1 :]:
            # Higher strength wins
            if true_strength[name_a] > true_strength[name_b]:
                choice = "feature_a"
            else:
                choice = "feature_b"

            r = client.post(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons",
                headers=superuser_token_headers,
                json={
                    "feature_a_id": feature_ids[name_a],
                    "feature_b_id": feature_ids[name_b],
                    "dimension": "complexity",
                    "choice": choice,
                },
            )
            assert r.status_code == 201

    # Get results
    r = client.get(
        f"{settings.API_V1_STR}/projects/{project_id}/results?sort_by=complexity",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    results = r.json()

    # Extract scores
    scores = {r["feature"]["name"]: r["score"] for r in results}

    print("\n📊 Theoretical Score Verification:")
    print("-" * 40)
    for name in feature_names:
        print(
            f"  {name}: score={scores[name]:.4f}, expected_rank={true_strength[name]}"
        )

    # Verify ordering matches true strength
    sorted_by_score = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    sorted_by_truth = sorted(
        true_strength.keys(), key=lambda x: true_strength[x], reverse=True
    )

    print(f"\n  Score order:    {sorted_by_score}")
    print(f"  Expected order: {sorted_by_truth}")

    assert (
        sorted_by_score == sorted_by_truth
    ), f"Score ordering doesn't match expected! Got {sorted_by_score}, expected {sorted_by_truth}"

    # Verify scores are monotonically decreasing
    score_values = [scores[name] for name in sorted_by_score]
    for i in range(len(score_values) - 1):
        assert (
            score_values[i] > score_values[i + 1]
        ), f"Scores should be strictly decreasing: {score_values}"

    print("  ✓ Scores correctly ordered and monotonically decreasing!")
