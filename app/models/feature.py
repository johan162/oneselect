from sqlalchemy import Column, String, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import uuid


class Feature(Base):
    __tablename__ = "features"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="features")
