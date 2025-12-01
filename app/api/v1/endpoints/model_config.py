from typing import Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models
from app.api import deps

router = APIRouter()


@router.get("/{project_id}/model-config")
def get_model_config(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve the Bayesian/Thurstone-Mosteller configuration for a project.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Return default configuration (would be stored per-project in production)
    return {
        "dimensions": {
            "complexity": {
                "prior_mean": 0.0,
                "prior_variance": 1.0,
                "logistic_scale": 1.0,
                "tie_tolerance": 0.1,
                "target_variance": 0.01,
            },
            "value": {
                "prior_mean": 0.0,
                "prior_variance": 1.0,
                "logistic_scale": 1.0,
                "tie_tolerance": 0.1,
                "target_variance": 0.01,
            },
        },
        "selection_strategy": "entropy",
        "max_parallel_pairs": 1,
    }


@router.put("/{project_id}/model-config")
def update_model_config(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    config: dict,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update configurable parameters that govern Bayesian updates.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Validate config (basic validation, expand as needed)
    if "selection_strategy" in config:
        if config["selection_strategy"] not in [
            "random",
            "uncertainty_sampling",
            "expected_value_of_information",
            "entropy",
        ]:
            raise HTTPException(status_code=400, detail="Invalid selection strategy")

    if "dimensions" in config:
        for dim_name, dim_config in config["dimensions"].items():
            if dim_name not in ["complexity", "value"]:
                raise HTTPException(
                    status_code=400, detail=f"Invalid dimension: {dim_name}"
                )

            # Validate ranges
            if "prior_variance" in dim_config and dim_config["prior_variance"] <= 0:
                raise HTTPException(
                    status_code=400, detail="prior_variance must be positive"
                )
            if "target_variance" in dim_config and dim_config["target_variance"] <= 0:
                raise HTTPException(
                    status_code=400, detail="target_variance must be positive"
                )

    # In production, store config in database
    return {
        "message": "Model config updated",
        "effective_from": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{project_id}/model-config/preview")
def preview_model_impact(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    config: dict,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Simulate the expected comparison counts/variance using a draft configuration.
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
    n = len(features)

    # Placeholder simulation (requires actual Bayesian model)
    return {
        "complexity": {
            "expected_comparisons": n * (n - 1) // 2,
            "predicted_variance": 0.01,
        },
        "value": {
            "expected_comparisons": n * (n - 1) // 2,
            "predicted_variance": 0.01,
        },
    }


@router.post("/{project_id}/model-config/reset")
def reset_model_config(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Reset the project's model configuration back to system defaults.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    defaults = {
        "dimensions": {
            "complexity": {
                "prior_mean": 0.0,
                "prior_variance": 1.0,
                "logistic_scale": 1.0,
                "tie_tolerance": 0.1,
                "target_variance": 0.01,
            },
            "value": {
                "prior_mean": 0.0,
                "prior_variance": 1.0,
                "logistic_scale": 1.0,
                "tie_tolerance": 0.1,
                "target_variance": 0.01,
            },
        },
        "selection_strategy": "entropy",
        "max_parallel_pairs": 1,
    }

    return {
        "message": "Model config reset",
        "defaults": defaults,
    }
