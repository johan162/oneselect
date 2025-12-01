from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models
from app.api import deps

router = APIRouter()


@router.get("/{project_id}/statistics")
def get_project_statistics(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current state statistics including total comparisons, average variance, etc.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get feature count
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
    total_features = len(features)

    # Get comparison counts by dimension
    comparisons = crud.comparison.get_multi_by_project(db=db, project_id=project_id)
    complexity_count = sum(1 for c in comparisons if c.dimension == "complexity")
    value_count = sum(1 for c in comparisons if c.dimension == "value")

    # Placeholder for variance calculations (requires Bayesian model)

    return {
        "total_features": total_features,
        "comparisons_count": {
            "complexity": complexity_count,
            "value": value_count,
        },
        "average_variance": {
            "complexity": 0.0,  # Placeholder
            "value": 0.0,  # Placeholder
        },
    }


@router.get("/{project_id}/statistics/scores")
def get_feature_scores(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get raw scores and variance for all features.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)

    # Placeholder scores (requires Bayesian model implementation)
    scores = []
    for feature in features:
        scores.append(
            {
                "feature_id": str(feature.id),
                "name": feature.name,
                "complexity": {
                    "mu": 0.0,  # Placeholder
                    "sigma_sq": 1.0,  # Placeholder
                },
                "value": {
                    "mu": 0.0,  # Placeholder
                    "sigma_sq": 1.0,  # Placeholder
                },
            }
        )

    return scores
