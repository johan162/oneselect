from typing import Any, List, Optional
import random
import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


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
    "/{project_id}/comparisons", response_model=schemas.Comparison, status_code=201
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
    db.commit()
    db.refresh(comparison)
    
    return comparison


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


@router.get("/{project_id}/comparisons/inconsistencies")
def get_inconsistencies(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    dimension: Optional[str] = None,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get graph cycles representing logical inconsistencies.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Placeholder - production would implement cycle detection
    return {
        "cycles": [],
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
    COMP-07: Get Resolution Pair
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Placeholder - would use cycle detection to identify pairs that need resolution
    # If no inconsistencies, return 204 No Content
    from fastapi import Response

    return Response(status_code=204)


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

    # Estimate total needed (placeholder)
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    n = len(features)
    estimated_total = int(n * (n - 1) * target_certainty / 2)

    progress_percent = min(100.0, (comparisons_done / max(1, estimated_total)) * 100)

    return {
        "dimension": dimension,
        "target_certainty": target_certainty,
        "current_certainty": progress_percent / 100.0,
        "progress_percent": progress_percent,
        "comparisons_done": comparisons_done,
        "comparisons_remaining": max(0, estimated_total - comparisons_done),
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
