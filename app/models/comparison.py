from sqlalchemy import Column, String, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import uuid
import enum


class ComparisonStrength(str, enum.Enum):
    """Strength of comparison for graded mode (5-point scale)."""

    a_much_better = "a_much_better"  # A is much better than B (strong signal)
    a_better = "a_better"  # A is better than B (normal signal)
    equal = "equal"  # A and B are equal (both converge)
    b_better = "b_better"  # B is better than A (normal signal)
    b_much_better = "b_much_better"  # B is much better than A (strong signal)


class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    feature_a_id = Column(String, ForeignKey("features.id"), nullable=False)
    feature_b_id = Column(String, ForeignKey("features.id"), nullable=False)
    choice = Column(String, nullable=False)  # "feature_a", "feature_b", "tie"
    dimension = Column(String, nullable=False)  # "complexity", "value"

    # Strength for graded comparisons (null for binary mode)
    # Maps to ComparisonStrength enum: a_much_better, a_better, equal, b_better, b_much_better
    strength = Column(String, nullable=True)

    user_id = Column(
        String, ForeignKey("users.id"), nullable=True
    )  # Who created the comparison
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete timestamp
    deleted_by = Column(String, ForeignKey("users.id"), nullable=True)  # Who deleted it

    project = relationship("Project", back_populates="comparisons")
    feature_a = relationship("Feature", foreign_keys=[feature_a_id])
    feature_b = relationship("Feature", foreign_keys=[feature_b_id])
    user = relationship("User", foreign_keys=[user_id])
    deleter = relationship("User", foreign_keys=[deleted_by])

    # Indexes for analytics queries
    __table_args__ = (
        Index("ix_comparisons_project_dimension", "project_id", "dimension"),
        Index("ix_comparisons_strength", "strength"),
        Index("ix_comparisons_created_at", "created_at"),
    )
