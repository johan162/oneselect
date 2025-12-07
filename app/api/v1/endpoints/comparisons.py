from typing import Any, List, Optional, Dict, Set, Tuple
import math
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.config import settings

router = APIRouter()


def _compute_transitive_closure(
    comparisons: list, feature_ids: List[str]
) -> Dict[str, Set[str]]:
    """
    Compute the transitive closure of comparison relationships.

    PURPOSE & MOTIVATION:
    ---------------------
    This is the core algorithm that makes efficient feature ranking possible.
    It implements the mathematical concept of "transitive closure" - expanding
    a set of direct relationships to include all implied indirect relationships.

    The key insight: humans naturally understand transitivity. If you know that:
    - Alice is taller than Bob
    - Bob is taller than Charlie
    Then you automatically know Alice is taller than Charlie WITHOUT measuring.

    This function automates that inference for feature comparisons, dramatically
    reducing the number of comparisons users need to make.

    COMPLEXITY REDUCTION:
    ---------------------
    Without transitivity: n*(n-1)/2 comparisons needed (all pairs)
    With transitivity:    ~n*log₂(n) comparisons needed (like merge sort)

    | Features | Naive O(n²) | With Transitivity | Savings |
    |----------|-------------|-------------------|---------|
    | 10       | 45          | ~33               | 27%     |
    | 30       | 435         | ~147              | 66%     |
    | 100      | 4,950       | ~664              | 87%     |

    THE ALGORITHM (Warshall's Algorithm):
    -------------------------------------
    1. Start with direct edges: A→B means "A beats B directly"
    2. Iterate until no changes:
       - For each feature A that beats B
       - And each feature C that B beats
       - Add edge A→C (A transitively beats C)

    Example walkthrough:
        Input comparisons: A>B, B>C, B>D

        Initial graph:     A → B → C
                               ↓
                               D

        Iteration 1:
        - A beats B, B beats C → Add A→C
        - A beats B, B beats D → Add A→D

        Final graph:       A → B → C
                           ↓   ↓
                           C   D
                           ↓
                           D

        Result: greater_than = {
            "A": {"B", "C", "D"},  # A beats all three
            "B": {"C", "D"},       # B beats C and D
        }

    WHERE IT'S USED:
    ----------------
    1. _compute_transitive_knowledge(): Wraps this to count known vs unknown pairs
    2. _get_optimal_next_pair_transitive(): Uses it to find pairs NOT yet determined
    3. Indirectly powers the /next and /progress endpoints

    IMPORTANT NOTES:
    ----------------
    - Ties are skipped (they don't establish ordering)
    - Cycles (A>B>C>A) indicate user inconsistency, handled separately
    - Time complexity: O(n³) worst case, but typically much faster with sparse graphs

    Args:
        comparisons: List of comparison objects with feature_a_id, feature_b_id, choice
        feature_ids: List of all feature IDs in the project

    Returns:
        Dict mapping each feature to the set of features it is greater than (transitively)
        e.g., {"A": {"B", "C", "D"}, "B": {"C", "D"}, ...}
    """
    # Build direct "greater than" relationships from comparisons
    # greater_than[X] = set of features that X beats directly
    greater_than: Dict[str, Set[str]] = defaultdict(set)

    for comp in comparisons:
        if comp.choice == "tie":
            continue

        if comp.choice == "feature_a":
            winner = str(comp.feature_a_id)
            loser = str(comp.feature_b_id)
        else:
            winner = str(comp.feature_b_id)
            loser = str(comp.feature_a_id)

        greater_than[winner].add(loser)

    # Compute transitive closure using Warshall's algorithm
    # If A > B and B > C, then A > C
    feature_set = set(str(fid) for fid in feature_ids)

    # Keep expanding until no new relationships found
    changed = True
    while changed:
        changed = False
        for a in feature_set:
            # For each feature B that A beats
            for b in list(greater_than[a]):
                # A also beats everything that B beats
                for c in greater_than[b]:
                    if c not in greater_than[a] and c != a:
                        greater_than[a].add(c)
                        changed = True

    return dict(greater_than)


def _compute_transitive_knowledge(
    comparisons: list, feature_ids: List[str]
) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]], int]:
    """
    Compute what we know about feature ordering via direct and transitive relationships.

    PURPOSE & MOTIVATION:
    ---------------------
    This function is a key optimization that enables the comparison system to determine
    feature rankings with far fewer comparisons than a naive approach would require.

    Without transitivity, ranking n features requires comparing every possible pair:
    n*(n-1)/2 comparisons (e.g., 435 comparisons for 30 features).

    But humans naturally understand transitivity: if A > B and B > C, then A > C.
    This function leverages that property to infer orderings without asking the user.

    With transitivity, only ~n*log₂(n) comparisons are needed (e.g., ~147 for 30 features),
    representing a 66% reduction in user effort.

    HOW IT WORKS:
    -------------
    1. Extracts direct comparison pairs from user input (who beat whom)
    2. Calls _compute_transitive_closure() to infer all implied orderings using
       Warshall's algorithm (if A>B and B>C, infer A>C)
    3. Counts how many of the n*(n-1)/2 possible pairs have known orderings
    4. Returns the count of pairs we still DON'T know about (uncertain_pairs_count)

    Example:
        User comparisons:     A > B,  B > C,  D > E
        Direct pairs:         {(A,B), (B,C), (D,E)}
        Transitive inference: A > C  (inferred!)
        Known pairs:          {(A,B), (B,C), (A,C), (D,E)}  -- 4 pairs known
        Total possible:       5*(5-1)/2 = 10 pairs
        Uncertain:            6 pairs (A vs D, A vs E, B vs D, B vs E, C vs D, C vs E)

    WHERE IT'S USED:
    ----------------
    1. get_next_comparison_pair(): Checks if target certainty is reached via
       transitive_coverage; returns 204 when uncertain_count == 0
    2. _get_optimal_next_pair_transitive(): Only suggests comparing pairs that
       will provide NEW information (not already known via transitivity)
    3. get_comparison_progress(): Calculates transitive_coverage as the key
       metric showing "what fraction of the ranking do we know"

    Args:
        comparisons: List of comparison objects with feature_a_id, feature_b_id, choice
        feature_ids: List of all feature IDs in the project

    Returns:
        Tuple of:
        - direct_pairs: Set of (winner, loser) from direct comparisons
        - known_pairs: Set of all (higher, lower) pairs including transitive inferences
        - uncertain_pairs_count: Number of pairs we still don't know the ordering for
    """
    n = len(feature_ids)
    total_pairs = n * (n - 1) // 2

    if total_pairs == 0:
        return set(), set(), 0

    # Get direct comparison pairs
    direct_pairs: Set[Tuple[str, str]] = set()
    for comp in comparisons:
        if comp.choice == "tie":
            continue
        if comp.choice == "feature_a":
            direct_pairs.add((str(comp.feature_a_id), str(comp.feature_b_id)))
        else:
            direct_pairs.add((str(comp.feature_b_id), str(comp.feature_a_id)))

    # Compute transitive closure
    greater_than = _compute_transitive_closure(comparisons, feature_ids)

    # Build set of all known ordered pairs (including transitive)
    known_pairs: Set[Tuple[str, str]] = set()
    for winner, losers in greater_than.items():
        for loser in losers:
            # Normalize pair as (higher, lower)
            known_pairs.add((winner, loser))

    # Count pairs where we know the ordering
    # We count each unordered pair once (either (A,B) or (B,A) tells us the order)
    known_unordered_pairs: Set[Tuple[str, str]] = set()
    for winner, loser in known_pairs:
        pair = tuple(sorted([winner, loser]))
        known_unordered_pairs.add(pair)

    known_pair_count = len(known_unordered_pairs)
    uncertain_pairs_count = total_pairs - known_pair_count

    return direct_pairs, known_pairs, uncertain_pairs_count


