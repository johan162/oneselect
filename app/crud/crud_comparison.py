from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.comparison import Comparison
from app.schemas.comparison import ComparisonCreate, ComparisonUpdate


class CRUDComparison(CRUDBase[Comparison, ComparisonCreate, ComparisonUpdate]):
    def get(self, db: Session, id: str) -> Optional[Comparison]:
        """Override to filter out soft-deleted records"""
        return (
            db.query(self.model)
            .filter(Comparison.id == id, Comparison.deleted_at.is_(None))
            .first()
        )
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Comparison]:
        """Override to filter out soft-deleted records"""
        return (
            db.query(self.model)
            .filter(Comparison.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_multi_by_project(
        self, db: Session, *, project_id: str, skip: int = 0, limit: int = 10000
    ) -> List[Comparison]:
        """Get active (non-deleted) comparisons for a project.
        
        Note: Default limit is high (10000) because this is typically used
        for analysis operations that need ALL comparisons for a project.
        """
        return (
            db.query(self.model)
            .filter(
                Comparison.project_id == project_id,
                Comparison.deleted_at.is_(None)
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_all_by_project_including_deleted(
        self, db: Session, *, project_id: str
    ) -> List[Comparison]:
        """Get all comparisons for a project, including soft-deleted ones"""
        return (
            db.query(self.model)
            .filter(Comparison.project_id == project_id)
            .order_by(Comparison.created_at.desc())
            .all()
        )

    def create_with_project(
        self, db: Session, *, obj_in: ComparisonCreate, project_id: str, user_id: str
    ) -> Comparison:
        """Create comparison with project_id and user_id"""
        obj_in_data = obj_in.model_dump()
        db_obj = Comparison(**obj_in_data, project_id=project_id, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def soft_delete(self, db: Session, *, id: str, deleted_by: str) -> Optional[Comparison]:
        """Soft delete a comparison by setting deleted_at and deleted_by"""
        obj = self.get(db=db, id=id)
        if obj:
            obj.deleted_at = datetime.now(timezone.utc)
            obj.deleted_by = deleted_by
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj


comparison = CRUDComparison(Comparison)

