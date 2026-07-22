"""
Authentication routes: register, login, logout, change password.
Implements secure cookie-based JWT session management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.users import crud as user_crud, models
from src.users.utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_password,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
import uuid
from src.users.crud import (
    create_session, revoke_session, get_session, rotate_session,
    revoke_all_user_sessions, create_password_reset_token,
    get_valid_password_reset_token, clear_password_reset_token,
)
from src.users.models import Session as SessionModel
from src.emails.password_reset_email import send_password_reset_email
from src.config import settings
from src.logging_config import get_logger

logger = get_logger("auth")
from typing import Optional
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================================
# Dependency: Get current authenticated user from access token cookie
# ============================================================================

def verify_access_token(
    access_token: Optional[str] = Cookie(None),
) -> dict:
    """
    Dependency: verifies the JWT access token signature and expiration.
    Pure crypto check — no DB access. Session validity is intentionally NOT
    checked here; that only happens at token refresh time.
    """
    if not access_token:
        logger.warning("Missing access token", extra={"skip_sentry": True})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(access_token, token_type="access")
    if payload is None:
        logger.warning("Access token invalid or expired", extra={"skip_sentry": True})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("uid")
    if not user_id:
        logger.warning("Access token missing user_id", extra={"skip_sentry": True})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    payload["uid"] = int(payload["uid"])
    return payload


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_access_token),
) -> models.UserRead:
    """
    Dependency: resolves the authenticated user from a verified access token.
    """
    user_id = token_payload["uid"]
    user = await user_crud.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        logger.warning(f"User not found or inactive: {user_id}", extra={"skip_sentry": True})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return models.UserRead.model_validate(user)


# ============================================================================
# Auth endpoints
# ============================================================================


@router.post("/register", response_model=models.TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: models.UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account and log them in.
    
    Creates a new user with the provided email and password. Passwords are securely hashed using Argon2 before storage.
    After registration, the user is automatically logged in and JWT tokens are set as HttpOnly cookies.
    
    **Request body:**
    - **email**: Unique email address
    - **password**: Minimum 8 characters, will be hashed before storage
    
    **Returns:** The newly created user and sets cookies (HTTP 201)
    
    **Errors:**
    - 409 Conflict: Email already registered
    """
    # Check if user already exists
    existing_user = await user_crud.get_user_by_email(db, user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Create user with hashed password
    user = await user_crud.create_user(db, user_create)
    # Create a new session in DB
    session_id = str(uuid.uuid4())
    await create_session(db, user.id, session_id)
    access_token = create_access_token(data={"uid": str(user.id), "sid": session_id})
    refresh_token = create_refresh_token(data={"uid": str(user.id), "sid": session_id})

    # Set access_token cookie (short-lived, sent to all endpoints)
    access_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60 - 5,
        expires=access_token_expiry.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/",
    )
    # Set refresh_token cookie (long-lived, sent ONLY to /auth/refresh)
    refresh_token_expiry = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 - 5,
        expires=refresh_token_expiry.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/api/auth/refresh",
    )
    logger.info(f"User {user.id} registered and logged in, session {session_id}")
    return models.TokenResponse(
        user=models.UserRead.model_validate(user),
    )