def _get_optimal_next_pair_transitive(
    feature_ids: List[str],
    features_by_id: Dict[str, Any],
    comparisons: list,
    dimension: str,
) -> Optional[Tuple[Any, Any, float]]:
    """
    Use transitive knowledge to find the most informative pair to compare next.

    Prioritizes pairs where:
    1. We don't know the ordering (not determined by transitivity)
    2. Comparing would maximize transitive information gain

    This is inspired by merge-sort: compare items that are "adjacent" in our
    current knowledge to efficiently determine the full ordering.

    Returns:
        Tuple of (feature_a, feature_b, selection_score) or None if all pairs known
    """
    if len(feature_ids) < 2:
        return None

    # Get current transitive knowledge
    greater_than = _compute_transitive_closure(comparisons, feature_ids)

    # Build set of pairs where we know the ordering
    known_pairs: Set[Tuple[str, str]] = set()
    for winner, losers in greater_than.items():
        for loser in losers:
            pair = tuple(sorted([winner, loser]))
            known_pairs.add(pair)

    # Find pairs where we DON'T know the ordering
    unknown_pairs: List[Tuple[str, str]] = []
    for i, a in enumerate(feature_ids):
        for b in feature_ids[i + 1 :]:
            pair = tuple(sorted([a, b]))
            if pair not in known_pairs:
                unknown_pairs.append((a, b))

    if not unknown_pairs:
        return None  # All pairs determined!

    # Score each unknown pair by expected information gain
    #
    # We use a hybrid approach:
    # 1. Traditional active learning (uncertainty × closeness) for ranking quality
    # 2. Connectivity bonus to encourage chain building for transitivity
    #
    # The key insight: features with existing comparisons have more reliable mu values,
    # so comparing them gives better information. But we also need to eventually
    # compare all features to build complete chains.

    # Count how many direct comparisons each feature has participated in
    comparison_count = defaultdict(int)
    for comp in comparisons:
        comparison_count[str(comp.feature_a_id)] += 1
        comparison_count[str(comp.feature_b_id)] += 1

    best_pair = None
    best_score = -1.0
    c = 2.0  # Scaling factor for closeness

    for a_id, b_id in unknown_pairs:
        feat_a = features_by_id[a_id]
        feat_b = features_by_id[b_id]

        # Get current mu and sigma
        if dimension == "complexity":
            mu_a, sigma_a = feat_a.complexity_mu, feat_a.complexity_sigma
            mu_b, sigma_b = feat_b.complexity_mu, feat_b.complexity_sigma
        else:
            mu_a, sigma_a = feat_a.value_mu, feat_a.value_sigma
            mu_b, sigma_b = feat_b.value_mu, feat_b.value_sigma

        # Traditional active learning score
        uncertainty = sigma_a + sigma_b
        mu_diff = mu_a - mu_b
        closeness = math.exp(-(mu_diff**2) / (2 * c**2))
        active_learning_score = uncertainty * closeness

        # Connectivity bonus: prefer pairs where at least one feature has comparisons
        # This helps build connected knowledge that enables transitivity
        a_comps = comparison_count[a_id]
        b_comps = comparison_count[b_id]

        # Prioritize: one has comparisons, other doesn't (extends knowledge)
        # Secondary: both have comparisons (links existing knowledge)
        # Tertiary: neither has comparisons (cold start)
        if (a_comps > 0) != (b_comps > 0):  # XOR - one has, one doesn't
            connectivity_bonus = 1.2  # Extends a chain
        elif a_comps > 0 and b_comps > 0:
            connectivity_bonus = 1.1  # Links existing knowledge
        else:
            connectivity_bonus = 1.0  # Cold start

        # Combined score
        selection_score = active_learning_score * connectivity_bonus

        if selection_score > best_score:
            best_score = selection_score
            best_pair = (feat_a, feat_b, selection_score)

    return best_pair


def _calculate_inconsistency_stats(
    db: Session, project_id: str, dimension: Optional[str] = None
) -> dict:
    """
    Calculate inconsistency statistics for a project.

    Returns:
        dict with keys:
        - cycle_count: Number of detected cycles
        - total_comparisons: Total comparisons for dimension(s)
        - inconsistency_percentage: Percentage of comparisons involved in cycles
        - dimension: The dimension analyzed
    """
    # Get all active comparisons
    comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)

    # Filter by dimension if specified
    if dimension:
        comparisons = [c for c in comparisons if c.dimension == dimension]

    total_comparisons = len(comparisons)

    if total_comparisons == 0:
        return {
            "cycle_count": 0,
            "total_comparisons": 0,
            "inconsistency_percentage": 0.0,
            "dimension": dimension or "all",
        }

    # Build directed graph
    graph = {}
    comparison_map = {}  # Map (winner, loser) -> comparison id

    for comp in comparisons:
        if comp.choice == "tie":
            continue

        winner_id = str(
            comp.feature_a_id if comp.choice == "feature_a" else comp.feature_b_id
        )
        loser_id = str(
            comp.feature_b_id if comp.choice == "feature_a" else comp.feature_a_id
        )

        if winner_id not in graph:
            graph[winner_id] = set()
        if loser_id not in graph:
            graph[loser_id] = set()

        graph[winner_id].add(loser_id)
        comparison_map[(winner_id, loser_id)] = str(comp.id)

    # Detect cycles
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in all_cycles:
                    all_cycles.append(normalized)

        path.pop()
        rec_stack.remove(node)

    cycles_found = []
    visited_global = set()

    for node in graph:
        if node not in visited_global:
            find_cycles_dfs(node, [], visited_global, set(), cycles_found)

    # Count unique comparisons involved in cycles
    comparisons_in_cycles = set()
    for cycle in cycles_found:
        for i in range(len(cycle)):
            winner = cycle[i]
            loser = cycle[(i + 1) % len(cycle)]
            edge = (winner, loser)
            if edge in comparison_map:
                comparisons_in_cycles.add(comparison_map[edge])

    # Calculate percentage
    inconsistency_percentage = (
        (len(comparisons_in_cycles) / total_comparisons * 100)
        if total_comparisons > 0
        else 0.0
    )

    return {
        "cycle_count": len(cycles_found),
        "total_comparisons": total_comparisons,
        "inconsistency_percentage": round(inconsistency_percentage, 2),
        "dimension": dimension or "all",
    }


def _recalculate_bayesian_scores(db: Session, project_id: str, dimension: str) -> None:
    """
    Reset and recalculate all Bayesian scores for a dimension by replaying comparisons.

    This function should be called after removing a comparison (undo or delete)
    to ensure feature scores and project variance are consistent with the
    remaining comparisons.

    Args:
        db: Database session
        project_id: Project ID
        dimension: "complexity" or "value"
    """
    from app import crud

    # Get project and features
    project = crud.project.get(db=db, id=project_id)
    if not project:
        return

    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    if not features:
        return

    # Reset all features to initial state for this dimension
    for feature in features:
        if dimension == "complexity":
            feature.complexity_mu = 0.0
            feature.complexity_sigma = 1.0
        else:  # value
            feature.value_mu = 0.0
            feature.value_sigma = 1.0
        db.add(feature)

    # Get remaining comparisons for this dimension
    remaining_comparisons = crud.comparison.get_multi_by_project(
        db=db, project_id=project_id
    )
    remaining_filtered = [c for c in remaining_comparisons if c.dimension == dimension]

    # Sort by created_at ascending to replay in order
    remaining_filtered = sorted(remaining_filtered, key=lambda c: c.created_at)

    # Replay all comparisons to rebuild scores
    features_by_id = {str(f.id): f for f in features}

    LAMBDA = math.pi / 8
    KAPPA = 0.01

    for comp in remaining_filtered:
        feature_a = features_by_id.get(str(comp.feature_a_id))
        feature_b = features_by_id.get(str(comp.feature_b_id))

        if not feature_a or not feature_b:
            continue

        # Get current scores
        if dimension == "complexity":
            mu_a, sigma_a = feature_a.complexity_mu, feature_a.complexity_sigma
            mu_b, sigma_b = feature_b.complexity_mu, feature_b.complexity_sigma
        else:
            mu_a, sigma_a = feature_a.value_mu, feature_a.value_sigma
            mu_b, sigma_b = feature_b.value_mu, feature_b.value_sigma

        # Determine outcome
        if comp.choice == "feature_a":
            y = 1.0
        elif comp.choice == "feature_b":
            y = 0.0
        else:
            y = 0.5

        # Bayesian update
        try:
            p_hat = 1.0 / (1.0 + math.exp(-(mu_a - mu_b)))
        except OverflowError:
            p_hat = 1.0 if mu_a > mu_b else 0.0

        delta = y - p_hat
        variance_term = p_hat * (1.0 - p_hat)
        if variance_term < 1e-10:
            variance_term = 1e-10

        denominator = math.sqrt(1.0 + LAMBDA * variance_term)
        sigma_a_squared = sigma_a**2
        sigma_b_squared = sigma_b**2

        new_mu_a = mu_a + (sigma_a_squared * delta) / denominator
        new_mu_b = mu_b - (sigma_b_squared * delta) / denominator

        variance_reduction_a = 1.0 - (sigma_a_squared * variance_term) / (
            1.0 + LAMBDA * variance_term
        )
        variance_reduction_b = 1.0 - (sigma_b_squared * variance_term) / (
            1.0 + LAMBDA * variance_term
        )

        new_sigma_a = math.sqrt(max(sigma_a_squared * variance_reduction_a, KAPPA))
        new_sigma_b = math.sqrt(max(sigma_b_squared * variance_reduction_b, KAPPA))

        # Apply updates
        if dimension == "complexity":
            feature_a.complexity_mu = new_mu_a
            feature_a.complexity_sigma = new_sigma_a
            feature_b.complexity_mu = new_mu_b
            feature_b.complexity_sigma = new_sigma_b
        else:
            feature_a.value_mu = new_mu_a
            feature_a.value_sigma = new_sigma_a
            feature_b.value_mu = new_mu_b
            feature_b.value_sigma = new_sigma_b

        db.add(feature_a)
        db.add(feature_b)

    # Update project average variance
    if features:
        if dimension == "complexity":
            avg_variance = sum(f.complexity_sigma for f in features) / len(features)
            project.complexity_avg_variance = avg_variance
        else:
            avg_variance = sum(f.value_sigma for f in features) / len(features)
            project.value_avg_variance = avg_variance
        db.add(project)


