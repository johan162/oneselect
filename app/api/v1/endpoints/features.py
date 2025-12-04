from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/{project_id}/features", response_model=List[schemas.Feature])
def read_features(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve features for a project.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    features = crud.feature.get_multi_by_project(
        db=db, project_id=project_id, skip=skip, limit=limit
    )
    return features


@router.post("/{project_id}/features", response_model=schemas.Feature, status_code=201)
def create_feature(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    feature_in: schemas.FeatureCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new feature.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    feature = crud.feature.create_with_project(
        db=db, obj_in=feature_in, project_id=project_id
    )

    # Update project average variance if comparisons exist
    if project.total_comparisons > 0:
        features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
        if features:
            complexity_avg = sum(f.complexity_sigma for f in features) / len(features)
            value_avg = sum(f.value_sigma for f in features) / len(features)
            project.complexity_avg_variance = complexity_avg
            project.value_avg_variance = value_avg
            db.add(project)
            db.commit()
            db.refresh(feature)

    return feature


@router.post("/{project_id}/features/bulk", status_code=201)
def bulk_create_features(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    features: List[schemas.FeatureCreate],
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Bulk add features.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    created_ids = []
    for feature_in in features:
        feature = crud.feature.create_with_project(
            db=db, obj_in=feature_in, project_id=project_id
        )
        created_ids.append(str(feature.id))

    # Update project average variance if comparisons exist
    if project.total_comparisons > 0:
        all_features = crud.feature.get_multi_by_project(db=db, project_id=project_id)
        if all_features:
            complexity_avg = sum(f.complexity_sigma for f in all_features) / len(
                all_features
            )
            value_avg = sum(f.value_sigma for f in all_features) / len(all_features)
            project.complexity_avg_variance = complexity_avg
            project.value_avg_variance = value_avg
            db.add(project)
            db.commit()

    return {
        "count": len(created_ids),
        "ids": created_ids,
    }


@router.post("/{project_id}/features/bulk-delete")
def bulk_delete_features(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    feature_ids: List[str],
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Bulk delete features.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    deleted_count = 0
    for feature_id in feature_ids:
        feature = crud.feature.get(db=db, id=feature_id)
        if feature and feature.project_id == project_id:
            crud.feature.remove(db=db, id=feature_id)
            deleted_count += 1

    # Update project average variance if comparisons exist
    if deleted_count > 0 and project.total_comparisons > 0:
        remaining_features = crud.feature.get_multi_by_project(
            db=db, project_id=project_id
        )
        if remaining_features:
            complexity_avg = sum(f.complexity_sigma for f in remaining_features) / len(
                remaining_features
            )
            value_avg = sum(f.value_sigma for f in remaining_features) / len(
                remaining_features
            )
            project.complexity_avg_variance = complexity_avg
            project.value_avg_variance = value_avg
        else:
            # No features left, reset to default
            project.complexity_avg_variance = 1.0
            project.value_avg_variance = 1.0
        db.add(project)
        db.commit()

    return {
        "deleted_count": deleted_count,
    }


@router.get("/{project_id}/features/{feature_id}", response_model=schemas.Feature)
def read_feature(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    feature_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get feature by ID.
    """
    feature = crud.feature.get(db=db, id=feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    if feature.project_id != project_id:
        raise HTTPException(
            status_code=400, detail="Feature does not belong to this project"
        )

    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    return feature


@router.put("/{project_id}/features/{feature_id}", response_model=schemas.Feature)
def update_feature(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    feature_id: str,
    feature_in: schemas.FeatureUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a feature.
    """
    feature = crud.feature.get(db=db, id=feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    if feature.project_id != project_id:
        raise HTTPException(
            status_code=400, detail="Feature does not belong to this project"
        )

    project = crud.project.get(db=db, id=feature.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    feature = crud.feature.update(db=db, db_obj=feature, obj_in=feature_in)
    return feature


@router.delete("/{project_id}/features/{feature_id}", status_code=204)
def delete_feature(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    feature_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> None:
    """
    Delete a feature.
    """
    feature = crud.feature.get(db=db, id=feature_id)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    if feature.project_id != project_id:
        raise HTTPException(
            status_code=400, detail="Feature does not belong to this project"
        )

    project = crud.project.get(db=db, id=feature.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    crud.feature.remove(db=db, id=feature_id)

    # Update project average variance if comparisons exist
    if project.total_comparisons > 0:
        remaining_features = crud.feature.get_multi_by_project(
            db=db, project_id=project_id
        )
        if remaining_features:
            complexity_avg = sum(f.complexity_sigma for f in remaining_features) / len(
                remaining_features
            )
            value_avg = sum(f.value_sigma for f in remaining_features) / len(
                remaining_features
            )
            project.complexity_avg_variance = complexity_avg
            project.value_avg_variance = value_avg
        else:
            # No features left, reset to default
            project.complexity_avg_variance = 1.0
            project.value_avg_variance = 1.0
        db.add(project)
        db.commit()

    return None
