from typing import Any
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud, models
from app.api import deps

router = APIRouter()


@router.get("/{project_id}/results")
def get_ranked_results(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    sort_by: str = "ratio",
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get the final ranked list of features.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    if sort_by not in ["complexity", "value", "ratio"]:
        raise HTTPException(status_code=400, detail="Invalid sort_by parameter")

    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)

    # Placeholder ranking (requires Bayesian model)
    results = []
    for rank, feature in enumerate(features, start=1):
        results.append(
            {
                "rank": rank,
                "feature": feature,
                "score": 0.0,  # Placeholder
                "variance": 1.0,  # Placeholder
                "confidence_interval": [0.0, 0.0],  # Placeholder
            }
        )

    return results


@router.get("/{project_id}/results/quadrants")
def get_quadrant_analysis(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get features categorized into four quadrants (Quick-Wins, Strategic, Fill-Ins, Avoid).
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get features for the project
    _ = crud.feature.get_multi_by_project(db=db, project_id=project_id)

    # Placeholder quadrant assignment (requires Bayesian scores)
    # Quick Wins: High Value, Low Complexity
    # Strategic: High Value, High Complexity
    # Fill-Ins: Low Value, Low Complexity
    # Avoid: Low Value, High Complexity

    return {
        "quick_wins": [],
        "strategic": [],
        "fill_ins": [],
        "avoid": [],
    }


@router.get("/{project_id}/results/export")
def export_results(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    format: str = "json",
    sort_by: str = "ratio",
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Export ranked results in various formats for reporting.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format")

    if sort_by not in ["complexity", "value", "ratio"]:
        raise HTTPException(status_code=400, detail="Invalid sort_by parameter")

    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)

    if format == "json":
        # Return JSON array
        results = []
        for rank, feature in enumerate(features, start=1):
            results.append(
                {
                    "rank": rank,
                    "id": str(feature.id),
                    "name": feature.name,
                    "description": feature.description,
                    "complexity_score": 0.0,  # Placeholder
                    "value_score": 0.0,  # Placeholder
                }
            )
        return results

    else:  # CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["Rank", "ID", "Name", "Description", "Complexity Score", "Value Score"]
        )

        for rank, feature in enumerate(features, start=1):
            writer.writerow(
                [
                    rank,
                    str(feature.id),
                    feature.name,
                    feature.description or "",
                    0.0,  # Placeholder
                    0.0,  # Placeholder
                ]
            )

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=project_{project_id}_results.csv"
            },
        )