@router.get("/{project_id}/comparisons", response_model=None)
def read_comparisons(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    dimension: Optional[str] = None,
    ids: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve comparisons for a project.

    Args:
        dimension: Filter by dimension ("complexity" or "value")
        ids: Comma-separated list of comparison UUIDs to fetch (batch fetch).
             **UI Efficiency**: Fetch multiple specific comparisons in one request.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Batch fetch by IDs if provided
    if ids:
        id_list = [id.strip() for id in ids.split(",") if id.strip()]
        comparisons = []
        for comp_id in id_list:
            comp = crud.comparison.get(db=db, id=comp_id)
            if comp and str(comp.project_id) == project_id:
                comparisons.append(comp)
        return comparisons

    comparisons = crud.comparison.get_multi_by_project(
        db=db, project_id=project_id, skip=skip, limit=limit
    )

    if dimension:
        comparisons = [c for c in comparisons if c.dimension == dimension]

    return comparisons


@router.get("/{project_id}/comparisons/next", response_model=None)
def get_next_comparison_pair(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: str,
    target_certainty: float = 1.0,
    include_progress: bool = False,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get the next pair of features to compare (highest information gain).

    Args:
        dimension: "complexity" or "value"
        target_certainty: Target confidence level (0.0-1.0). Returns 204 when reached.
                         Default 1.0 means continue until all orderings are known.
        include_progress: If True, includes progress metrics in the response.
                         **UI Efficiency**: Eliminates separate /progress call during comparison workflow.

    Returns:
        - 200 with ComparisonPair if there are useful comparisons to make
        - 204 No Content if target certainty is reached or ordering is fully determined
        - 200 with resolution pair if cycles exist that need resolution

    The endpoint uses active learning with transitive inference to select
    the pair that will provide the most information gain:
    1. Pairs whose ordering is unknown (not determinable by transitivity)
    2. Among unknown pairs, those that would transitively determine the most other pairs

    Key insight: We don't need to compare all N*(N-1)/2 pairs. With transitivity,
    ~N*log(N) comparisons suffice. If A>B and B>C, we know A>C without asking.
    """
    from fastapi import Response

    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    if dimension not in ["complexity", "value"]:
        raise HTTPException(status_code=400, detail="Invalid dimension")

    # Get all features for the project
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)

    if len(features) < 2:
        raise HTTPException(
            status_code=400, detail="Not enough features for comparison"
        )

    feature_ids = [str(f.id) for f in features]
    features_by_id = {str(f.id): f for f in features}

    # Get existing comparisons for this dimension
    all_comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    dimension_comparisons = [c for c in all_comparisons if c.dimension == dimension]
    total_comparisons_done = len(dimension_comparisons)

    # Check if we have inconsistencies (cycles)
    inconsistency_stats = _calculate_inconsistency_stats(db, project_id, dimension)
    has_cycles = inconsistency_stats["cycle_count"] > 0

    # Compute transitive knowledge - what pairs do we already know the ordering for?
    direct_pairs, known_pairs, uncertain_count = _compute_transitive_knowledge(
        dimension_comparisons, feature_ids
    )

    n = len(features)
    total_possible_pairs = n * (n - 1) // 2

    # Calculate transitive coverage (same as in /progress endpoint)
    if total_possible_pairs > 0:
        transitive_known_pairs = total_possible_pairs - uncertain_count
        transitive_coverage = transitive_known_pairs / total_possible_pairs
    else:
        transitive_coverage = 1.0

    # Calculate effective confidence (same formula as /progress endpoint)
    # Get Bayesian confidence from project variance
    current_variance = (
        project.complexity_avg_variance
        if dimension == "complexity"
        else project.value_avg_variance
    )
    bayesian_confidence = max(0.0, min(1.0, 1.0 - current_variance))

    # Consistency score
    if len(dimension_comparisons) > 0:
        consistency_score = max(
            0.5, 1.0 - (inconsistency_stats["cycle_count"] / len(dimension_comparisons))
        )
    else:
        consistency_score = 1.0

    # Effective confidence formula (must match /progress endpoint)
    if transitive_coverage >= 1.0 and consistency_score >= 1.0:
        effective_confidence = 1.0
    elif transitive_coverage >= 1.0:
        effective_confidence = min(0.95, consistency_score)
    else:
        bayesian_boost = 0.05 * bayesian_confidence
        effective_confidence = (
            min(1.0, transitive_coverage + bayesian_boost) * consistency_score
        )

    # Check if we've reached the target certainty - return 204 if so
    # Only check if target_certainty > 0 (explicitly requested)
    if target_certainty > 0:
        if transitive_coverage >= target_certainty and not has_cycles:
            return Response(status_code=204)

    # If all orderings are known (via transitivity) and no cycles, we're done!
    if uncertain_count == 0 and not has_cycles:
        return Response(status_code=204)

    # If cycles exist and we've directly compared enough pairs, offer resolution
    if has_cycles:
        resolution_result = _get_resolution_pair_internal(
            db, project_id, dimension, features
        )
        if resolution_result:
            return resolution_result

    # Find the best pair to compare using transitive-aware selection
    best_result = _get_optimal_next_pair_transitive(
        feature_ids, features_by_id, dimension_comparisons, dimension
    )

    if best_result is None:
        # All orderings known but might have cycles - try resolution
        if has_cycles:
            resolution_result = _get_resolution_pair_internal(
                db, project_id, dimension, features
            )
            if resolution_result:
                return resolution_result
        # Truly complete
        return Response(status_code=204)

    feature_a, feature_b, selection_score = best_result

    result = {
        "comparison_id": None,  # Generated on submission
        "feature_a": feature_a,
        "feature_b": feature_b,
        "dimension": dimension,
    }

    # Include progress metrics if requested (UI efficiency optimization)
    if include_progress:
        comparisons_remaining = max(
            0, int(0.77 * n * math.log2(max(n, 2))) - total_comparisons_done
        )
        result["progress"] = {
            "progress_percent": (
                round(effective_confidence * 100 / target_certainty, 1)
                if target_certainty > 0
                else round(transitive_coverage * 100, 1)
            ),
            "comparisons_done": total_comparisons_done,
            "comparisons_remaining": comparisons_remaining,
            "transitive_coverage": round(transitive_coverage, 4),
            "effective_confidence": round(effective_confidence, 4),
        }

    return result


def _get_resolution_pair_internal(
    db: Session, project_id: str, dimension: str, features: list
) -> Optional[dict]:
    """
    Internal helper to find the weakest link in detected cycles.

    Returns a comparison pair dict or None if no suitable pair found.
    """
    comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    comparisons = [c for c in comparisons if c.dimension == dimension]

    # Build graph
    graph = {}
    comparison_map = {}  # Map (winner, loser) -> comparison object

    for comp in comparisons:
        if comp.choice == "tie":
            continue

        winner_id = str(
            comp.feature_a_id if comp.choice == "feature_a" else comp.feature_b_id
        )
        loser_id = str(
            comp.feature_b_id if comp.choice == "feature_a" else comp.feature_a_id
        )

        if winner_id not in graph:
            graph[winner_id] = set()
        if loser_id not in graph:
            graph[loser_id] = set()

        graph[winner_id].add(loser_id)
        comparison_map[(winner_id, loser_id)] = comp

    # Find cycles
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in all_cycles:
                    all_cycles.append(normalized)

        path.pop()
        rec_stack.remove(node)

    cycles_found = []
    visited_global = set()

    for node in graph:
        if node not in visited_global:
            find_cycles_dfs(node, [], visited_global, set(), cycles_found)

    if not cycles_found:
        return None

    # Find the "weakest link" - the pair with highest uncertainty
    weakest_pair = None
    max_uncertainty = -1.0

    # Create feature lookup
    feature_map = {str(f.id): f for f in features}

    for cycle in cycles_found:
        for i in range(len(cycle)):
            winner = cycle[i]
            loser = cycle[(i + 1) % len(cycle)]

            feature_winner = feature_map.get(winner)
            feature_loser = feature_map.get(loser)

            if not feature_winner or not feature_loser:
                continue

            if dimension == "complexity":
                uncertainty = (
                    feature_winner.complexity_sigma + feature_loser.complexity_sigma
                )
            else:
                uncertainty = feature_winner.value_sigma + feature_loser.value_sigma

            if uncertainty > max_uncertainty:
                max_uncertainty = uncertainty
                weakest_pair = (feature_winner, feature_loser)

    if not weakest_pair:
        return None

    feature_a, feature_b = weakest_pair

    return {
        "comparison_id": None,
        "feature_a": feature_a,
        "feature_b": feature_b,
        "dimension": dimension,
        "reason": "This pair is involved in a logical cycle. Re-comparing may help resolve the inconsistency.",
    }


@router.post(
    "/{project_id}/comparisons",
    response_model=schemas.ComparisonWithStats,
    status_code=201,
)
def create_comparison(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    comparison_in: schemas.ComparisonCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Submit the result of a pairwise comparison.

    Returns the created comparison along with updated inconsistency statistics
    for immediate UI feedback.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Validate features exist
    feature_a = crud.feature.get(db=db, id=str(comparison_in.feature_a_id))
    feature_b = crud.feature.get(db=db, id=str(comparison_in.feature_b_id))
    if not feature_a or not feature_b:
        raise HTTPException(status_code=404, detail="One or both features not found")

    # Validate not comparing same feature
    if str(comparison_in.feature_a_id) == str(comparison_in.feature_b_id):
        raise HTTPException(
            status_code=400, detail="Cannot compare a feature with itself"
        )

    # Store the comparison
    comparison = crud.comparison.create_with_project(
        db=db, obj_in=comparison_in, project_id=project_id, user_id=str(current_user.id)  # type: ignore
    )

    # Increment project comparison counter
    project.total_comparisons += 1
    db.add(project)

    # Bayesian Bradley-Terry update
    # Update the mu and sigma values for both features based on the comparison outcome

    # Tuning parameters
    LAMBDA = math.pi / 8  # ≈ 0.39 - standard for logistic model
    KAPPA = 0.01  # Minimum variance to prevent overconfidence

    # Get current scores for the relevant dimension
    if comparison_in.dimension == "complexity":
        mu_a = feature_a.complexity_mu
        sigma_a = feature_a.complexity_sigma
        mu_b = feature_b.complexity_mu
        sigma_b = feature_b.complexity_sigma
    else:  # value
        mu_a = feature_a.value_mu
        sigma_a = feature_a.value_sigma
        mu_b = feature_b.value_mu
        sigma_b = feature_b.value_sigma

    # Determine outcome: y=1 if feature_a wins, y=0 if feature_b wins, y=0.5 for tie
    if comparison_in.choice == "feature_a":
        y = 1.0
    elif comparison_in.choice == "feature_b":
        y = 0.0
    else:  # tie
        y = 0.5

    # Step 1: Compute expected outcome probability
    # p_hat = P(feature_a > feature_b) = 1 / (1 + exp(-(mu_a - mu_b)))
    try:
        p_hat = 1.0 / (1.0 + math.exp(-(mu_a - mu_b)))
    except OverflowError:
        # Handle extreme values
        p_hat = 1.0 if mu_a > mu_b else 0.0

    # Step 2: Calculate prediction error
    delta = y - p_hat

    # Step 3: Calculate variance of outcome
    variance_term = p_hat * (1.0 - p_hat)

    # Avoid division by zero
    if variance_term < 1e-10:
        variance_term = 1e-10

    # Step 4: Update means
    # mu_i += sigma_i^2 * delta / sqrt(1 + lambda * p_hat * (1-p_hat))
    denominator = math.sqrt(1.0 + LAMBDA * variance_term)

    sigma_a_squared = sigma_a**2
    sigma_b_squared = sigma_b**2

    new_mu_a = mu_a + (sigma_a_squared * delta) / denominator
    new_mu_b = mu_b - (sigma_b_squared * delta) / denominator

    # Step 5: Update variances (reduce uncertainty)
    # sigma_i^2 *= max(1 - sigma_i^2 * p_hat*(1-p_hat) / (1 + lambda*p_hat*(1-p_hat)), kappa)
    variance_reduction_a = 1.0 - (sigma_a_squared * variance_term) / (
        1.0 + LAMBDA * variance_term
    )
    variance_reduction_b = 1.0 - (sigma_b_squared * variance_term) / (
        1.0 + LAMBDA * variance_term
    )

    new_sigma_a_squared = max(sigma_a_squared * variance_reduction_a, KAPPA)
    new_sigma_b_squared = max(sigma_b_squared * variance_reduction_b, KAPPA)

    new_sigma_a = math.sqrt(new_sigma_a_squared)
    new_sigma_b = math.sqrt(new_sigma_b_squared)

    # Step 6: Apply updates to features
    if comparison_in.dimension == "complexity":
        feature_a.complexity_mu = new_mu_a
        feature_a.complexity_sigma = new_sigma_a
        feature_b.complexity_mu = new_mu_b
        feature_b.complexity_sigma = new_sigma_b
    else:  # value
        feature_a.value_mu = new_mu_a
        feature_a.value_sigma = new_sigma_a
        feature_b.value_mu = new_mu_b
        feature_b.value_sigma = new_sigma_b

    # Commit the updates
    db.add(feature_a)
    db.add(feature_b)

    # Update project average variance for this dimension
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    if features:
        if comparison_in.dimension == "complexity":
            avg_variance = sum(f.complexity_sigma for f in features) / len(features)
            project.complexity_avg_variance = avg_variance
        else:  # value
            avg_variance = sum(f.value_sigma for f in features) / len(features)
            project.value_avg_variance = avg_variance

    db.commit()
    db.refresh(comparison)

    # Calculate inconsistency stats for immediate UI feedback
    inconsistency_stats = _calculate_inconsistency_stats(
        db=db, project_id=project_id, dimension=comparison_in.dimension
    )

    # Construct response with stats
    comparison_dict = {
        "id": comparison.id,
        "project_id": comparison.project_id,
        "feature_a": comparison.feature_a,
        "feature_b": comparison.feature_b,
        "choice": comparison.choice,
        "dimension": comparison.dimension,
        "created_at": comparison.created_at,
        "inconsistency_stats": inconsistency_stats,
    }

    return comparison_dict


def _apply_bayesian_update(
    feature_a: models.Feature,
    feature_b: models.Feature,
    dimension: str,
    y: float,  # 1.0=A wins, 0.0=B wins, 0.5=tie
    strength_multiplier: float = 1.0,  # For graded: see settings.GRADED_MUCH_BETTER_MULTIPLIER
) -> None:
    """
    Apply Bayesian Bradley-Terry update to feature scores.

    Args:
        feature_a: First feature in comparison
        feature_b: Second feature in comparison
        dimension: "complexity" or "value"
        y: Outcome (1.0=A wins, 0.0=B wins, 0.5=tie)
        strength_multiplier: Multiplier for graded comparisons (default 1.0)
            - 1.0 for binary comparisons or "a_better"/"b_better" graded
            - settings.GRADED_MUCH_BETTER_MULTIPLIER for "a_much_better"/"b_much_better"
    """
    # Tuning parameters
    LAMBDA = math.pi / 8  # ≈ 0.39 - standard for logistic model
    KAPPA = 0.01  # Minimum variance to prevent overconfidence

    # Get current scores for the relevant dimension
    if dimension == "complexity":
        mu_a = feature_a.complexity_mu
        sigma_a = feature_a.complexity_sigma
        mu_b = feature_b.complexity_mu
        sigma_b = feature_b.complexity_sigma
    else:  # value
        mu_a = feature_a.value_mu
        sigma_a = feature_a.value_sigma
        mu_b = feature_b.value_mu
        sigma_b = feature_b.value_sigma

    # Step 1: Compute expected outcome probability
    try:
        p_hat = 1.0 / (1.0 + math.exp(-(mu_a - mu_b)))
    except OverflowError:
        p_hat = 1.0 if mu_a > mu_b else 0.0

    # Step 2: Calculate prediction error with strength multiplier
    delta = (y - p_hat) * strength_multiplier

    # Step 3: Calculate variance of outcome
    variance_term = p_hat * (1.0 - p_hat)
    if variance_term < 1e-10:
        variance_term = 1e-10

    # Step 4: Update means
    denominator = math.sqrt(1.0 + LAMBDA * variance_term)
    sigma_a_squared = sigma_a**2
    sigma_b_squared = sigma_b**2

    new_mu_a = mu_a + (sigma_a_squared * delta) / denominator
    new_mu_b = mu_b - (sigma_b_squared * delta) / denominator

    # Step 5: Update variances (reduce uncertainty)
    # Apply strength multiplier to variance reduction for stronger convergence
    variance_reduction_a = 1.0 - (
        sigma_a_squared * variance_term * strength_multiplier
    ) / (1.0 + LAMBDA * variance_term)
    variance_reduction_b = 1.0 - (
        sigma_b_squared * variance_term * strength_multiplier
    ) / (1.0 + LAMBDA * variance_term)

    new_sigma_a_squared = max(sigma_a_squared * variance_reduction_a, KAPPA)
    new_sigma_b_squared = max(sigma_b_squared * variance_reduction_b, KAPPA)

    new_sigma_a = math.sqrt(new_sigma_a_squared)
    new_sigma_b = math.sqrt(new_sigma_b_squared)

    # Step 6: Apply updates to features
    if dimension == "complexity":
        feature_a.complexity_mu = new_mu_a
        feature_a.complexity_sigma = new_sigma_a
        feature_b.complexity_mu = new_mu_b
        feature_b.complexity_sigma = new_sigma_b
    else:  # value
        feature_a.value_mu = new_mu_a
        feature_a.value_sigma = new_sigma_a
        feature_b.value_mu = new_mu_b
        feature_b.value_sigma = new_sigma_b


@router.post(
    "/{project_id}/comparisons/binary",
    response_model=schemas.ComparisonWithStats,
    status_code=201,
)
def create_binary_comparison(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    comparison_in: schemas.BinaryComparisonCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Submit a binary comparison (A beats B, B beats A, or tie).

    This endpoint is for projects in binary comparison mode.
    For graded comparisons, use POST /{project_id}/comparisons/graded.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and project.owner_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Validate project is in binary mode
    if project.comparison_mode != "binary":
        raise HTTPException(
            status_code=400,
            detail=f"Project is in '{project.comparison_mode}' mode. Use the graded comparison endpoint.",
        )

    # Validate features exist
    feature_a = crud.feature.get(db=db, id=str(comparison_in.feature_a_id))
    feature_b = crud.feature.get(db=db, id=str(comparison_in.feature_b_id))
    if not feature_a or not feature_b:
        raise HTTPException(status_code=404, detail="One or both features not found")

    if str(comparison_in.feature_a_id) == str(comparison_in.feature_b_id):
        raise HTTPException(
            status_code=400, detail="Cannot compare a feature with itself"
        )

    # Create comparison record (convert to ComparisonCreate for CRUD)
    comparison_data = schemas.ComparisonCreate(
        feature_a_id=comparison_in.feature_a_id,
        feature_b_id=comparison_in.feature_b_id,
        choice=comparison_in.choice,
        dimension=comparison_in.dimension,
        strength=None,
    )
    comparison = crud.comparison.create_with_project(
        db=db, obj_in=comparison_data, project_id=project_id, user_id=str(current_user.id)  # type: ignore
    )

    # Increment project comparison counter
    project.total_comparisons += 1
    db.add(project)

    # Determine outcome for Bayesian update
    if comparison_in.choice == schemas.ComparisonChoice.feature_a:
        y = 1.0
    elif comparison_in.choice == schemas.ComparisonChoice.feature_b:
        y = 0.0
    else:  # tie
        y = 0.5

    # Apply Bayesian update
    _apply_bayesian_update(feature_a, feature_b, comparison_in.dimension.value, y)
    db.add(feature_a)
    db.add(feature_b)

    # Update project average variance
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    if features:
        if comparison_in.dimension.value == "complexity":
            avg_variance = sum(f.complexity_sigma for f in features) / len(features)
            project.complexity_avg_variance = avg_variance
        else:
            avg_variance = sum(f.value_sigma for f in features) / len(features)
            project.value_avg_variance = avg_variance

    db.commit()
    db.refresh(comparison)

    # Calculate inconsistency stats
    inconsistency_stats = _calculate_inconsistency_stats(
        db=db, project_id=project_id, dimension=comparison_in.dimension.value
    )

    return {
        "id": comparison.id,
        "project_id": comparison.project_id,
        "feature_a": comparison.feature_a,
        "feature_b": comparison.feature_b,
        "choice": comparison.choice,
        "dimension": comparison.dimension,
        "created_at": comparison.created_at,
        "inconsistency_stats": inconsistency_stats,
    }


@router.post(
    "/{project_id}/comparisons/graded",
    response_model=schemas.GradedComparisonWithStats,
    status_code=201,
)
def create_graded_comparison(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    comparison_in: schemas.GradedComparisonCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Submit a graded comparison using a 5-point scale.

    Strength options:
    - a_much_better: Feature A is much better than B
    - a_better: Feature A is better than B
    - equal: Features are roughly equal
    - b_better: Feature B is better than A
    - b_much_better: Feature B is much better than A

    Graded comparisons provide more information per comparison, allowing
    faster convergence with 30-40% fewer total comparisons needed.

    This endpoint is for projects in graded comparison mode.
    For binary comparisons, use POST /{project_id}/comparisons/binary.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and project.owner_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Validate project is in graded mode
    if project.comparison_mode != "graded":
        raise HTTPException(
            status_code=400,
            detail=f"Project is in '{project.comparison_mode}' mode. Use the binary comparison endpoint.",
        )

    # Validate features exist
    feature_a = crud.feature.get(db=db, id=str(comparison_in.feature_a_id))
    feature_b = crud.feature.get(db=db, id=str(comparison_in.feature_b_id))
    if not feature_a or not feature_b:
        raise HTTPException(status_code=404, detail="One or both features not found")

    if str(comparison_in.feature_a_id) == str(comparison_in.feature_b_id):
        raise HTTPException(
            status_code=400, detail="Cannot compare a feature with itself"
        )

    # Map strength to choice and multiplier
    # Multipliers are configured in settings: GRADED_MUCH_BETTER_MULTIPLIER, GRADED_EQUAL_MULTIPLIER
    strength = comparison_in.strength
    if strength == schemas.ComparisonStrength.a_much_better:
        choice = schemas.ComparisonChoice.feature_a
        y = 1.0
        strength_multiplier = settings.GRADED_MUCH_BETTER_MULTIPLIER
    elif strength == schemas.ComparisonStrength.a_better:
        choice = schemas.ComparisonChoice.feature_a
        y = 1.0
        strength_multiplier = 1.0
    elif strength == schemas.ComparisonStrength.equal:
        choice = schemas.ComparisonChoice.tie
        y = 0.5
        strength_multiplier = settings.GRADED_EQUAL_MULTIPLIER
    elif strength == schemas.ComparisonStrength.b_better:
        choice = schemas.ComparisonChoice.feature_b
        y = 0.0
        strength_multiplier = 1.0
    else:  # b_much_better
        choice = schemas.ComparisonChoice.feature_b
        y = 0.0
        strength_multiplier = settings.GRADED_MUCH_BETTER_MULTIPLIER

    # Create comparison record
    comparison_data = schemas.ComparisonCreate(
        feature_a_id=comparison_in.feature_a_id,
        feature_b_id=comparison_in.feature_b_id,
        choice=choice,
        dimension=comparison_in.dimension,
        strength=strength,
    )
    comparison = crud.comparison.create_with_project(
        db=db, obj_in=comparison_data, project_id=project_id, user_id=str(current_user.id)  # type: ignore
    )

    # Increment project comparison counter
    project.total_comparisons += 1
    db.add(project)

    # Apply strength-weighted Bayesian update
    _apply_bayesian_update(
        feature_a, feature_b, comparison_in.dimension.value, y, strength_multiplier
    )
    db.add(feature_a)
    db.add(feature_b)

    # Update project average variance
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    if features:
        if comparison_in.dimension.value == "complexity":
            avg_variance = sum(f.complexity_sigma for f in features) / len(features)
            project.complexity_avg_variance = avg_variance
        else:
            avg_variance = sum(f.value_sigma for f in features) / len(features)
            project.value_avg_variance = avg_variance

    db.commit()
    db.refresh(comparison)

    # Calculate inconsistency stats
    inconsistency_stats = _calculate_inconsistency_stats(
        db=db, project_id=project_id, dimension=comparison_in.dimension.value
    )

    return {
        "id": comparison.id,
        "project_id": comparison.project_id,
        "feature_a": comparison.feature_a,
        "feature_b": comparison.feature_b,
        "dimension": comparison.dimension,
        "strength": comparison.strength,
        "choice": comparison.choice,
        "created_at": comparison.created_at,
        "inconsistency_stats": inconsistency_stats,
    }


@router.get("/{project_id}/comparisons/estimates")
def get_comparison_estimates(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get estimated number of comparisons needed to reach certainty thresholds.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Validate dimension
    if dimension not in ["complexity", "value"]:
        raise HTTPException(status_code=400, detail="Invalid dimension")

    # Placeholder estimates (production would use Bayesian model)
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    n = len(features)

    return {
        "dimension": dimension,
        "estimates": {
            "70%": max(0, n * (n - 1) // 4),
            "80%": max(0, n * (n - 1) // 3),
            "90%": max(0, n * (n - 1) // 2),
            "95%": max(0, n * (n - 1) * 3 // 4),
        },
    }


@router.get("/{project_id}/comparisons/inconsistency-stats")
def get_inconsistency_stats(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get inconsistency statistics without full cycle details.

    Useful for:
    - Dashboard widgets showing inconsistency count
    - Polling for updates without creating comparisons
    - Quick health checks of comparison quality

    Returns summary statistics including cycle count and percentage.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    stats = _calculate_inconsistency_stats(
        db=db, project_id=project_id, dimension=dimension
    )

    return stats


@router.get(
    "/{project_id}/comparisons/inconsistencies",
    response_model=schemas.InconsistencyResponse,
)
def get_inconsistencies(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get graph cycles representing logical inconsistencies.

    Detects cycles in the comparison graph where A>B, B>C, C>A.
    These represent logical inconsistencies in user choices.

    Note: The Bayesian model handles probabilistic inconsistencies naturally,
    but detecting hard cycles is useful for identifying pairs that need re-evaluation.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get all active comparisons for the project
    comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)

    # Filter by dimension if specified
    if dimension:
        comparisons = [c for c in comparisons if c.dimension == dimension]

    # Build directed graph: winner -> loser edges
    # Key: feature_id, Value: set of feature_ids that this feature beats
    graph = {}
    feature_names = {}  # Cache feature names for response

    for comp in comparisons:
        # Skip ties - they don't create directed edges
        if comp.choice == "tie":
            continue

        winner_id = str(
            comp.feature_a_id if comp.choice == "feature_a" else comp.feature_b_id
        )
        loser_id = str(
            comp.feature_b_id if comp.choice == "feature_a" else comp.feature_a_id
        )

        # Initialize graph nodes
        if winner_id not in graph:
            graph[winner_id] = set()
        if loser_id not in graph:
            graph[loser_id] = set()

        # Add directed edge: winner -> loser
        graph[winner_id].add(loser_id)

        # Cache feature names
        if winner_id not in feature_names:
            feature_names[winner_id] = (
                comp.feature_a.name
                if comp.choice == "feature_a"
                else comp.feature_b.name
            )
        if loser_id not in feature_names:
            feature_names[loser_id] = (
                comp.feature_b.name
                if comp.choice == "feature_a"
                else comp.feature_a.name
            )

    # Detect cycles using DFS with cycle tracking
    #
    # DFS CYCLE DETECTION PRINCIPLES:
    # ================================
    # This algorithm detects cycles in a directed graph using Depth-First Search
    # with a "recursion stack" (rec_stack) to track the current DFS path.
    #
    # KEY INSIGHT: A cycle exists if and only if we encounter a node that is
    # already in our current recursion path (not just visited before).
    #
    # Why two sets (visited vs rec_stack)?
    # ------------------------------------
    # - `visited`: All nodes we've ever seen (prevents re-exploring finished subtrees)
    # - `rec_stack`: Nodes in the CURRENT path from root to current node
    #
    # Consider this graph:  A → B → C
    #                       ↓
    #                       D → C
    #
    # When exploring A→B→C, we mark B,C as visited. Later exploring A→D→C,
    # C is visited but NOT in rec_stack (we backtracked from C already).
    # This is NOT a cycle - C is just reachable via two paths.
    #
    # But in:  A → B → C → A  (cycle!)
    #
    # When we reach C and see edge C→A, A IS in rec_stack (we're still in the
    # path A→B→C), so this IS a cycle.
    #
    # Algorithm steps:
    # 1. Add current node to both visited and rec_stack
    # 2. For each neighbor:
    #    - If unvisited: recurse
    #    - If in rec_stack: CYCLE FOUND! Extract cycle from path
    #    - If visited but not in rec_stack: skip (already explored, no cycle)
    # 3. Backtrack: remove from rec_stack (but keep in visited)
    #
    # Time complexity: O(V + E) where V=vertices, E=edges
    # Space complexity: O(V) for the recursion stack and tracking sets
    #
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        """
        DFS-based cycle detection.

        Args:
            node: Current node being explored
            path: Current path from start to current node
            visited: Set of all visited nodes (global)
            rec_stack: Set of nodes in current recursion stack
            all_cycles: List to accumulate found cycles
        """
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        # Explore all neighbors
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                # Recursively explore unvisited neighbor
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                # Found a cycle! Extract the cycle from path
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:] + [neighbor]

                # Normalize cycle to start with lexicographically smallest node
                # This prevents duplicates like [A,B,C] and [B,C,A]
                min_idx = cycle.index(min(cycle[:-1]))  # Exclude last (duplicate) node
                normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]

                # Add if not already found
                if normalized not in all_cycles:
                    all_cycles.append(normalized)

        # Backtrack
        path.pop()
        rec_stack.remove(node)

    # Find all cycles
    cycles_found = []
    visited_global = set()

    for node in graph:
        if node not in visited_global:
            find_cycles_dfs(node, [], visited_global, set(), cycles_found)

    # Format cycles for response with feature names and dimension
    formatted_cycles = []
    for cycle in cycles_found:
        formatted_cycles.append(
            {
                "feature_ids": cycle,
                "feature_names": [feature_names.get(fid, "Unknown") for fid in cycle],
                "length": len(cycle)
                - 1,  # Subtract 1 because last node is duplicate of first
                "dimension": dimension if dimension else "mixed",
            }
        )

    return {
        "cycles": formatted_cycles,
        "count": len(formatted_cycles),
        "message": (
            f"Found {len(formatted_cycles)} logical inconsistencies"
            if formatted_cycles
            else "No inconsistencies detected"
        ),
    }


@router.get("/{project_id}/comparisons/resolve-inconsistency")
def get_resolution_pair(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get a specific pair of features to compare to resolve a detected inconsistency.

    Strategy: Find the "weakest link" in detected cycles - the pair where
    the Bayesian model is most uncertain about the current comparison result.
    Re-comparing this pair can help break the cycle.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Reuse cycle detection logic from get_inconsistencies
    comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    comparisons = [c for c in comparisons if c.dimension == dimension]

    # Build graph
    graph = {}
    comparison_map = {}  # Map (winner, loser) -> comparison object

    for comp in comparisons:
        if comp.choice == "tie":
            continue

        winner_id = str(
            comp.feature_a_id if comp.choice == "feature_a" else comp.feature_b_id
        )
        loser_id = str(
            comp.feature_b_id if comp.choice == "feature_a" else comp.feature_a_id
        )

        if winner_id not in graph:
            graph[winner_id] = set()
        if loser_id not in graph:
            graph[loser_id] = set()

        graph[winner_id].add(loser_id)
        comparison_map[(winner_id, loser_id)] = comp

    # Find cycles
    def find_cycles_dfs(node, path, visited, rec_stack, all_cycles):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                find_cycles_dfs(neighbor, path, visited, rec_stack, all_cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:]
                min_idx = cycle.index(min(cycle))
                normalized = cycle[min_idx:] + cycle[:min_idx]
                if normalized not in all_cycles:
                    all_cycles.append(normalized)

        path.pop()
        rec_stack.remove(node)

    cycles_found = []
    visited_global = set()

    for node in graph:
        if node not in visited_global:
            find_cycles_dfs(node, [], visited_global, set(), cycles_found)

    # If no cycles, return 204
    if not cycles_found:
        from fastapi import Response

        return Response(status_code=204)

    # Find the "weakest link" in all cycles
    # This is the comparison where the model is least confident (highest combined variance)
    weakest_pair = None
    max_uncertainty = -1.0

    for cycle in cycles_found:
        # Check each edge in the cycle
        for i in range(len(cycle)):
            winner = cycle[i]
            loser = cycle[(i + 1) % len(cycle)]

            comp = comparison_map.get((winner, loser))
            if not comp:
                continue

            # Get features to calculate uncertainty
            feature_winner = crud.feature.get(db=db, id=winner)
            feature_loser = crud.feature.get(db=db, id=loser)

            if not feature_winner or not feature_loser:
                continue

            # Calculate combined uncertainty for this pair
            if dimension == "complexity":
                uncertainty = (
                    feature_winner.complexity_sigma + feature_loser.complexity_sigma
                )
            else:  # value
                uncertainty = feature_winner.value_sigma + feature_loser.value_sigma

            if uncertainty > max_uncertainty:
                max_uncertainty = uncertainty
                weakest_pair = (feature_winner, feature_loser)

    if not weakest_pair:
        from fastapi import Response

        return Response(status_code=204)

    feature_a, feature_b = weakest_pair

    # Build cycle context for UI (helps user understand what they're resolving)
    # Find the cycle containing this pair
    containing_cycle = None
    for cycle in cycles_found:
        for i in range(len(cycle)):
            if (
                cycle[i] == str(feature_a.id)
                and cycle[(i + 1) % len(cycle)] == str(feature_b.id)
            ) or (
                cycle[i] == str(feature_b.id)
                and cycle[(i + 1) % len(cycle)] == str(feature_a.id)
            ):
                containing_cycle = cycle
                break
        if containing_cycle:
            break

    cycle_context = None
    if containing_cycle:
        # Get feature names for the cycle
        cycle_feature_names = []
        for fid in containing_cycle:
            feat = crud.feature.get(db=db, id=fid)
            if feat:
                cycle_feature_names.append(feat.name)
            else:
                cycle_feature_names.append(f"Unknown ({fid[:8]})")

        cycle_context = {
            "cycle_length": len(containing_cycle),
            "features_in_cycle": cycle_feature_names,
            "feature_ids_in_cycle": containing_cycle,
        }

    return {
        "comparison_id": None,
        "feature_a": {
            "id": str(feature_a.id),
            "name": feature_a.name,
            "description": feature_a.description,
        },
        "feature_b": {
            "id": str(feature_b.id),
            "name": feature_b.name,
            "description": feature_b.description,
        },
        "dimension": dimension,
        "reason": "This pair is involved in a logical cycle and has high uncertainty. Re-comparing may help resolve the inconsistency.",
        "combined_uncertainty": max_uncertainty,
        "cycle_context": cycle_context,
    }


@router.get("/{project_id}/comparisons/progress")
def get_comparison_progress(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: str,
    target_certainty: float = 0.90,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current comparison progress using a hybrid confidence model with transitive inference.

    The hybrid model combines:
    1. Transitive Coverage: What fraction of pairs have known ordering (direct OR inferred)
    2. Direct Coverage: What fraction of unique pairs have been directly compared
    3. Bayesian Confidence: How certain the model is about score magnitudes
    4. Consistency Score: Whether comparisons are logically consistent (no cycles)

    Key insight: With transitivity, we don't need to compare ALL n*(n-1)/2 pairs.
    If A>B and B>C, we know A>C without direct comparison.
    For n features, ~n*log(n) comparisons suffice to determine complete ordering.

    Example: For 30 features:
    - O(N²) approach: 435 comparisons
    - O(N log N) with transitivity: ~150 comparisons
    - Theoretical minimum: ~107 comparisons (ceiling of log₂(30!))
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get features and calculate total possible pairs
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    n = len(features)
    total_possible_pairs = n * (n - 1) // 2 if n >= 2 else 0
    feature_ids = [str(f.id) for f in features]

    # Get comparisons for this dimension
    all_comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    dimension_comparisons = [c for c in all_comparisons if c.dimension == dimension]
    total_comparisons_done = len(dimension_comparisons)

    # Count unique pairs directly compared
    compared_pairs = set()
    for comp in dimension_comparisons:
        pair = tuple(sorted([str(comp.feature_a_id), str(comp.feature_b_id)]))
        compared_pairs.add(pair)
    unique_pairs_compared = len(compared_pairs)

    # 1. Direct Coverage: fraction of pairs directly compared
    direct_coverage = (
        unique_pairs_compared / total_possible_pairs
        if total_possible_pairs > 0
        else 0.0
    )

    # 2. Transitive Coverage: fraction of pairs with known ordering (direct OR inferred)
    if total_possible_pairs > 0:
        direct_pairs, known_pairs, uncertain_count = _compute_transitive_knowledge(
            dimension_comparisons, feature_ids
        )
        transitive_known_pairs = total_possible_pairs - uncertain_count
        transitive_coverage = transitive_known_pairs / total_possible_pairs
    else:
        transitive_known_pairs = 0
        transitive_coverage = 0.0
        uncertain_count = 0

    # 3. Bayesian Confidence: based on variance reduction
    current_variance = (
        project.complexity_avg_variance
        if dimension == "complexity"
        else project.value_avg_variance
    )
    bayesian_confidence = max(0.0, min(1.0, 1.0 - current_variance))

    # 4. Consistency Score: penalize for logical cycles
    inconsistency_stats = _calculate_inconsistency_stats(db, project_id, dimension)
    cycle_count = inconsistency_stats["cycle_count"]
    if unique_pairs_compared > 0:
        consistency_score = max(0.5, 1.0 - (cycle_count / unique_pairs_compared))
    else:
        consistency_score = 1.0

    # 5. Calculate Effective Confidence using TRANSITIVE coverage
    # This is the key optimization - we're done when we transitively know all orderings
    #
    # IMPORTANT: The formula must be able to REACH the target confidence!
    # Key insight: transitive_coverage directly measures "what fraction of the ranking do we know"
    #
    # Mapping strategy:
    # - transitive_coverage >= 1.0 → effective = 1.0 (complete)
    # - transitive_coverage ~0.90 → effective should be ~0.90 (close to target)
    # - Apply consistency_score as a multiplier to penalize cycles

    if transitive_coverage >= 1.0 and consistency_score >= 1.0:
        # All orderings known (via transitivity) with no inconsistencies
        effective_confidence = 1.0
    elif transitive_coverage >= 1.0:
        # All orderings known but with inconsistencies - cap at 95%
        effective_confidence = min(0.95, consistency_score)
    else:
        # Use transitive coverage as the primary signal, slightly boosted by Bayesian confidence
        # The boost is small (max 5%) to ensure transitive=90% → effective≈90%
        bayesian_boost = 0.05 * bayesian_confidence  # 0-5% boost
        effective_confidence = (
            min(1.0, transitive_coverage + bayesian_boost) * consistency_score
        )

    # Calculate progress percent and estimate remaining comparisons
    progress_percent = effective_confidence * 100.0

    # Estimate remaining comparisons needed
    # With transitivity, we estimate ~n*log₂(n) comparisons for n features
    if effective_confidence >= target_certainty:
        comparisons_remaining = 0
    else:
        # Estimate based on uncertain pairs - each comparison resolves ~2 pairs on average
        comparisons_remaining = max(0, int(uncertain_count / 2))

    # Calculate theoretical minimum and practical estimate
    if n >= 2:
        import math as math_module

        # Theoretical minimum: log₂(n!) - information theoretic lower bound for complete ordering
        if n <= 20:
            theoretical_minimum = int(
                math_module.ceil(math_module.log2(math_module.factorial(n)))
            )
        else:
            # Stirling's approximation: log₂(n!) ≈ n*log₂(n) - n*log₂(e) + 0.5*log₂(2πn)
            theoretical_minimum = int(
                n * math_module.log2(n)
                - n * 0.4427
                + 0.5 * math_module.log2(2 * 3.14159 * n)
            )

        # Practical estimate for reaching target_certainty coverage
        # Based on observed performance: ~0.7 * n * log₂(n) for 90% coverage
        # Scale by target: lower targets need fewer comparisons
        coverage_factor = (
            0.5 + 0.3 * target_certainty
        )  # 0.77 at 90%, 0.74 at 80%, 0.71 at 70%
        practical_estimate = int(coverage_factor * n * math_module.log2(n))
    else:
        theoretical_minimum = 0
        practical_estimate = 0

    return {
        "dimension": dimension,
        "target_certainty": target_certainty,
        # Transitive confidence metrics (NEW - key for O(N log N) efficiency)
        "transitive_coverage": round(transitive_coverage, 4),
        "transitive_known_pairs": transitive_known_pairs,
        "uncertain_pairs": uncertain_count,
        # Direct comparison metrics
        "direct_coverage": round(direct_coverage, 4),
        "unique_pairs_compared": unique_pairs_compared,
        "total_possible_pairs": total_possible_pairs,
        # Hybrid confidence metrics
        "coverage_confidence": round(
            direct_coverage, 4
        ),  # Legacy: same as direct_coverage
        "bayesian_confidence": round(bayesian_confidence, 4),
        "consistency_score": round(consistency_score, 4),
        "effective_confidence": round(effective_confidence, 4),
        "progress_percent": round(progress_percent, 2),
        # Comparison counts and estimates
        "total_comparisons_done": total_comparisons_done,
        "comparisons_remaining": comparisons_remaining,
        "theoretical_minimum": theoretical_minimum,
        "practical_estimate": practical_estimate,  # NEW: realistic estimate for good results
        # Legacy fields for backward compatibility
        "current_avg_variance": round(current_variance, 4),
        "comparisons_done": total_comparisons_done,
        # Inconsistency info
        "cycle_count": cycle_count,
    }


@router.post("/{project_id}/comparisons/reset")
def reset_comparisons(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Remove all comparisons for a project (or specific dimension).
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    count = 0
    for comp in comparisons:
        if dimension is None or comp.dimension == dimension:
            crud.comparison.remove(db=db, id=comp.id)
            count += 1

    # Decrement project comparison counter
    project.total_comparisons = max(0, project.total_comparisons - count)
    db.add(project)
    db.commit()

    return {
        "message": "Comparisons reset",
        "count": count,
    }


@router.post("/{project_id}/comparisons/undo")
def undo_last_comparison(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Undo the most recent comparison for a dimension.

    This removes the comparison and recalculates all feature scores
    by replaying the remaining comparisons from scratch.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get most recent comparison for dimension
    comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    filtered = [c for c in comparisons if c.dimension == dimension]

    if not filtered:
        raise HTTPException(status_code=404, detail="No comparisons to undo")

    # Sort by created_at descending and get first
    last_comparison = sorted(filtered, key=lambda c: c.created_at, reverse=True)[0]
    undone_id = str(last_comparison.id)

    # Store dimension before soft delete
    dimension_for_recalc = last_comparison.dimension

    # Soft delete the comparison (preserves audit trail)
    crud.comparison.soft_delete(
        db=db, id=last_comparison.id, deleted_by=str(current_user.id)
    )

    # Decrement project comparison counter
    project.total_comparisons = max(0, project.total_comparisons - 1)
    db.add(project)

    # Recalculate all Bayesian scores for this dimension
    _recalculate_bayesian_scores(
        db=db, project_id=project_id, dimension=dimension_for_recalc
    )

    db.commit()

    # Calculate updated progress for UI efficiency
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    n = len(features)
    feature_ids = [str(f.id) for f in features]

    remaining_comparisons = crud.comparison.get_multi_by_project(
        db=db, project_id=project_id
    )
    remaining_filtered = [c for c in remaining_comparisons if c.dimension == dimension]
    comparisons_done = len(remaining_filtered)

    # Calculate transitive coverage
    direct_pairs, known_pairs, uncertain_count = _compute_transitive_knowledge(
        remaining_filtered, feature_ids
    )
    total_possible = n * (n - 1) // 2 if n >= 2 else 0
    transitive_coverage = (
        (total_possible - uncertain_count) / total_possible
        if total_possible > 0
        else 1.0
    )

    # Estimate comparisons remaining
    practical_estimate = int(0.77 * n * math.log2(max(n, 2))) if n >= 2 else 0
    comparisons_remaining = max(0, practical_estimate - comparisons_done)

    return {
        "undone_comparison_id": undone_id,
        "message": "Comparison undone",
        "updated_progress": {
            "comparisons_done": comparisons_done,
            "comparisons_remaining": comparisons_remaining,
            "transitive_coverage": round(transitive_coverage, 4),
            "progress_percent": round(transitive_coverage * 100, 1),
        },
    }


@router.post("/{project_id}/comparisons/skip")
def skip_comparison(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    comparison_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Skip a comparison pair if the user is unsure.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # In a full implementation, would mark comparison as skipped
    return {
        "status": "skipped",
    }


@router.get(
    "/{project_id}/comparisons/{comparison_id}", response_model=schemas.Comparison
)
def read_comparison(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    comparison_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get comparison by ID.
    """
    comparison = crud.comparison.get(db=db, id=comparison_id)
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")

    if comparison.project_id != project_id:
        raise HTTPException(
            status_code=400, detail="Comparison does not belong to this project"
        )

    project = crud.project.get(db=db, id=comparison.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    return comparison


@router.put(
    "/{project_id}/comparisons/{comparison_id}", response_model=schemas.Comparison
)
def update_comparison(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    comparison_id: str,
    comparison_in: schemas.ComparisonUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a comparison.
    """
    comparison = crud.comparison.get(db=db, id=comparison_id)
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")

    if comparison.project_id != project_id:
        raise HTTPException(
            status_code=400, detail="Comparison does not belong to this project"
        )

    project = crud.project.get(db=db, id=comparison.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    comparison = crud.comparison.update(db=db, db_obj=comparison, obj_in=comparison_in)
    return comparison


@router.delete("/{project_id}/comparisons/{comparison_id}", status_code=204)
def delete_comparison(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    comparison_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> None:
    """
    Delete a comparison (soft delete - marks as deleted but preserves for audit trail).

    This also recalculates all feature scores for the affected dimension
    by replaying the remaining comparisons from scratch.
    """
    comparison = crud.comparison.get(db=db, id=comparison_id)
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")

    if comparison.project_id != project_id:
        raise HTTPException(
            status_code=400, detail="Comparison does not belong to this project"
        )

    project = crud.project.get(db=db, id=comparison.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Store dimension before soft delete
    dimension = comparison.dimension

    # Soft delete instead of hard delete
    crud.comparison.soft_delete(db=db, id=comparison_id, deleted_by=str(current_user.id))  # type: ignore

    # Decrement project comparison counter
    project.total_comparisons = max(0, project.total_comparisons - 1)
    db.add(project)

    # Recalculate all Bayesian scores for this dimension
    _recalculate_bayesian_scores(db=db, project_id=project_id, dimension=dimension)

    db.commit()
    return None
