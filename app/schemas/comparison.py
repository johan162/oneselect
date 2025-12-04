from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
import uuid
from enum import Enum
from app.schemas.feature import Feature


class Dimension(str, Enum):
    complexity = "complexity"
    value = "value"


class ComparisonChoice(str, Enum):
    feature_a = "feature_a"
    feature_b = "feature_b"
    tie = "tie"


class ComparisonBase(BaseModel):
    choice: ComparisonChoice
    dimension: Dimension


class ComparisonCreate(ComparisonBase):
    feature_a_id: str
    feature_b_id: str


class ComparisonUpdate(BaseModel):
    choice: Optional[ComparisonChoice] = None


class Comparison(ComparisonBase):
    id: uuid.UUID
    project_id: str
    feature_a: Feature
    feature_b: Feature
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComparisonWithStats(Comparison):
    """Comparison response with inconsistency statistics."""

    inconsistency_stats: dict


class ComparisonResult(BaseModel):
    status: str
    updated_variance: float


class ComparisonPair(BaseModel):
    comparison_id: Optional[uuid.UUID]
    feature_a: Feature
    feature_b: Feature
    dimension: Dimension


class InconsistencyCycle(BaseModel):
    """Represents a detected cycle in comparison graph (e.g., A>B, B>C, C>A)."""

    feature_ids: list[str]
    feature_names: list[str]
    length: int
    dimension: str


class InconsistencyResponse(BaseModel):
    """Response containing all detected cycles and inconsistencies."""

    cycles: list[InconsistencyCycle]
    count: int
    message: str
