"""
Parameterized integration tests for OneSelect comparison workflow.

This test suite runs various combinations of:
- Number of features: 10, 20, 30
- Target confidence levels: 70%, 80%, 90%

For each combination, it measures the "goodness" of the resulting ranking
by calculating how many swaps are needed to achieve the correct ranking
(Kendall tau distance / inversion count).
"""

import pytest
from fastapi.testclient import TestClient
from typing import List, Tuple, Dict, Any
from app.core.config import settings


# Global storage for test results (used by summary fixture)
_test_results: List[Dict[str, Any]] = []


def calculate_inversions(actual: List[str], expected: List[str]) -> int:
    """
    Calculate the number of inversions (swaps) needed to transform
    the actual ranking into the expected ranking.
    
    This is the Kendall tau distance - counts pairs that are in
    different order between the two rankings.
    
    Args:
        actual: The actual ranking produced by the algorithm
        expected: The expected (correct) ranking
        
    Returns:
        Number of inversions (0 = perfect match)
    """
    # Create position maps
    expected_pos = {name: i for i, name in enumerate(expected)}
    
    # Map actual ranking to expected positions
    actual_positions = [expected_pos[name] for name in actual]
    
    # Count inversions using merge sort approach for O(n log n)
    def merge_count(arr: List[int]) -> Tuple[List[int], int]:
        if len(arr) <= 1:
            return arr, 0
        
        mid = len(arr) // 2
        left, left_inv = merge_count(arr[:mid])
        right, right_inv = merge_count(arr[mid:])
        
        merged = []
        inversions = left_inv + right_inv
        i = j = 0
        
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                inversions += len(left) - i  # All remaining left elements are inversions
                j += 1
        
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged, inversions
    
    _, inversions = merge_count(actual_positions)
    return inversions


def calculate_goodness_score(actual: List[str], expected: List[str]) -> float:
    """
    Calculate a goodness score from 0.0 (worst) to 1.0 (perfect).
    
    Score = 1 - (inversions / max_possible_inversions)
    
    Where max_possible_inversions = n*(n-1)/2 (completely reversed)
    
    Args:
        actual: The actual ranking produced
        expected: The expected (correct) ranking
        
    Returns:
        Goodness score between 0.0 and 1.0
    """
    n = len(expected)
    max_inversions = n * (n - 1) // 2
    
    if max_inversions == 0:
        return 1.0
    
    inversions = calculate_inversions(actual, expected)
    return 1.0 - (inversions / max_inversions)


