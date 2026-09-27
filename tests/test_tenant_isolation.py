"""Tenant-isolation and authentication tests for ``get_current_user``.

Verifies that the core auth dependency:
- resolves a valid token to the right user,
- scopes the user lookup by the token's tenant_id (so a token cannot resolve a
  user outside its own tenant),
- rejects missing/invalid Authorization headers,
- rejects inactive accounts.
"""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.models import Tenant, User, UserRole, SubscriptionStatus


def _request_with_token(token: str | None) -> Request:
    """Build a minimal ASGI GET request, optionally carrying a bearer token."""
    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
    }
    return Request(scope)


async def _seed_user(
    db,
    *,
    tenant_pk: int,
    tenant_slug: str,
    email: str,
    role: UserRole = UserRole.OWNER,
    is_active: bool = True,
) -> User:
    tenant = Tenant(
        id=tenant_pk,
        tenant_id=tenant_slug,
        name=tenant_slug,
        subscription_status=SubscriptionStatus.ACTIVE,
    )
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant_pk,
        email=email,
        hashed_password="x",
        role=role,
        is_active=is_active,
        is_admin=(role == UserRole.OWNER),
    )
    db.add(user)
    await db.commit()
    return user


def _token_for(email: str, tenant_id: int, role: UserRole = UserRole.OWNER) -> str:
    return create_access_token(
        {"sub": email, "tenant_id": tenant_id, "role": role.value}
    )


async def test_valid_token_resolves_user(db_session):
    await _seed_user(
        db_session, tenant_pk=1, tenant_slug="tenant-a", email="alice@a.com"
    )
    token = _token_for("alice@a.com", tenant_id=1)

    user = await get_current_user(_request_with_token(token), db=db_session)

    assert user.email == "alice@a.com"
    assert user.tenant_id == 1


async def test_token_tenant_mismatch_is_rejected(db_session):
    """A token whose tenant_id does not match the user's tenant must not resolve.

    The lookup filters on both email and tenant_id, so a token minted for the
    wrong tenant fails closed with 401 rather than crossing the tenant boundary.
    """
    await _seed_user(
        db_session, tenant_pk=1, tenant_slug="tenant-a", email="alice@a.com"
    )
    # Same email, but the token claims tenant 2 (which alice does not belong to).
    token = _token_for("alice@a.com", tenant_id=2)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_request_with_token(token), db=db_session)
    assert exc.value.status_code == 401


async def test_missing_authorization_header_is_rejected(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_request_with_token(None), db=db_session)
    assert exc.value.status_code == 401


async def test_malformed_token_is_rejected(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_request_with_token("not-a-jwt"), db=db_session)
    assert exc.value.status_code == 401


async def test_inactive_user_is_forbidden(db_session):
    await _seed_user(
        db_session,
        tenant_pk=1,
        tenant_slug="tenant-a",
        email="frozen@a.com",
        is_active=False,
    )
    token = _token_for("frozen@a.com", tenant_id=1)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_request_with_token(token), db=db_session)
    assert exc.value.status_code == 403
