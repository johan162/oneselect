from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=None)
def read_projects(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    include_stats: bool = False,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve projects.

    Args:
        include_stats: If True, includes quick stats for each project (feature count,
                       comparison counts, progress %). Eliminates need to call
                       /summary for each project in dashboard views.
                       **UI Efficiency**: Reduces N+1 API calls for project list dashboards.
    """
    if crud.user.is_superuser(current_user):
        projects = crud.project.get_multi(db, skip=skip, limit=limit)
    else:
        projects = crud.project.get_multi_by_owner(
            db=db, owner_id=str(current_user.id), skip=skip, limit=limit  # type: ignore
        )

    if not include_stats:
        return projects

    # Include quick stats for each project
    result = []
    for project in projects:
        # Get feature count
        features = crud.feature.get_multi_by_project(db=db, project_id=str(project.id))
        feature_count = len(features)

        # Get comparison counts by dimension
        comparisons = crud.comparison.get_multi_by_project(
            db=db, project_id=str(project.id)
        )
        complexity_count = sum(1 for c in comparisons if c.dimension == "complexity")
        value_count = sum(1 for c in comparisons if c.dimension == "value")

        # Calculate simple progress (percentage of possible pairs compared)
        n = feature_count
        total_possible = n * (n - 1) // 2 if n >= 2 else 0
        complexity_progress = (
            round(complexity_count / total_possible * 100, 1)
            if total_possible > 0
            else 0.0
        )
        value_progress = (
            round(value_count / total_possible * 100, 1) if total_possible > 0 else 0.0
        )

        result.append(
            {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "created_at": (
                    project.created_at.isoformat() if project.created_at else None
                ),
                "owner_id": str(project.owner_id),
                "stats": {
                    "feature_count": feature_count,
                    "comparisons": {
                        "complexity": complexity_count,
                        "value": value_count,
                    },
                    "progress": {
                        "complexity": complexity_progress,
                        "value": value_progress,
                    },
                },
            }
        )

    return result


@router.post("/", response_model=schemas.Project, status_code=201)
def create_project(
    *,
    db: Session = Depends(deps.get_db),
    project_in: schemas.ProjectCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new project.
    """
    project = crud.project.create_with_owner(
        db=db, obj_in=project_in, owner_id=str(current_user.id)  # type: ignore
    )
    return project


@router.put("/{id}", response_model=schemas.Project)
def update_project(
    *,
    db: Session = Depends(deps.get_db),
    id: str,
    project_in: schemas.ProjectUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a project.
    """
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    project = crud.project.update(db=db, db_obj=project, obj_in=project_in)
    return project


@router.get("/{id}", response_model=schemas.Project)
def read_project(
    *,
    db: Session = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get project by ID.
    """
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return project


@router.delete("/{id}", response_model=schemas.Project)
def delete_project(
    *,
    db: Session = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a project.
    """
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    project = crud.project.remove(db=db, id=id)
    return project


@router.get("/{id}/summary", response_model=schemas.ProjectSummary)
def get_project_summary(
    *,
    db: Session = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get comprehensive project summary including stats, progress, and alerts.
    """
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get feature count
    features = crud.feature.get_multi_by_project(db=db, project_id=id)
    feature_count = len(features)

    # Get comparison counts by dimension
    comparisons = crud.comparison.get_multi_by_project(db=db, project_id=id)
    complexity_comparisons = sum(1 for c in comparisons if c.dimension == "complexity")
    value_comparisons = sum(1 for c in comparisons if c.dimension == "value")

    # Placeholder for variance and inconsistency calculations
    # These would require actual Bayesian model implementation

    return {
        "project": project,
        "feature_count": feature_count,
        "comparisons": {
            "complexity": {
                "done": complexity_comparisons,
                "remaining_for_95": 0,  # Placeholder
            },
            "value": {
                "done": value_comparisons,
                "remaining_for_95": 0,  # Placeholder
            },
        },
        "average_variance": {
            "complexity": 0.0,  # Placeholder
            "value": 0.0,  # Placeholder
        },
        "inconsistency_count": {
            "complexity": 0,  # Placeholder
            "value": 0,  # Placeholder
        },
    }


@router.get("/{id}/collaborators")
def get_project_collaborators(
    *,
    db: Session = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get all users who have access to a project.
    """
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # For now, return just the owner
    # In a full implementation, would include collaborators table
    owner = crud.user.get(db=db, id=project.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return [
        {
            "user_id": str(owner.id),  # type: ignore
            "username": str(owner.username),  # type: ignore
            "role": "owner",
            "assigned_at": project.created_at,
        }
    ]


@router.get("/{id}/activity")
def get_project_activity(
    *,
    db: Session = Depends(deps.get_db),
    id: str,
    page: int = 1,
    per_page: int = 50,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get paginated activity/audit log for a project.
    """
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Placeholder - would require activity log table
    return {
        "items": [],
        "total": 0,
    }


@router.get("/{id}/last-modified")
def get_project_last_modified(
    *,
    db: Session = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get the last modification timestamp for cache invalidation.
    """
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Use project's updated_at if available, otherwise created_at
    last_modified = getattr(project, "updated_at", project.created_at)

    return {
        "last_modified": last_modified,
        "modified_by": project.owner_id,
    }


@router.get("/{id}/history")
def get_project_history(
    *,
    db: Session = Depends(deps.get_db),
    id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get complete audit trail of all comparisons made in a project.
    PROJ-11: Get Comparison History

    Returns all active comparisons and soft-deleted comparisons with full details.
    """
    project = crud.project.get(db=db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get all comparisons including soft-deleted ones
    all_comparisons = crud.comparison.get_all_by_project_including_deleted(
        db=db, project_id=id
    )

    # Separate active and deleted comparisons
    active_comparisons = []
    deleted_comparisons = []

    for comp in all_comparisons:
        comparison_data = {
            "id": comp.id,
            "feature_a": {
                "id": comp.feature_a.id,
                "name": comp.feature_a.name,
            },
            "feature_b": {
                "id": comp.feature_b.id,
                "name": comp.feature_b.name,
            },
            "choice": comp.choice,
            "dimension": comp.dimension,
            "user": {
                "id": str(comp.user_id) if comp.user_id else str(project.owner_id),
                "username": comp.user.username if comp.user else "unknown",
            },
            "created_at": comp.created_at,
        }

        if comp.deleted_at:
            # This is a deleted comparison
            comparison_data.update(
                {
                    "deleted_at": comp.deleted_at,
                    "deleted_by": {
                        "id": str(comp.deleted_by) if comp.deleted_by else "unknown",
                        "username": (
                            comp.deleter.username if comp.deleter else "unknown"
                        ),
                    },
                }
            )
            deleted_comparisons.append(comparison_data)
        else:
            # This is an active comparison
            active_comparisons.append(comparison_data)

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
        },
        "comparisons": active_comparisons,
        "deleted_comparisons": deleted_comparisons,
    }
