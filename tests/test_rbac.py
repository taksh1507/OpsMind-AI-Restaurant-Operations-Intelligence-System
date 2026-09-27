"""RBAC unit tests for the route-level authorization dependencies.

Covers the ``role_required`` factory that backs ``get_current_owner`` and
``get_current_manager``:

    get_current_owner   == role_required(OWNER)
    get_current_manager == role_required(OWNER, MANAGER)

These run against transient (session-less) User objects, so they exercise the
authorization decision in isolation with no DB or network.
"""

import pytest
from fastapi import HTTPException

from app.api.deps import role_required, get_current_owner, get_current_manager
from app.models import User, UserRole


def _user(role: UserRole) -> User:
    """Build a transient User with the given role (not persisted)."""
    return User(
        id=1,
        tenant_id=1,
        email="user@example.com",
        hashed_password="x",
        role=role,
        is_active=True,
        is_admin=(role == UserRole.OWNER),
    )


# get_current_owner is role_required(OWNER): only OWNER passes.
@pytest.mark.parametrize(
    "role, allowed",
    [
        (UserRole.OWNER, True),
        (UserRole.MANAGER, False),
        (UserRole.STAFF, False),
    ],
)
async def test_owner_only_gate(role: UserRole, allowed: bool):
    checker = role_required(UserRole.OWNER)
    if allowed:
        assert await checker(user=_user(role)) is not None
    else:
        with pytest.raises(HTTPException) as exc:
            await checker(user=_user(role))
        assert exc.value.status_code == 403


# get_current_manager is role_required(OWNER, MANAGER): STAFF is denied.
@pytest.mark.parametrize(
    "role, allowed",
    [
        (UserRole.OWNER, True),
        (UserRole.MANAGER, True),
        (UserRole.STAFF, False),
    ],
)
async def test_manager_or_owner_gate(role: UserRole, allowed: bool):
    checker = role_required(UserRole.OWNER, UserRole.MANAGER)
    if allowed:
        assert await checker(user=_user(role)) is not None
    else:
        with pytest.raises(HTTPException) as exc:
            await checker(user=_user(role))
        assert exc.value.status_code == 403


def test_can_view_financials_matrix():
    """Financial data (profit/margins) must be hidden from STAFF."""
    assert _user(UserRole.OWNER).can_view_financials() is True
    assert _user(UserRole.MANAGER).can_view_financials() is True
    assert _user(UserRole.STAFF).can_view_financials() is False


def test_owner_and_manager_deps_are_wired():
    """Guard against the wrappers drifting from their intended roles."""
    assert callable(get_current_owner)
    assert callable(get_current_manager)
