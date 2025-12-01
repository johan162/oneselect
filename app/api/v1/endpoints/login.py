from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    AUTH-01: Login
    """
    user = crud.user.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    elif not crud.user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/login/test-token", response_model=schemas.User)
def test_token(current_user: models.User = Depends(deps.get_current_user)) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/register", response_model=schemas.User, status_code=201)
def register(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Register a new user (self-service sign-up).
    AUTH-02: Register
    """
    if user_in.email:
        user = crud.user.get_by_email(db, email=user_in.email)
        if user:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system",
            )
    # Check for duplicate username
    user = crud.user.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
    try:
        user = crud.user.create(db, obj_in=user_in)
    except Exception as e:
        # Catch any database integrity errors
        if "UNIQUE constraint failed" in str(e) or "IntegrityError" in str(type(e)):
            raise HTTPException(
                status_code=400,
                detail="User with this email or username already exists",
            )
        raise
    return user


@router.post("/change-password", status_code=204)
def change_password(
    *,
    db: Session = Depends(deps.get_db),
    current_password: str,
    new_password: str,
    current_user: models.User = Depends(deps.get_current_user),
) -> None:
    """
    Change password for current user.
    AUTH-06: Change Password
    """
    user = crud.user.authenticate(
        db, username=str(current_user.username), password=current_password  # type: ignore
    )
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect password")

    # Update password
    from app.schemas.user import UserUpdate

    user_in = UserUpdate(password=new_password)
    crud.user.update(db, db_obj=current_user, obj_in=user_in)
    return None


@router.post("/refresh")
def refresh_token(
    *,
    db: Session = Depends(deps.get_db),
    refresh_token: str,
) -> Any:
    """
    Refresh an expired JWT token using a refresh token.
    AUTH-03: Refresh Token

    Note: This is a placeholder implementation. In production, you would:
    1. Store refresh tokens in database
    2. Validate the refresh token
    3. Check if it's expired or revoked
    4. Issue new access and refresh tokens
    """
    # Placeholder: Decode and validate refresh token
    # For now, just return a mock response
    raise HTTPException(
        status_code=501,
        detail="Refresh token functionality requires refresh token storage implementation",
    )


@router.get("/me", response_model=schemas.User)
def get_current_user(
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Get the profile of the currently authenticated user.
    AUTH-05: Get Current User
    """
    return current_user


@router.patch("/me", response_model=schemas.User)
def update_profile(
    *,
    db: Session = Depends(deps.get_db),
    email: Optional[str] = Body(None),
    display_name: Optional[str] = Body(None),
    avatar_url: Optional[str] = Body(None),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Update mutable profile attributes for the current user.
    AUTH-07: Update Profile
    """
    from app.schemas.user import UserUpdate

    update_data = {}
    if email is not None:
        update_data["email"] = email
    if display_name is not None:
        update_data["full_name"] = display_name  # Map to existing field
    # avatar_url would need to be added to User model

    if update_data:
        user_in = UserUpdate(**update_data)
        try:
            user = crud.user.update(db, db_obj=current_user, obj_in=user_in)
        except Exception as e:
            # Catch database integrity errors
            if "UNIQUE constraint failed" in str(e) or "IntegrityError" in str(type(e)):
                raise HTTPException(
                    status_code=400,
                    detail="Email already exists in the system",
                )
            raise
        return user
    return current_user


@router.post("/logout", status_code=204)
def logout(
    current_user: models.User = Depends(deps.get_current_user),
) -> None:
    """
    Logout (token invalidation would be handled by client or token blacklist).
    AUTH-04: Logout
    """
    # In a stateless JWT system, logout is typically handled client-side
    # For a production system, implement token blacklisting here
    return None
