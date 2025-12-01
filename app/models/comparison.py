from sqlalchemy import Column, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import uuid


class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    feature_a_id = Column(String, ForeignKey("features.id"), nullable=False)
    feature_b_id = Column(String, ForeignKey("features.id"), nullable=False)
    choice = Column(String, nullable=False)  # "feature_a", "feature_b", "tie"
    dimension = Column(String, nullable=False)  # "complexity", "value"
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Who created the comparison
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete timestamp
    deleted_by = Column(String, ForeignKey("users.id"), nullable=True)  # Who deleted it

    project = relationship("Project", back_populates="comparisons")
    feature_a = relationship("Feature", foreign_keys=[feature_a_id])
    feature_b = relationship("Feature", foreign_keys=[feature_b_id])
    user = relationship("User", foreign_keys=[user_id])
    deleter = relationship("User", foreign_keys=[deleted_by])
