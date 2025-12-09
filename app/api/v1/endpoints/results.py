from typing import Any
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud, models
from app.api import deps
from app.schemas.feature import Feature as FeatureSchema

router = APIRouter()


def _compute_quadrants(features: list[Any]) -> dict[str, list[FeatureSchema]]:
    """
    Compute quadrant categorization for features.

    Returns dict with quick_wins, strategic, fill_ins, avoid lists.
    """
    if not features:
        return {
            "quick_wins": [],
            "strategic": [],
            "fill_ins": [],
            "avoid": [],
        }

    value_scores = [f.value_mu for f in features]
    complexity_scores = [f.complexity_mu for f in features]

    median_value = sorted(value_scores)[len(value_scores) // 2] if value_scores else 0
    median_complexity = (
        sorted(complexity_scores)[len(complexity_scores) // 2]
        if complexity_scores
        else 0
    )

    quick_wins = []
    strategic = []
    fill_ins = []
    avoid = []

    for feature in features:
        high_value = feature.value_mu >= median_value
        high_complexity = feature.complexity_mu >= median_complexity

        feature_schema = FeatureSchema.model_validate(feature)
        if high_value and not high_complexity:
            quick_wins.append(feature_schema)
        elif high_value and high_complexity:
            strategic.append(feature_schema)
        elif not high_value and not high_complexity:
            fill_ins.append(feature_schema)
        else:  # low value, high complexity
            avoid.append(feature_schema)

    return {
        "quick_wins": quick_wins,
        "strategic": strategic,
        "fill_ins": fill_ins,
        "avoid": avoid,
    }


@router.get("/{project_id}/results")
def get_ranked_results(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    sort_by: str = "ratio",
    include_quadrants: bool = False,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get the final ranked list of features.

    Args:
        sort_by: Sort dimension - "complexity", "value", or "ratio" (value/complexity)
        include_quadrants: If True, includes quadrant categorization in response.
                          **UI Efficiency**: Eliminates separate /quadrants call for results view.
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

    # Sort features based on the requested dimension
    if sort_by == "complexity":
        sorted_features = sorted(features, key=lambda f: f.complexity_mu, reverse=True)
    elif sort_by == "value":
        sorted_features = sorted(features, key=lambda f: f.value_mu, reverse=True)
    else:  # ratio
        # Value/Complexity ratio (handle division by zero)
        sorted_features = sorted(
            features, key=lambda f: f.value_mu / max(f.complexity_mu, 0.1), reverse=True
        )

    # Build ranked results with Bayesian scores
    ranked = []
    for rank, feature in enumerate(sorted_features, start=1):
        # Select the appropriate mu and sigma based on sort dimension
        variance: float
        if sort_by == "complexity":
            score = feature.complexity_mu
            variance = float(float(feature.complexity_sigma) ** 2)  # type: ignore
            sigma = feature.complexity_sigma
        elif sort_by == "value":
            score = feature.value_mu
            variance = float(float(feature.value_sigma) ** 2)  # type: ignore
            sigma = feature.value_sigma
        else:  # ratio
            score = feature.value_mu / max(feature.complexity_mu, 0.1)  # type: ignore
            # Propagate uncertainty for ratio (simplified)
            variance = float(  # type: ignore
                float(feature.value_sigma) ** 2 + float(feature.complexity_sigma) ** 2
            )
            sigma = variance**0.5

        # 95% confidence interval (±1.96 sigma)
        ci_lower = score - 1.96 * sigma
        ci_upper = score + 1.96 * sigma

        ranked.append(
            {
                "rank": rank,
                "feature": FeatureSchema.model_validate(feature),
                "score": score,
                "variance": variance,
                "confidence_interval": [ci_lower, ci_upper],
            }
        )

    if not include_quadrants:
        return ranked

    # Include quadrants in response
    return {
        "ranked": ranked,
        "quadrants": _compute_quadrants(features),
    }


@router.get("/{project_id}/results/quadrants")
def get_quadrant_analysis(
    *,
    db: Session = Depends(deps.get_db),
    project_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get features categorized into four quadrants (Quick-Wins, Strategic, Fill-Ins, Avoid).

    Note: Consider using GET /results?include_quadrants=true instead for combined results.
    """
    project = crud.project.get(db=db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not crud.user.is_superuser(current_user) and (
        project.owner_id != current_user.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Get features for the project
    features = crud.feature.get_multi_by_project(db=db, project_id=project_id)

    return _compute_quadrants(features)


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
        # Sort features based on dimension
        if sort_by == "complexity":
            sorted_features = sorted(
                features, key=lambda f: f.complexity_mu, reverse=True
            )
        elif sort_by == "value":
            sorted_features = sorted(features, key=lambda f: f.value_mu, reverse=True)
        else:  # ratio
            sorted_features = sorted(
                features,
                key=lambda f: f.value_mu / max(f.complexity_mu, 0.1),
                reverse=True,
            )

        # Return JSON array with actual Bayesian scores
        results = []
        for rank, feature in enumerate(sorted_features, start=1):
            results.append(
                {
                    "rank": rank,
                    "id": str(feature.id),
                    "name": feature.name,
                    "description": feature.description,
                    "complexity_mu": feature.complexity_mu,
                    "complexity_sigma": feature.complexity_sigma,
                    "value_mu": feature.value_mu,
                    "value_sigma": feature.value_sigma,
                    "ratio": feature.value_mu / max(feature.complexity_mu, 0.1),
                }
            )
        return results

    else:  # CSV
        # Sort features based on dimension
        if sort_by == "complexity":
            sorted_features = sorted(
                features, key=lambda f: f.complexity_mu, reverse=True
            )
        elif sort_by == "value":
            sorted_features = sorted(features, key=lambda f: f.value_mu, reverse=True)
        else:  # ratio
            sorted_features = sorted(
                features,
                key=lambda f: f.value_mu / max(f.complexity_mu, 0.1),
                reverse=True,
            )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Rank",
                "ID",
                "Name",
                "Description",
                "Complexity μ",
                "Complexity σ",
                "Value μ",
                "Value σ",
                "Value/Complexity Ratio",
            ]
        )

        for rank, feature in enumerate(sorted_features, start=1):
            writer.writerow(
                [
                    rank,
                    str(feature.id),
                    feature.name,
                    feature.description or "",
                    round(feature.complexity_mu, 4),
                    round(feature.complexity_sigma, 4),
                    round(feature.value_mu, 4),
                    round(feature.value_sigma, 4),
                    round(feature.value_mu / max(feature.complexity_mu, 0.1), 4),
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
