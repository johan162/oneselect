from sqlalchemy import Column, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import uuid


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", backref="projects")
    features = relationship(
        "Feature", back_populates="project", cascade="all, delete-orphan"
    )
    comparisons = relationship(
        "Comparison", back_populates="project", cascade="all, delete-orphan"
    )
