"""Tests for the authentication service: registration and refresh-token rotation.

Exercises the full server-side token lifecycle that Phase 5 depends on:
- registration creates an OWNER + TRIAL tenant and issues a token pair,
- credentials are verified correctly,
- refreshing rotates the token (old one is revoked, a new pair is issued),
- an explicitly revoked token can no longer be refreshed.
"""

import pytest

from app.models import UserRole, SubscriptionStatus
from app.models.schemas import RegisterRequest
from app.services.auth_service import (
    register_user,
    authenticate_user,
    refresh_access_token,
    revoke_refresh_token,
)


def _register_request(email: str = "owner@test.com") -> RegisterRequest:
    return RegisterRequest(
        restaurant_name="Test Bistro",
        email=email,
        password="password123",
    )


async def test_register_creates_owner_and_tenant(db_session):
    user, tenant, access_token, refresh_token = await register_user(
        db_session, _register_request()
    )

    assert user.role == UserRole.OWNER
    assert user.is_admin is True
    assert user.is_active is True
    assert tenant.subscription_status == SubscriptionStatus.TRIAL
    assert access_token and refresh_token


async def test_register_duplicate_email_rejected(db_session):
    await register_user(db_session, _register_request())
    with pytest.raises(ValueError):
        await register_user(db_session, _register_request())


async def test_authenticate_user_password_check(db_session):
    await register_user(db_session, _register_request())

    assert await authenticate_user(db_session, "owner@test.com", "password123") is not None
    assert await authenticate_user(db_session, "owner@test.com", "wrong-pass") is None
    assert await authenticate_user(db_session, "nobody@test.com", "password123") is None


async def test_refresh_rotates_and_revokes_old_token(db_session):
    _, _, _, refresh_token = await register_user(db_session, _register_request())

    _, new_access, new_refresh = await refresh_access_token(db_session, refresh_token)
    assert new_access
    assert new_refresh != refresh_token

    # The original token was rotated out and can no longer be used.
    with pytest.raises(ValueError):
        await refresh_access_token(db_session, refresh_token)


async def test_revoked_token_cannot_refresh(db_session):
    _, _, _, refresh_token = await register_user(db_session, _register_request())

    assert await revoke_refresh_token(db_session, refresh_token) is True
    with pytest.raises(ValueError):
        await refresh_access_token(db_session, refresh_token)


async def test_unknown_refresh_token_rejected(db_session):
    with pytest.raises(ValueError):
        await refresh_access_token(db_session, "totally-made-up-token")
