from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime
import uuid


class FeatureBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list)

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


class FeatureCreate(FeatureBase):
    pass


class FeatureUpdate(FeatureBase):
    pass


class Feature(FeatureBase):
    id: uuid.UUID
    project_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
