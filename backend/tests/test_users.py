"""Tests for auth/user endpoints."""

import logging
import uuid

import pytest
from httpx import AsyncClient

from src.logging_config import SkipSentryFilter
from src.users.crud import get_session
from src.users.utils import hash_password, create_access_token, create_refresh_token, verify_token
from src.users.routers import verify_access_token
from tests.conftest import USER_1_PAYLOAD
from tests.test_tournaments import compare_item




NEW_USER_1_PAYLOAD = {
    "email": "newuser1@example.com",
    "password": "securepassword123",
    "first_name": "One",
}


def test_skip_sentry_filter_ignores_marked_records():
    """Records marked to skip Sentry are filtered out of Sentry handlers."""
    filter_instance = SkipSentryFilter()

    record = logging.LogRecord("auth", logging.WARNING, __file__, 1, "unauthorized", (), None)
    assert filter_instance.filter(record) is True

    record.skip_sentry = True
    assert filter_instance.filter(record) is False


# ============================================================================
# Registration
# ============================================================================


@pytest.mark.asyncio
async def test_register_success(client_unauth: AsyncClient, db_session):
    """POST /auth/register creates a new user and returns user info."""
    resp = await client_unauth.post("/auth/register", json={**NEW_USER_1_PAYLOAD, "email": NEW_USER_1_PAYLOAD["email"].upper()})
    assert resp.status_code == 201
    data = resp.json()
    user = data["user"]
    compare_item(NEW_USER_1_PAYLOAD, user, exclude_keys=["password"])
    assert "id" in user

    # Verify access token cookie contains correct uid
    token_payload = verify_access_token(resp.cookies["access_token"])
    assert token_payload["uid"] == user["id"]

    # Verify session ID is valid UUID and corresponds to a session in the database
    assert uuid.UUID(token_payload["sid"])
    session = await get_session(db_session, token_payload["sid"])
    assert session is not None
    assert session.user_id == user["id"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client_unauth: AsyncClient):
    """POST /auth/register with existing email returns 409."""
    resp = await client_unauth.post("/auth/register", json=NEW_USER_1_PAYLOAD)
    assert resp.status_code == 201
    resp = await client_unauth.post("/auth/register", json={**NEW_USER_1_PAYLOAD, "email": NEW_USER_1_PAYLOAD["email"].upper()})
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()
    assert len(resp.cookies) == 0


@pytest.mark.asyncio
async def test_register_short_password(client_unauth: AsyncClient):
    """POST /auth/register with short password returns 422."""
    resp = await client_unauth.post("/auth/register", json={**NEW_USER_1_PAYLOAD, "password": "short"})
    assert resp.status_code == 422
    assert len(resp.cookies) == 0


@pytest.mark.asyncio
async def test_register_invalid_email(client_unauth: AsyncClient):
    """POST /auth/register with invalid email returns 422."""
    resp = await client_unauth.post("/auth/register", json={**NEW_USER_1_PAYLOAD, "email": "not-an-email"})
    assert resp.status_code == 422
    assert len(resp.cookies) == 0


# ============================================================================
# Login
# ============================================================================


