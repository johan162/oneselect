"""
Google OAuth authentication endpoints.
"""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.oauth import oauth
from app.core import security
from app.core.config import settings
from app.api import deps
from app import crud, schemas

router = APIRouter()


@router.get("/google/login")
async def google_login(request: Request) -> Any:
    """
    Redirect to Google OAuth login page.
    AUTH-GOOGLE-01: Initiate Google OAuth flow
    """
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(
    request: Request, 
    db: Session = Depends(deps.get_db)
) -> RedirectResponse:
    """
    Handle Google OAuth callback and create/login user.
    AUTH-GOOGLE-02: Process Google OAuth callback
    """
    try:
        # Get access token from Google
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(
                status_code=400,
                detail="Failed to get user info from Google"
            )
        
        email = user_info.get('email')
        google_id = user_info.get('sub')
        name = user_info.get('name', '')
        picture = user_info.get('picture')
        
        if not email or not google_id:
            raise HTTPException(
                status_code=400,
                detail="Email and Google ID are required"
            )
        
        # Check if user exists by Google ID
        user = crud.user.get_by_google_id(db, google_id=google_id)
        
        if not user:
            # Check if user exists by email (for account linking)
            user = crud.user.get_by_email(db, email=email)
            
            if user:
                # Link existing account to Google
                if user.auth_provider == "local":
                    # Update existing local account with Google ID
                    user.google_id = google_id
                    user.auth_provider = "google"
                    if not user.display_name:
                        user.display_name = name
                    if not user.avatar_url and picture:
                        user.avatar_url = picture
                    db.commit()
                    db.refresh(user)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Account already linked to another provider"
                    )
            else:
                # Create new user
                username = email.split('@')[0]
                
                # Ensure unique username
                base_username = username
                counter = 1
                while crud.user.get_by_username(db, username=username):
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = crud.user.create_google_user(
                    db,
                    email=email,
                    google_id=google_id,
                    username=username,
                    display_name=name,
                    avatar_url=picture
                )
        
        # Create JWT access token
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token
        frontend_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        return RedirectResponse(url=frontend_url)
        
    except HTTPException:
        raise
    except Exception as e:
        # Redirect to frontend with error
        error_url = f"{settings.FRONTEND_URL}/auth/error?message={str(e)}"
        return RedirectResponse(url=error_url)


@router.get("/google/status")
async def google_status() -> dict:
    """
    Check if Google OAuth is configured.
    AUTH-GOOGLE-03: Check Google OAuth configuration status
    """
    is_configured = bool(
        settings.GOOGLE_CLIENT_ID and 
        settings.GOOGLE_CLIENT_SECRET
    )
    return {
        "google_oauth_enabled": is_configured,
        "google_client_id_set": bool(settings.GOOGLE_CLIENT_ID),
        "google_client_secret_set": bool(settings.GOOGLE_CLIENT_SECRET),
    }
