from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime
import uuid


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        # Remove potential XSS characters
        if "<" in v or ">" in v:
            raise ValueError("Name contains invalid characters")
        return v.strip()

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: Optional[str]) -> Optional[str]:
        if v and ("<" in v or ">" in v):
            raise ValueError("Description contains invalid characters")
        return v.strip() if v else v


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class Project(ProjectBase):
    id: uuid.UUID
    created_at: datetime
    owner_id: str
    total_comparisons: int = 0
    complexity_avg_variance: float = 1.0
    value_avg_variance: float = 1.0

    model_config = ConfigDict(from_attributes=True)


class ProjectSummary(BaseModel):
    project: Project
    feature_count: int
    comparisons: dict
    average_variance: dict
    inconsistency_count: dict