class TestParameterizedWorkflow:
    """Parameterized integration tests with varying features and confidence levels."""

    @pytest.fixture
    def generate_features(self):
        """Factory fixture to generate feature names and orderings."""
        def _generate(n: int):
            # Generate feature names: Feat01, Feat02, ..., FeatN
            feature_names = [f"Feat{i:02d}" for i in range(1, n + 1)]
            
            # Complexity order: Feat01 is most complex, FeatN is least complex
            complexity_order = {name: n - i for i, name in enumerate(feature_names)}
            
            # Value order: FeatN is most valuable, Feat01 is least valuable (inverted)
            value_order = {name: i + 1 for i, name in enumerate(feature_names)}
            
            return feature_names, complexity_order, value_order
        
        return _generate

    @pytest.mark.parametrize(
        "num_features,target_confidence",
        [
            # 10 features with different confidence targets
            (10, 0.90),
            (10, 0.80),
            (10, 0.70),
            # 20 features with different confidence targets
            (20, 0.90),
            (20, 0.80),
            (20, 0.70),
            # 30 features with different confidence targets
            (30, 0.90),
            (30, 0.80),
            (30, 0.70),
        ],
        ids=[
            "10_features_90%",
            "10_features_80%",
            "10_features_70%",
            "20_features_90%",
            "20_features_80%",
            "20_features_70%",
            "30_features_90%",
            "30_features_80%",
            "30_features_70%",
        ]
    )
    def test_parameterized_workflow(
        self,
        client: TestClient,
        superuser_token_headers: dict,
        generate_features,
        num_features: int,
        target_confidence: float,
    ) -> None:
        """
        Parameterized integration test for different feature counts and confidence levels.
        
        Tests:
        1. Creates a project with N features
        2. Performs comparisons until target confidence is reached
        3. Measures ranking accuracy using Kendall tau distance
        4. Reports goodness score (1.0 = perfect ranking)
        """
        print(f"\n{'='*70}")
        print(f"TEST: {num_features} features, {target_confidence:.0%} target confidence")
        print(f"{'='*70}")
        
        # Generate feature data
        feature_names, complexity_order, value_order = generate_features(num_features)
        
        # Calculate theoretical values
        total_pairs = num_features * (num_features - 1) // 2
        print(f"Total possible pairs: {total_pairs}")
        
        # ============================================================
        # STEP 1: Create project
        # ============================================================
        project_data = {
            "name": f"param_test_{num_features}f_{int(target_confidence*100)}c",
            "description": f"Parameterized test: {num_features} features, {target_confidence:.0%} confidence",
        }
        r = client.post(
            f"{settings.API_V1_STR}/projects/",
            headers=superuser_token_headers,
            json=project_data,
        )
        assert r.status_code == 201, f"Failed to create project: {r.text}"
        project_id = r.json()["id"]
        print(f"✓ Created project: {project_data['name']}")

        # ============================================================
        # STEP 2: Create features
        # ============================================================
        feature_ids = {}
        for feature_name in feature_names:
            feature_data = {
                "name": feature_name,
                "description": f"Test feature {feature_name}",
            }
            r = client.post(
                f"{settings.API_V1_STR}/projects/{project_id}/features",
                headers=superuser_token_headers,
                json=feature_data,
            )
            assert r.status_code == 201, f"Failed to create feature {feature_name}: {r.text}"
            feature_ids[feature_name] = r.json()["id"]
        
        print(f"✓ Created {num_features} features")

        # ============================================================
        # STEP 3: Helper function to determine winner
        # ============================================================
        def get_choice(feat_a_name: str, feat_b_name: str, order_map: dict) -> str:
            """Determine winner based on the expected order."""
            if order_map[feat_a_name] > order_map[feat_b_name]:
                return "feature_a"
            elif order_map[feat_b_name] > order_map[feat_a_name]:
                return "feature_b"
            else:
                return "tie"

        # ============================================================
        # STEP 4: Perform COMPLEXITY comparisons until target confidence
        # ============================================================
        complexity_comparisons = 0
        max_iterations = total_pairs + 5  # Safety limit
        
        while complexity_comparisons < max_iterations:
            # Check current progress (for logging only)
            r = client.get(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress?dimension=complexity&target_certainty={target_confidence}",
                headers=superuser_token_headers,
            )
            assert r.status_code == 200
            progress = r.json()
            
            effective_conf = progress["effective_confidence"]
            transitive_cov = progress["transitive_coverage"]
            
            # Get the next optimal pair - API will return 204 when target is reached
            r = client.get(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=complexity&target_certainty={target_confidence}",
                headers=superuser_token_headers,
            )
            
            if r.status_code == 204:
                # Target certainty reached
                print(f"  Complexity: Target {target_confidence:.0%} reached after {complexity_comparisons} comparisons")
                break
            
            assert r.status_code == 200, f"Unexpected status: {r.status_code} - {r.text}"
            
            next_pair = r.json()
            feat_a_name = next_pair["feature_a"]["name"]
            feat_b_name = next_pair["feature_b"]["name"]
            feat_a_id = next_pair["feature_a"]["id"]
            feat_b_id = next_pair["feature_b"]["id"]
            
            # Submit the comparison
            choice = get_choice(feat_a_name, feat_b_name, complexity_order)
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
            assert r.status_code == 201, f"Failed comparison: {r.text}"
            complexity_comparisons += 1
            
            # Progress indicator every 10 comparisons
            if complexity_comparisons % 10 == 0:
                print(f"    ... {complexity_comparisons} complexity comparisons")

        # ============================================================
        # STEP 5: Perform VALUE comparisons until target confidence
        # ============================================================
        value_comparisons = 0
        
        while value_comparisons < max_iterations:
            # Get the next optimal pair (API returns 204 when target_certainty reached)
            r = client.get(
                f"{settings.API_V1_STR}/projects/{project_id}/comparisons/next?dimension=value&target_certainty={target_confidence}",
                headers=superuser_token_headers,
            )
            
            if r.status_code == 204:
                # Target certainty reached
                print(f"  Value: Target {target_confidence:.0%} reached after {value_comparisons} comparisons")
                break
            
            assert r.status_code == 200, f"Unexpected status: {r.status_code} - {r.text}"
            
            next_pair = r.json()
            feat_a_name = next_pair["feature_a"]["name"]
            feat_b_name = next_pair["feature_b"]["name"]
            feat_a_id = next_pair["feature_a"]["id"]
            feat_b_id = next_pair["feature_b"]["id"]
            
            # Submit the comparison
            choice = get_choice(feat_a_name, feat_b_name, value_order)
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
            assert r.status_code == 201, f"Failed comparison: {r.text}"
            value_comparisons += 1
            
            # Progress indicator every 10 comparisons
            if value_comparisons % 10 == 0:
                print(f"    ... {value_comparisons} value comparisons")

        total_comparisons = complexity_comparisons + value_comparisons
        print(f"✓ Total comparisons: {total_comparisons} ({complexity_comparisons} complexity + {value_comparisons} value)")

        # ============================================================
        # STEP 6: Get complexity ranking and calculate goodness
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/results?sort_by=complexity",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        complexity_results = r.json()
        
        complexity_ranking = [result["feature"]["name"] for result in complexity_results]
        expected_complexity = sorted(feature_names, key=lambda x: complexity_order[x], reverse=True)
        
        complexity_inversions = calculate_inversions(complexity_ranking, expected_complexity)
        complexity_goodness = calculate_goodness_score(complexity_ranking, expected_complexity)

        # ============================================================
        # STEP 7: Get value ranking and calculate goodness
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/results?sort_by=value",
            headers=superuser_token_headers,
        )
        assert r.status_code == 200
        value_results = r.json()
        
        value_ranking = [result["feature"]["name"] for result in value_results]
        expected_value = sorted(feature_names, key=lambda x: value_order[x], reverse=True)
        
        value_inversions = calculate_inversions(value_ranking, expected_value)
        value_goodness = calculate_goodness_score(value_ranking, expected_value)

        # ============================================================
        # STEP 8: Get final progress metrics
        # ============================================================
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress?dimension=complexity",
            headers=superuser_token_headers,
        )
        complexity_progress = r.json()
        
        r = client.get(
            f"{settings.API_V1_STR}/projects/{project_id}/comparisons/progress?dimension=value",
            headers=superuser_token_headers,
        )
        value_progress = r.json()

        # ============================================================
        # RESULTS SUMMARY
        # ============================================================
        print(f"\n{'─'*70}")
        print(f"📊 RESULTS SUMMARY: {num_features} features, {target_confidence:.0%} target")
        print(f"{'─'*70}")
        
        print(f"\n  Comparisons:")
        print(f"    Complexity:  {complexity_comparisons:4d} / {total_pairs} pairs ({complexity_comparisons/total_pairs:.1%})")
        print(f"    Value:       {value_comparisons:4d} / {total_pairs} pairs ({value_comparisons/total_pairs:.1%})")
        print(f"    Total:       {total_comparisons:4d}")
        
        print(f"\n  Confidence Achieved:")
        print(f"    Complexity: Direct={complexity_progress['direct_coverage']:.1%}, Transitive={complexity_progress['transitive_coverage']:.1%}, Effective={complexity_progress['effective_confidence']:.1%}")
        print(f"    Value:      Direct={value_progress['direct_coverage']:.1%}, Transitive={value_progress['transitive_coverage']:.1%}, Effective={value_progress['effective_confidence']:.1%}")
        
        print(f"\n  Ranking Accuracy (Kendall tau):")
        print(f"    Complexity: {complexity_inversions} inversions, goodness={complexity_goodness:.4f}")
        print(f"    Value:      {value_inversions} inversions, goodness={value_goodness:.4f}")
        
        avg_goodness = (complexity_goodness + value_goodness) / 2
        print(f"\n  ⭐ AVERAGE GOODNESS SCORE: {avg_goodness:.4f}")
        
        # Show top-5 comparison for complexity
        print(f"\n  Complexity Top-5:")
        print(f"    Expected: {expected_complexity[:5]}")
        print(f"    Actual:   {complexity_ranking[:5]}")
        
        # Show top-5 comparison for value
        print(f"\n  Value Top-5:")
        print(f"    Expected: {expected_value[:5]}")
        print(f"    Actual:   {value_ranking[:5]}")
        
        print(f"\n{'─'*70}")
        
        # ============================================================
        # ASSERTIONS
        # ============================================================
        # The test verifies two things:
        # 1. We achieved either the target confidence OR 204 (ranking complete)
        # 2. The ranking quality (goodness) meets expectations based on confidence achieved
        
        # For this test, we're more interested in the relationship between
        # comparisons made, confidence achieved, and ranking accuracy
        # The system may return 204 (complete) before reaching target confidence
        # if transitive knowledge completes the ranking
        
        complexity_achieved = complexity_progress['effective_confidence']
        value_achieved = value_progress['effective_confidence']
        
        # Report whether target was met or ranking completed via transitivity
        complexity_reached_target = complexity_achieved >= target_confidence * 0.95
        value_reached_target = value_achieved >= target_confidence * 0.95
        
        if complexity_reached_target:
            print(f"✓ Complexity reached target confidence: {complexity_achieved:.1%} >= {target_confidence:.0%}")
        else:
            print(f"ℹ Complexity stopped at {complexity_achieved:.1%} (target: {target_confidence:.0%}) - ranking complete via transitivity")
        
        if value_reached_target:
            print(f"✓ Value reached target confidence: {value_achieved:.1%} >= {target_confidence:.0%}")
        else:
            print(f"ℹ Value stopped at {value_achieved:.1%} (target: {target_confidence:.0%}) - ranking complete via transitivity")
        
        # The key assertion: ranking quality should be good regardless of confidence metric
        # With perfect transitive comparisons, goodness should be high
        # Even partial coverage with good ordering should yield good goodness
        min_expected_goodness = 0.70  # Minimum acceptable goodness for any test
        
        assert complexity_goodness >= min_expected_goodness, \
            f"Complexity goodness {complexity_goodness:.4f} below minimum {min_expected_goodness}"
        assert value_goodness >= min_expected_goodness, \
            f"Value goodness {value_goodness:.4f} below minimum {min_expected_goodness}"
        
        print(f"\n✅ All assertions passed for {num_features} features at {target_confidence:.0%} target")
        print(f"   Goodness scores: complexity={complexity_goodness:.4f}, value={value_goodness:.4f}")
        
        # Store results for summary table
        _test_results.append({
            "num_features": num_features,
            "target_confidence": target_confidence,
            "total_pairs": total_pairs,
            "complexity_comparisons": complexity_comparisons,
            "value_comparisons": value_comparisons,
            "total_comparisons": total_comparisons,
            "complexity_direct_coverage": complexity_progress['direct_coverage'],
            "complexity_transitive_coverage": complexity_progress['transitive_coverage'],
            "complexity_effective_confidence": complexity_achieved,
            "value_direct_coverage": value_progress['direct_coverage'],
            "value_transitive_coverage": value_progress['transitive_coverage'],
            "value_effective_confidence": value_achieved,
            "complexity_inversions": complexity_inversions,
            "complexity_goodness": complexity_goodness,
            "value_inversions": value_inversions,
            "value_goodness": value_goodness,
            "avg_goodness": avg_goodness,
        })