@pytest.mark.asyncio
async def test_login_success(client_unauth: AsyncClient, db_session):
    """POST /auth/login with valid credentials returns user info and sets cookies."""
    # Use test user 1 from conftest fixture
    resp = await client_unauth.post("/auth/login", json=USER_1_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    user = data["user"]
    compare_item(USER_1_PAYLOAD, user, exclude_keys=["password"])

    # Verify access token cookie contains correct uid
    token_payload = verify_access_token(resp.cookies["access_token"])
    assert token_payload["uid"] == user["id"]

    # Verify session ID is valid UUID and corresponds to a session in the database
    assert uuid.UUID(token_payload["sid"])
    session = await get_session(db_session, token_payload["sid"])
    assert session is not None
    assert session.user_id == user["id"]


@pytest.mark.asyncio
async def test_login_wrong_password(client_unauth: AsyncClient):
    """POST /auth/login with wrong password returns 401."""
    resp = await client_unauth.post("/auth/login", json={**USER_1_PAYLOAD, "password": "wrongpassword"})
    assert resp.status_code == 401
    assert len(resp.cookies) == 0


@pytest.mark.asyncio
async def test_login_nonexistent_user(client_unauth: AsyncClient):
    """POST /auth/login with unknown email returns 401."""
    resp = await client_unauth.post("/auth/login", json={**USER_1_PAYLOAD, "email": "wrong@example.com"})
    assert resp.status_code == 401
    assert len(resp.cookies) == 0


# ============================================================================
# Token refresh
# ============================================================================


@pytest.mark.asyncio
async def test_refresh_missing_token(client_unauth: AsyncClient):
    """POST /auth/refresh without refresh token returns 401."""
    resp = await client_unauth.post("/auth/refresh")
    assert resp.status_code == 401
    assert len(resp.cookies) == 0


@pytest.mark.asyncio
async def test_refresh_success(client_unauth: AsyncClient, db_session):
    """POST /auth/refresh with valid refresh token rotates session."""
    resp = await client_unauth.post("/auth/register", json=NEW_USER_1_PAYLOAD)
    data = resp.json()
    user = data["user"]
    refresh_original = resp.cookies["refresh_token"]
    
    # Verify refresh token cookie contains correct uid
    token_payload = verify_token(refresh_original)
    assert int(token_payload["uid"]) == user["id"]
    assert token_payload["type"] == "refresh"

    # Verify session ID is valid UUID and corresponds to a session in the database
    session_id_original = token_payload["sid"]
    assert uuid.UUID(session_id_original)
    session = await get_session(db_session, session_id_original)
    assert session is not None
    assert session.user_id == user["id"]

    # refresh the token and verify new tokens and session
    resp = await client_unauth.post("/auth/refresh", cookies={
        "access_token": resp.cookies["access_token"],
        "refresh_token": refresh_original,
    })
    assert resp.status_code == 200
    data = resp.json()
    user = data["user"]
    compare_item(NEW_USER_1_PAYLOAD, user, exclude_keys=["password"])
    refresh_new = resp.cookies["refresh_token"]
    token_payload = verify_token(refresh_new)
    assert int(token_payload["uid"]) == user["id"]
    assert session_id_original != token_payload["sid"]  # Session ID should be rotated
    assert refresh_new != refresh_original  # Refresh token should be rotated
    session_original = await get_session(db_session, session_id_original)
    session_new = await get_session(db_session, token_payload["sid"])
    assert session_original.revoked is True  # Old session should be revoked
    assert session_new.revoked is False  # New session should be active

    # check if new access token is valid and contains correct uid
    access_new = resp.cookies["access_token"]
    resp = await client_unauth.get("/auth/me", cookies={"access_token": access_new})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == user["id"]


@pytest.mark.asyncio
async def test_refresh_revoked_session(client_unauth: AsyncClient, db_session):
    """POST /auth/refresh with a revoked session returns 401."""
    from src.users.crud import create_session, revoke_session

    session_id = "revoked-session"
    await create_session(db_session, 1, session_id)
    await revoke_session(db_session, session_id)

    refresh = create_refresh_token(data={"uid": "1", "sid": session_id})
    resp = await client_unauth.post("/auth/refresh", cookies={"refresh_token": refresh})
    assert resp.status_code == 401


# ============================================================================
# Logout
# ============================================================================


@pytest.mark.asyncio
async def test_logout_success(client_unauth: AsyncClient, db_session):
    """POST /auth/logout clears cookies and revokes session."""
    # Login
    resp = await client_unauth.post("/auth/login", json=USER_1_PAYLOAD)
    assert resp.status_code == 200
    session_id = verify_access_token(resp.cookies["access_token"])["sid"]

    # Logout
    resp = await client_unauth.post("/auth/logout", cookies={"access_token": resp.cookies["access_token"]})
    assert resp.status_code == 200
    assert len(resp.cookies) == 0

    # Check if session is revoked in the database
    session = await get_session(db_session, session_id)
    assert session.revoked is True


# ============================================================================
# Get current user (/auth/me)
# ============================================================================


@pytest.mark.asyncio
async def test_get_me(client_unauth: AsyncClient):
    """GET /auth/me returns the authenticated user's info."""
    # Login
    resp = await client_unauth.post("/auth/login", json=USER_1_PAYLOAD)
    assert resp.status_code == 200

    # Get current user info
    resp = await client_unauth.get("/auth/me", cookies={"access_token": resp.cookies["access_token"]})
    assert resp.status_code == 200
    user = resp.json()
    compare_item(USER_1_PAYLOAD, user, exclude_keys=["password"])


# ============================================================================
# Change password
# ============================================================================


@pytest.mark.asyncio
async def test_change_password_success(client_unauth: AsyncClient, db_session):
    """POST /auth/change-password with correct current password succeeds."""
    # Login
    resp = await client_unauth.post("/auth/login", json=USER_1_PAYLOAD)
    assert resp.status_code == 200

    # Change password
    resp = await client_unauth.post("/auth/change-password", json={
        "current_password": USER_1_PAYLOAD["password"],
        "new_password": "newsecurepassword",
    }, cookies={"access_token": resp.cookies["access_token"]})
    assert resp.status_code == 204

    # Try logging in with old password (should fail)
    resp = await client_unauth.post("/auth/login", json=USER_1_PAYLOAD)
    assert resp.status_code == 401

    # Try logging in with new password (should succeed)
    resp = await client_unauth.post("/auth/login", json={**USER_1_PAYLOAD, "password": "newsecurepassword"})
    assert resp.status_code == 200
    compare_item(USER_1_PAYLOAD, resp.json()["user"], exclude_keys=["password"])



@pytest.mark.asyncio
async def test_change_password_wrong_current(client_unauth: AsyncClient, db_session):
    """POST /auth/change-password with wrong current password returns 401."""
    # Login
    resp = await client_unauth.post("/auth/login", json=USER_1_PAYLOAD)
    assert resp.status_code == 200

    # Change password with wrong current password - failed
    resp = await client_unauth.post("/auth/change-password", json={
        "current_password": "wrongpassword",
        "new_password": "newpassword1",
    }, cookies={"access_token": resp.cookies["access_token"]})
    assert resp.status_code == 401

    # Verify password was not changed by logging in with the original password (should succeed)
    resp = await client_unauth.post("/auth/login", json=USER_1_PAYLOAD)
    assert resp.status_code == 200
    compare_item(USER_1_PAYLOAD, resp.json()["user"], exclude_keys=["password"])


@pytest.mark.asyncio
async def test_change_password_same_password(client_unauth: AsyncClient, db_session):
    """POST /auth/change-password with same new password returns 400."""
    # Login
    resp = await client_unauth.post("/auth/login", json=USER_1_PAYLOAD)
    assert resp.status_code == 200

    # Change password to the same password - should fail
    resp = await client_unauth.post("/auth/change-password", json={
        "current_password": USER_1_PAYLOAD["password"],
        "new_password": USER_1_PAYLOAD["password"],
    }, cookies={"access_token": resp.cookies["access_token"]})
    assert resp.status_code == 400
    assert "new password must differ from current password" in resp.json()["detail"].lower()


# ============================================================================
# Forgot password
# ============================================================================


@pytest.mark.asyncio
async def test_forgot_password_existing_email(client_unauth: AsyncClient):
    """POST /auth/forgot-password always returns 200 (no email leak)."""
    resp = await client_unauth.post("/auth/forgot-password", json={
        "email": "test@example.com",
    })
    assert resp.status_code == 200
    assert "reset link" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_forgot_password_unknown_email(client_unauth: AsyncClient):
    """POST /auth/forgot-password with unknown email still returns 200."""
    resp = await client_unauth.post("/auth/forgot-password", json={
        "email": "unknown@example.com",
    })
    assert resp.status_code == 200


# ============================================================================
# Reset password
# ============================================================================


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client_unauth: AsyncClient):
    """POST /auth/reset-password with invalid token returns 400."""
    resp = await client_unauth.post("/auth/reset-password", json={
        "token": "nonexistent-token",
        "new_password": "newpassword1",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_success(client_unauth: AsyncClient, db_session):
    """POST /auth/reset-password with valid token resets the password."""
    from src.users.crud import create_password_reset_token

    await create_password_reset_token(db_session, user_id=1, token="valid-reset-token", expire_minutes=30)

    resp = await client_unauth.post("/auth/reset-password", json={
        "token": "valid-reset-token",
        "new_password": "resetpassword1",
    })
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_reset_password_used_token(client_unauth: AsyncClient, db_session):
    """POST /auth/reset-password with already-used token returns 400."""
    from src.users.crud import create_password_reset_token, clear_password_reset_token

    await create_password_reset_token(db_session, user_id=1, token="used-token", expire_minutes=30)
    await clear_password_reset_token(db_session, 1)

    resp = await client_unauth.post("/auth/reset-password", json={
        "token": "used-token",
        "new_password": "newpassword1",
    })
    assert resp.status_code == 400



