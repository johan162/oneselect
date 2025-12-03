from typing import Any, List, Optional
import random
import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


def _calculate_inconsistency_stats(db: Session, project_id: str, dimension: Optional[str] = None) -> dict:
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
    comparison_edges = set()  # Track which comparisons are involved in cycles
    comparison_map = {}  # Map (winner, loser) -> comparison id
    
    for comp in comparisons:
        if comp.choice == "tie":
            continue
        
        winner_id = str(comp.feature_a_id if comp.choice == "feature_a" else comp.feature_b_id)
        loser_id = str(comp.feature_b_id if comp.choice == "feature_a" else comp.feature_a_id)
        
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
    inconsistency_percentage = (len(comparisons_in_cycles) / total_comparisons * 100) if total_comparisons > 0 else 0.0
    
    return {
        "cycle_count": len(cycles_found),
        "total_comparisons": total_comparisons,
        "inconsistency_percentage": round(inconsistency_percentage, 2),
        "dimension": dimension or "all",
    }


@router.get("/{project_id}/comparisons", response_model=List[schemas.Comparison])
def read_comparisons(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    dimension: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve comparisons for a project.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    comparisons = crud.comparison.get_multi_by_project(
        db=db, project_id=project_id, skip=skip, limit=limit
    )

    if dimension:
        comparisons = [c for c in comparisons if c.dimension == dimension]

    return comparisons


@router.get("/{project_id}/comparisons/next", response_model=schemas.ComparisonPair)
def get_next_comparison_pair(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get the next pair of features to compare (highest information gain).
    """
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

    # Get existing comparisons for this dimension
    all_comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    compared_pairs = set()
    for comp in all_comparisons:
        if comp.dimension == dimension:
            pair = tuple(sorted([str(comp.feature_a_id), str(comp.feature_b_id)]))
            compared_pairs.add(pair)

    # Find unpaired combinations and calculate selection scores
    available_pairs = []
    for i, feat_a in enumerate(features):
        for feat_b in features[i + 1 :]:
            pair = tuple(sorted([str(feat_a.id), str(feat_b.id)]))
            if pair not in compared_pairs:
                available_pairs.append((feat_a, feat_b))

    if not available_pairs:
        raise HTTPException(status_code=400, detail="No useful comparisons left")

    # Active Learning: Select pair with maximum expected information gain
    # Based on the formula from theory_background.md:
    # Selection Score = (σ_i + σ_j) * exp(-(μ_i - μ_j)² / (2c²))
    #
    # This combines two factors:
    # 1. Uncertainty (σ_i + σ_j): Prioritize features we're uncertain about
    # 2. Closeness: Prioritize pairs where outcome is uncertain (close scores)
    
    best_score = -1.0
    best_pair = None
    
    # Scaling factor for closeness term (controls how much we favor close pairs)
    c = 2.0
    
    for feat_a, feat_b in available_pairs:
        # Get current mu and sigma for this dimension
        if dimension == "complexity":
            mu_a, sigma_a = feat_a.complexity_mu, feat_a.complexity_sigma
            mu_b, sigma_b = feat_b.complexity_mu, feat_b.complexity_sigma
        else:  # value
            mu_a, sigma_a = feat_a.value_mu, feat_a.value_sigma
            mu_b, sigma_b = feat_b.value_mu, feat_b.value_sigma
        
        # Calculate selection score
        uncertainty = sigma_a + sigma_b
        mu_diff = mu_a - mu_b
        closeness = math.exp(-(mu_diff ** 2) / (2 * c ** 2))
        
        selection_score = uncertainty * closeness
        
        if selection_score > best_score:
            best_score = selection_score
            best_pair = (feat_a, feat_b)
    
    if best_pair is None:
        # Fallback to random if scoring fails
        best_pair = random.choice(available_pairs)
    
    feature_a, feature_b = best_pair

    return {
        "comparison_id": None,  # Generated on submission
        "feature_a": feature_a,
        "feature_b": feature_b,
        "dimension": dimension,
    }


@router.post(
    "/{project_id}/comparisons", response_model=schemas.ComparisonWithStats, status_code=201
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
    if comparison_in.winner == "feature_a":
        y = 1.0
    elif comparison_in.winner == "feature_b":
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
    
    sigma_a_squared = sigma_a ** 2
    sigma_b_squared = sigma_b ** 2
    
    new_mu_a = mu_a + (sigma_a_squared * delta) / denominator
    new_mu_b = mu_b - (sigma_b_squared * delta) / denominator
    
    # Step 5: Update variances (reduce uncertainty)
    # sigma_i^2 *= max(1 - sigma_i^2 * p_hat*(1-p_hat) / (1 + lambda*p_hat*(1-p_hat)), kappa)
    variance_reduction_a = 1.0 - (sigma_a_squared * variance_term) / (1.0 + LAMBDA * variance_term)
    variance_reduction_b = 1.0 - (sigma_b_squared * variance_term) / (1.0 + LAMBDA * variance_term)
    
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
        db=db,
        project_id=project_id,
        dimension=comparison_in.dimension
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
        db=db,
        project_id=project_id,
        dimension=dimension
    )
    
    return stats


@router.get("/{project_id}/comparisons/inconsistencies", response_model=schemas.InconsistencyResponse)
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
        
        winner_id = str(comp.feature_a_id if comp.choice == "feature_a" else comp.feature_b_id)
        loser_id = str(comp.feature_b_id if comp.choice == "feature_a" else comp.feature_a_id)
        
        # Initialize graph nodes
        if winner_id not in graph:
            graph[winner_id] = set()
        if loser_id not in graph:
            graph[loser_id] = set()
        
        # Add directed edge: winner -> loser
        graph[winner_id].add(loser_id)
        
        # Cache feature names
        if winner_id not in feature_names:
            feature_names[winner_id] = comp.feature_a.name if comp.choice == "feature_a" else comp.feature_b.name
        if loser_id not in feature_names:
            feature_names[loser_id] = comp.feature_b.name if comp.choice == "feature_a" else comp.feature_a.name
    
    # Detect cycles using DFS with cycle tracking
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
        formatted_cycles.append({
            "feature_ids": cycle,
            "feature_names": [feature_names.get(fid, "Unknown") for fid in cycle],
            "length": len(cycle) - 1,  # Subtract 1 because last node is duplicate of first
            "dimension": dimension if dimension else "mixed",
        })
    
    return {
        "cycles": formatted_cycles,
        "count": len(formatted_cycles),
        "message": f"Found {len(formatted_cycles)} logical inconsistencies" if formatted_cycles else "No inconsistencies detected",
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
        
        winner_id = str(comp.feature_a_id if comp.choice == "feature_a" else comp.feature_b_id)
        loser_id = str(comp.feature_b_id if comp.choice == "feature_a" else comp.feature_a_id)
        
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
                uncertainty = feature_winner.complexity_sigma + feature_loser.complexity_sigma
            else:  # value
                uncertainty = feature_winner.value_sigma + feature_loser.value_sigma
            
            if uncertainty > max_uncertainty:
                max_uncertainty = uncertainty
                weakest_pair = (feature_winner, feature_loser)
    
    if not weakest_pair:
        from fastapi import Response
        return Response(status_code=204)
    
    feature_a, feature_b = weakest_pair
    
    return {
        "comparison_id": None,
        "feature_a": feature_a,
        "feature_b": feature_b,
        "dimension": dimension,
        "reason": "This pair is involved in a logical cycle and has high uncertainty. Re-comparing may help resolve the inconsistency.",
        "combined_uncertainty": max_uncertainty,
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
    Get current comparison progress as percentage toward target certainty.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get comparisons for dimension
    all_comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    comparisons_done = sum(1 for c in all_comparisons if c.dimension == dimension)

    # Use actual average variance to determine progress
    # Target variance for different certainty levels:
    # 90% certainty ≈ σ < 0.5
    # 95% certainty ≈ σ < 0.3
    # 99% certainty ≈ σ < 0.2
    target_variance_map = {
        0.70: 0.7,
        0.80: 0.6,
        0.90: 0.5,
        0.95: 0.3,
        0.99: 0.2,
    }
    target_variance = target_variance_map.get(target_certainty, 0.5)
    
    # Get current average variance for the dimension
    current_variance = (
        project.complexity_avg_variance if dimension == "complexity" 
        else project.value_avg_variance
    )
    
    # Calculate progress based on variance reduction
    # Starting variance is 1.0, we measure how much we've reduced it
    initial_variance = 1.0
    variance_reduction = (initial_variance - current_variance) / (initial_variance - target_variance)
    progress_percent = min(100.0, max(0.0, variance_reduction * 100))
    current_certainty = min(1.0, max(0.0, variance_reduction))
    
    # Estimate remaining comparisons needed (heuristic: ~2-3 comparisons per feature to converge)
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    n = len(features)
    if current_variance <= target_variance:
        comparisons_remaining = 0
    else:
        # Rough estimate: need more comparisons if variance is still high
        comparisons_remaining = max(0, int(n * (current_variance / target_variance - 1)))

    return {
        "dimension": dimension,
        "target_certainty": target_certainty,
        "current_certainty": current_certainty,
        "progress_percent": progress_percent,
        "comparisons_done": comparisons_done,
        "comparisons_remaining": comparisons_remaining,
        "current_avg_variance": current_variance,
        "target_variance": target_variance,
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

    crud.comparison.remove(db=db, id=last_comparison.id)
    
    # Decrement project comparison counter
    project.total_comparisons = max(0, project.total_comparisons - 1)
    db.add(project)
    db.commit()

    return {
        "undone_comparison_id": str(last_comparison.id),
        "message": "Comparison undone",
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

    # Soft delete instead of hard delete
    crud.comparison.soft_delete(db=db, id=comparison_id, deleted_by=str(current_user.id))  # type: ignore
    return None