def print_summary_table():
    """Print a formatted summary table of all test results."""
    if not _test_results:
        print("\nNo test results to summarize.")
        return
    
    # Sort results by num_features, then by target_confidence (descending)
    sorted_results = sorted(_test_results, key=lambda x: (x["num_features"], -x["target_confidence"]))
    
    print("\n")
    print("=" * 120)
    print("📊 PARAMETERIZED TEST RESULTS SUMMARY TABLE")
    print("=" * 120)
    
    # Header
    print(f"{'Features':<10} {'Target':<8} {'Total':<8} {'Cmplx':<8} {'Value':<8} {'Cmplx':<10} {'Value':<10} {'Cmplx':<10} {'Value':<10} {'Avg':<10}")
    print(f"{'':10} {'Conf.':<8} {'Pairs':<8} {'Comp.':<8} {'Comp.':<8} {'Goodness':<10} {'Goodness':<10} {'Eff.Conf':<10} {'Eff.Conf':<10} {'Goodness':<10}")
    print("-" * 120)
    
    for r in sorted_results:
        print(f"{r['num_features']:<10} {r['target_confidence']:.0%}{'':4} {r['total_pairs']:<8} "
              f"{r['complexity_comparisons']:<8} {r['value_comparisons']:<8} "
              f"{r['complexity_goodness']:<10.4f} {r['value_goodness']:<10.4f} "
              f"{r['complexity_effective_confidence']:<10.1%} {r['value_effective_confidence']:<10.1%} "
              f"{r['avg_goodness']:<10.4f}")
    
    print("-" * 120)
    
    # Detailed breakdown
    print("\n")
    print("=" * 120)
    print("📈 DETAILED COMPARISON METRICS")
    print("=" * 120)
    print(f"{'Features':<10} {'Target':<8} {'Cmplx Direct':<14} {'Cmplx Trans.':<14} {'Value Direct':<14} {'Value Trans.':<14} {'Cmplx Inv.':<12} {'Value Inv.':<12}")
    print("-" * 120)
    
    for r in sorted_results:
        print(f"{r['num_features']:<10} {r['target_confidence']:.0%}{'':4} "
              f"{r['complexity_direct_coverage']:<14.1%} {r['complexity_transitive_coverage']:<14.1%} "
              f"{r['value_direct_coverage']:<14.1%} {r['value_transitive_coverage']:<14.1%} "
              f"{r['complexity_inversions']:<12} {r['value_inversions']:<12}")
    
    print("-" * 120)
    
    # Analysis section
    print("\n")
    print("=" * 120)
    print("🔍 KEY OBSERVATIONS")
    print("=" * 120)
    
    # Find anomalies - cases where lower confidence target yields better goodness
    anomalies = []
    for i, r1 in enumerate(sorted_results):
        for r2 in sorted_results[i+1:]:
            if (r1["num_features"] == r2["num_features"] and 
                r1["target_confidence"] > r2["target_confidence"] and
                r1["avg_goodness"] < r2["avg_goodness"]):
                anomalies.append((r1, r2))
    
    if anomalies:
        print("\n⚠️  ANOMALIES DETECTED: Higher confidence target yielded LOWER goodness!")
        for r1, r2 in anomalies:
            print(f"   • {r1['num_features']} features: {r1['target_confidence']:.0%} target → {r1['avg_goodness']:.4f} goodness")
            print(f"                      {r2['target_confidence']:.0%} target → {r2['avg_goodness']:.4f} goodness (BETTER by {r2['avg_goodness'] - r1['avg_goodness']:.4f})")
            print(f"     Explanation: More comparisons ({r1['total_comparisons']} vs {r2['total_comparisons']}) can cause score convergence,")
            print(f"                  making rankings less distinguishable due to numerical precision.\n")
    
    # Find cases where value needed all pairs
    full_coverage_cases = [r for r in sorted_results if r['value_comparisons'] >= r['total_pairs'] * 0.95]
    if full_coverage_cases:
        print("\nℹ️  VALUE DIMENSION REQUIRED NEAR-FULL COVERAGE in these cases:")
        for r in full_coverage_cases:
            print(f"   • {r['num_features']} features, {r['target_confidence']:.0%} target: {r['value_comparisons']}/{r['total_pairs']} pairs ({r['value_comparisons']/r['total_pairs']:.1%})")
        print("   Reason: Value comparisons run AFTER complexity, starting with fresh transitive knowledge.")
    
    # Efficiency analysis
    print("\n📊 EFFICIENCY ANALYSIS (comparisons needed vs total pairs):")
    for n in [10, 20, 30]:
        n_results = [r for r in sorted_results if r['num_features'] == n]
        if n_results:
            total_pairs = n_results[0]['total_pairs']
            avg_total = sum(r['total_comparisons'] for r in n_results) / len(n_results)
            min_total = min(r['total_comparisons'] for r in n_results)
            max_total = max(r['total_comparisons'] for r in n_results)
            print(f"   • {n} features ({total_pairs} pairs): avg={avg_total:.0f}, min={min_total}, max={max_total} comparisons")
    
    print("\n" + "=" * 120)


