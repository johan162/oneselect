from typing import List

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.feature import Feature
from app.schemas.feature import FeatureCreate, FeatureUpdate


class CRUDFeature(CRUDBase[Feature, FeatureCreate, FeatureUpdate]):
    def get_multi_by_project(
        self, db: Session, *, project_id: str, skip: int = 0, limit: int = 100
    ) -> List[Feature]:
        return (
            db.query(self.model)
            .filter(Feature.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_project(
        self, db: Session, *, obj_in: FeatureCreate, project_id: str
    ) -> Feature:
        obj_in_data = obj_in.model_dump()
        db_obj = Feature(**obj_in_data, project_id=project_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


feature = CRUDFeature(Feature)
