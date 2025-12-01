from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from typing import Optional
import uuid


class UserBase(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

    @field_validator("username")
    @classmethod
    def sanitize_username(cls, v: str) -> str:
        # Remove potential XSS characters
        if "<" in v or ">" in v or '"' in v:
            raise ValueError("Username contains invalid characters")
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=1, max_length=100)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    password: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

    @field_validator("display_name")
    @classmethod
    def sanitize_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v and ("<" in v or ">" in v):
            raise ValueError("Display name contains invalid characters")
        return v


class UserInDBBase(UserBase):
    id: uuid.UUID
    role: str = "user"
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    hashed_password: str