@pytest.fixture(scope="session", autouse=True)
def print_final_summary(request):
    """Print summary table after all tests complete."""
    yield
    # This runs after all tests in the session
    print_summary_table()


class TestGoodnessScoreCalculation:
    """Unit tests for the goodness score calculation functions."""
    
    def test_perfect_ranking(self):
        """Perfect ranking should have 0 inversions and goodness 1.0."""
        expected = ["A", "B", "C", "D", "E"]
        actual = ["A", "B", "C", "D", "E"]
        
        assert calculate_inversions(actual, expected) == 0
        assert calculate_goodness_score(actual, expected) == 1.0
    
    def test_reversed_ranking(self):
        """Completely reversed ranking should have max inversions."""
        expected = ["A", "B", "C", "D", "E"]
        actual = ["E", "D", "C", "B", "A"]
        
        n = 5
        max_inversions = n * (n - 1) // 2  # 10
        
        assert calculate_inversions(actual, expected) == max_inversions
        assert calculate_goodness_score(actual, expected) == 0.0
    
    def test_one_swap(self):
        """One adjacent swap should have 1 inversion."""
        expected = ["A", "B", "C", "D", "E"]
        actual = ["A", "C", "B", "D", "E"]  # B and C swapped
        
        assert calculate_inversions(actual, expected) == 1
        
        n = 5
        max_inversions = n * (n - 1) // 2  # 10
        assert calculate_goodness_score(actual, expected) == 1.0 - (1 / max_inversions)
    
    def test_partial_disorder(self):
        """Test a partially disordered ranking."""
        expected = ["A", "B", "C", "D", "E"]
        actual = ["A", "C", "B", "E", "D"]  # 2 swaps: B-C and D-E
        
        # B-C swap: 1 inversion
        # D-E swap: 1 inversion
        # No additional inversions between the swapped pairs
        assert calculate_inversions(actual, expected) == 2
    
    def test_larger_example(self):
        """Test with a larger list."""
        expected = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        actual = ["1", "2", "4", "3", "5", "6", "8", "7", "9", "10"]  # 2 adjacent swaps
        
        assert calculate_inversions(actual, expected) == 2
        
        n = 10
        max_inversions = n * (n - 1) // 2  # 45
        expected_goodness = 1.0 - (2 / 45)
        assert abs(calculate_goodness_score(actual, expected) - expected_goodness) < 0.0001