@router.post("/login", response_model=models.TokenResponse)
async def login(
    user_login: models.UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and set JWT tokens as HttpOnly cookies.
    Implements refresh token rotation and session tracking.
    """
    user = await user_crud.authenticate_user(db, user_login.email, user_login.password)
    if not user:
        logger.info(f"Failed login attempt for email: {user_login.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    # Create a new session in DB
    session_id = str(uuid.uuid4())
    await create_session(db, user.id, session_id)
    access_token = create_access_token(data={"uid": str(user.id), "sid": session_id})
    refresh_token = create_refresh_token(data={"uid": str(user.id), "sid": session_id})

    # Set access_token cookie (short-lived, sent to all endpoints)
    access_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60 - 5,
        expires=access_token_expiry.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/",
    )
    # Set refresh_token cookie (long-lived, sent ONLY to /auth/refresh)
    refresh_token_expiry = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 - 5,
        expires=refresh_token_expiry.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/api/auth/refresh",
    )
    logger.info(f"User {user.id} logged in, session {session_id}")
    return models.TokenResponse(
        # access_token=access_token,
        # token_type="bearer",
        user=models.UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=models.TokenResponse)
async def refresh_token(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None),
):
    """
    Refresh access token using refresh token from HttpOnly cookie.
    Implements refresh token rotation, session revocation, and replay attack detection.
    """
    if not refresh_token:
        logger.warning("Missing refresh token on refresh", extra={"skip_sentry": True})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    payload = verify_token(refresh_token, token_type="refresh")
    if payload is None:
        logger.warning("Invalid or expired refresh token", extra={"skip_sentry": True})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    user_id = payload.get("uid")
    session_id = payload.get("sid")
    if not user_id or not session_id:
        logger.warning("Refresh token missing user_id or session_id", extra={"skip_sentry": True})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    session = await get_session(db, session_id)
    if not session or session.revoked:
        logger.warning(f"Replay attack detected for session {session_id} (user {user_id})")
        response.delete_cookie(
            key="access_token",
            secure=settings.https_auth_only,
            httponly=True,
            samesite="strict",
            path="/",
        )
        response.delete_cookie(
            key="refresh_token",
            secure=settings.https_auth_only,
            httponly=True,
            samesite="strict",
            path="/api/auth/refresh",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked or replay attack detected",
        )
    user = await user_crud.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        logger.warning(f"User not found or inactive: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    # Rotate session in DB
    new_session_id = str(uuid.uuid4())
    await rotate_session(db, session_id, user.id, new_session_id)
    new_access_token = create_access_token(data={"uid": str(user.id), "sid": new_session_id})
    new_refresh_token = create_refresh_token(data={"uid": str(user.id), "sid": new_session_id})
    access_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60 - 5,
        expires=access_token_expiry.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/",
    )
    refresh_token_expiry = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 - 5,
        expires=refresh_token_expiry.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/api/auth/refresh",
    )
    logger.info(f"User {user.id} refreshed session {session_id} -> {new_session_id}")
    return models.TokenResponse(
        # access_token=new_access_token,
        # token_type="bearer",
        user=models.UserRead.model_validate(user),
    )



@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: models.UserRead = Depends(get_current_user),
    access_token: Optional[str] = Cookie(None),
    refresh_token: Optional[str] = Cookie(None),
):
    """
    Logout the authenticated user by clearing cookies and revoking session.
    """
    # Revoke session if possible (DB)
    session_id = None
    if access_token:
        payload = verify_token(access_token)
        if payload and payload.get("sid"):
            session_id = payload["sid"]
    elif refresh_token:
        payload = verify_token(refresh_token)
        if payload and payload.get("sid"):
            session_id = payload["sid"]
    if session_id:
        await revoke_session(db, session_id)
        logger.info(f"User {current_user.id} logged out, session {session_id} revoked")
    else:
        logger.info(f"User {current_user.id} logged out, no session found to revoke")
    response.delete_cookie(
        key="access_token",
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/",
    )
    response.delete_cookie(
        key="refresh_token",
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/api/auth/refresh",
    )
    return {"message": "Logged out successfully"}


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    change_pwd_req: models.ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.UserRead = Depends(get_current_user),
):
    """
    Change password for the authenticated user.
    
    Verifies the current password and updates it with the new one.
    
    **Authentication:** Required (Bearer token)
    
    **Request body:**
    - **current_password**: User's current password for verification
    - **new_password**: New password (minimum 8 characters, must be different from current)
    
    **Returns:** No content (HTTP 204)
    
    **Errors:**
    - 400 Bad Request: New password same as current password
    - 401 Unauthorized: Current password is incorrect
    - 404 Not Found: User not found
    """
    # Get full user object to verify current password
    user = await user_crud.get_user_by_id(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(change_pwd_req.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    
    # Prevent reusing the same password
    if verify_password(change_pwd_req.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from current password",
        )
    
    # Update password and invalidate all existing sessions
    await user_crud.set_user_password(db, user.id, change_pwd_req.new_password)
    await revoke_all_user_sessions(db, user.id)
    return None


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: models.ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate a password reset.

    Always returns HTTP 200 regardless of whether the email is registered, to
    avoid leaking which addresses exist. If the email is found, a single-use
    reset link is sent (or logged to the console if SMTP is not configured).
    """
    user = await user_crud.get_user_by_email(db, body.email)
    if user and user.is_active:
        token = str(uuid.uuid4())
        expire_minutes = getattr(settings, "password_reset_expire_minutes", 30)
        await create_password_reset_token(db, user.id, token, expire_minutes)
        reset_link = f"{settings.main_host.rstrip('/')}/reset-password?token={token}"
        await send_password_reset_email(user.email, reset_link, first_name=user.first_name or "there")
        logger.info("Password reset requested for user %s", user.id)
    return {"message": "If that email is registered you will receive a reset link shortly."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    body: models.ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete a password reset using a token from the reset email.

    **Request body:**
    - **token**: The reset token from the email link
    - **new_password**: New password (minimum 8 characters)

    **Returns:** No content (HTTP 204)

    **Errors:**
    - 400 Bad Request: Token is invalid, already used, or expired
    """
    reset_token = await get_valid_password_reset_token(db, body.token)
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )
    await user_crud.set_user_password(db, reset_token.id, body.new_password)
    await clear_password_reset_token(db, reset_token.id)
    await revoke_all_user_sessions(db, reset_token.id)
    logger.info("Password reset completed for user %s", reset_token.id)
    return None


@router.get("/me", response_model=models.UserRead)
async def get_current_user_info(
    current_user: models.UserRead = Depends(get_current_user),
):
    """
    Get the authenticated user's profile information.
    
    Returns the complete user profile for the authenticated user.
    
    **Authentication:** Required (Bearer token in Authorization header)
    
    **Returns:** User profile (HTTP 200)
    
    **Errors:**
    - 401 Unauthorized: Missing or invalid token
    """
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: models.UserRead = Depends(get_current_user),
):
    """
    Permanently delete the authenticated user's account.

    Removes all predictions, withdraws admin/participant memberships, and deletes
    any competitions where the user was the sole admin. This action is irreversible.

    **Authentication:** Required

    **Returns:** No content (HTTP 204)
    """
    await user_crud.delete_account(db, current_user.id)
    logger.info(f"User {current_user.id} deleted their account")
    response.delete_cookie(
        key="access_token",
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/",
    )
    response.delete_cookie(
        key="refresh_token",
        secure=settings.https_auth_only,
        httponly=True,
        samesite="strict",
        path="/api/auth/refresh",
    )
    return None


@router.patch("/me", response_model=models.UserRead)
async def update_current_user(
    body: models.UserUpdate,
    current_user: models.UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the authenticated user's profile (first name, last name, username, gender, email).

    **Authentication:** Required

    **Returns:** Updated user profile (HTTP 200)
    """
    # Strip superuser/is_active fields — users cannot elevate their own privileges
    safe_update = models.UserUpdate(
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        user_name=body.user_name,
        gender=body.gender,
    )
    updated = await user_crud.update_user(db, current_user.id, safe_update)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated
