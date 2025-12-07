from pydantic import BaseModel, ConfigDict, Field
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


class ComparisonStrength(str, Enum):
    """Strength for graded comparisons (5-point scale)."""

    a_much_better = "a_much_better"  # Feature A is much better than B
    a_better = "a_better"  # Feature A is better than B
    equal = "equal"  # Features are equal
    b_better = "b_better"  # Feature B is better than A
    b_much_better = "b_much_better"  # Feature B is much better than A


class ComparisonBase(BaseModel):
    choice: ComparisonChoice
    dimension: Dimension


class ComparisonCreate(ComparisonBase):
    """Standard comparison creation (for backward compatibility)."""

    feature_a_id: str
    feature_b_id: str
    strength: Optional[ComparisonStrength] = None  # Only used for graded mode


class BinaryComparisonCreate(BaseModel):
    """Binary comparison: simple A vs B choice."""

    feature_a_id: str
    feature_b_id: str
    choice: ComparisonChoice
    dimension: Dimension


class GradedComparisonCreate(BaseModel):
    """Graded comparison: 5-point scale."""

    feature_a_id: str
    feature_b_id: str
    dimension: Dimension
    strength: ComparisonStrength = Field(
        ...,
        description="Which feature is better: a_much_better, a_better, equal, b_better, b_much_better",
    )


class ComparisonUpdate(BaseModel):
    choice: Optional[ComparisonChoice] = None
    strength: Optional[ComparisonStrength] = None  # For graded mode updates


class Comparison(ComparisonBase):
    id: uuid.UUID
    project_id: str
    feature_a: Feature
    feature_b: Feature
    created_at: datetime
    strength: Optional[str] = None  # Strength for graded comparisons

    model_config = ConfigDict(from_attributes=True)


class ComparisonWithStats(Comparison):
    """Comparison response with inconsistency statistics."""

    inconsistency_stats: dict


class GradedComparisonWithStats(BaseModel):
    """Graded comparison response with statistics."""

    id: uuid.UUID
    project_id: str
    feature_a: Feature
    feature_b: Feature
    dimension: str
    strength: str
    choice: str  # Derived from strength
    created_at: datetime
    inconsistency_stats: dict

    model_config = ConfigDict(from_attributes=True)


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
