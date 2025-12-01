from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from pydantic.networks import EmailStr
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Retrieve users.
    """
    users = crud.user.get_multi(db, skip=skip, limit=limit)
    return users


@router.post("/", response_model=schemas.User)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Create new user.
    """
    if user_in.email:
        user = crud.user.get_by_email(db, email=user_in.email)
        if user:
            raise HTTPException(
                status_code=400,
                detail="The user with this username already exists in the system.",
            )
    user = crud.user.create(db, obj_in=user_in)
    return user


@router.post("/{user_id}/assignments")
def assign_project(
    *,
    db: Session = Depends(deps.get_db),
    user_id: str,
    project_id: str = Body(..., embed=True, alias="projectId"),
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Assign a project to a specific user. Root access required.
    USER-02: Assign Project
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = crud.project.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Note: This requires a project_assignments table in the database
    # For now, this is a placeholder that acknowledges the assignment
    # In production, you would store this relationship in the database
    return {"message": "Project assigned"}


@router.put("/me", response_model=schemas.User)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    password: Optional[str] = Body(None),
    username: Optional[str] = Body(None),
    email: Optional[EmailStr] = Body(None),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    current_user_data = jsonable_encoder(current_user)
    user_in = schemas.UserUpdate(**current_user_data)
    if password is not None:
        user_in.password = password
    if email is not None:
        user_in.email = email
    user = crud.user.update(db, db_obj=current_user, obj_in=user_in)
    return user


@router.get("/me", response_model=schemas.User)
def read_user_me(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.get("/{user_id}", response_model=schemas.User)
def read_user_by_id(
    user_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Get a specific user by id.
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        return user
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return user


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: str,
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update a user.
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    user = crud.user.update(db, db_obj=user, obj_in=user_in)
    return user


@router.delete("/{user_id}", status_code=204, response_class=Response)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: str,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Response:
    """
    Delete a user.
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    crud.user.remove(db, id=user_id)
    return Response(status_code=204)


@router.patch("/{user_id}/role", response_model=schemas.User)
def update_user_role(
    *,
    db: Session = Depends(deps.get_db),
    user_id: str,
    role: str = Body(..., embed=True),
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Update user role (grant or revoke root access).
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if role not in ["root", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_in = schemas.UserUpdate(is_superuser=(role == "root"))
    user = crud.user.update(db, db_obj=user, obj_in=user_in)
    return user


@router.get("/{user_id}/projects", response_model=List[schemas.Project])
def read_user_projects(
    *,
    db: Session = Depends(deps.get_db),
    user_id: str,
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Get all projects for a specific user. Root access required.
    """
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    projects = crud.project.get_multi_by_owner(db=db, owner_id=user_id)
    return projects
