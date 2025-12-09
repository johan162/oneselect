from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Float, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import uuid
import enum


class ComparisonMode(str, enum.Enum):
    """Comparison mode for a project."""

    binary = "binary"  # Simple A vs B choice
    graded = "graded"  # 5-point scale: much_worse, worse, equal, better, much_better


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    total_comparisons = Column(Integer, default=0, nullable=False)
    complexity_avg_variance = Column(Float, default=1.0, nullable=False)
    value_avg_variance = Column(Float, default=1.0, nullable=False)

    # Comparison mode: binary (default) or graded (5-point scale)
    comparison_mode = Column(
        String, default=ComparisonMode.binary.value, nullable=False
    )

    owner = relationship("User", backref="projects")
    features = relationship(
        "Feature", back_populates="project", cascade="all, delete-orphan"
    )
    comparisons = relationship(
        "Comparison", back_populates="project", cascade="all, delete-orphan"
    )
