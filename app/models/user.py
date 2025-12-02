from sqlalchemy import Column, String, Boolean
from app.db.base_class import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth users
    is_active: bool = Column(Boolean(), default=True)  # type: ignore
    is_superuser: bool = Column(Boolean(), default=False)  # type: ignore
    role = Column(String, default="user")  # "root" or "user"
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    
    # OAuth fields
    google_id = Column(String, unique=True, index=True, nullable=True)
    auth_provider = Column(String, default="local")  # "local" or "google"
