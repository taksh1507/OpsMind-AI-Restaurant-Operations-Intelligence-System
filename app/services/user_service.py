"""Team / User Management Service

Owner-driven creation and management of staff/manager logins within a single
tenant, plus self-service password change. There is no email/SMTP: the owner
sets (or the server generates) a one-time temporary password, and the teammate
must change it on first login (tracked by User.must_change_password).

Every operation is tenant-scoped through the acting owner, so one restaurant can
never see or mutate another restaurant's users.
"""

import secrets
from typing import Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import hash_password, verify_password
from app.models import User, UserRole, RefreshToken

# Ambiguity-free alphabet (no O/0, I/l/1) so temp passwords are easy to read out.
_TEMP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"

# Roles an owner may assign via team management. OWNER is intentionally excluded.
_ASSIGNABLE = {"manager", "staff"}


def generate_temp_password(length: int = 12) -> str:
    """Generate a readable, reasonably strong one-time password."""
    return "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(length))


async def _get_tenant_user(
    session: AsyncSession, tenant_id: int, user_id: int
) -> Optional[User]:
    """Fetch a user by id, scoped to the given tenant (cross-tenant safe)."""
    result = await session.execute(
        select(User).where((User.id == user_id) & (User.tenant_id == tenant_id))
    )
    return result.scalar_one_or_none()


async def list_team_members(
    session: AsyncSession, tenant_id: int
) -> Sequence[User]:
    """Return every user in the tenant, oldest first (owner appears too)."""
    result = await session.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at)
    )
    return result.scalars().all()


async def create_team_member(
    session: AsyncSession,
    owner: User,
    email: str,
    role: str,
    temp_password: Optional[str] = None,
) -> Tuple[User, str]:
    """Create a staff/manager login in the owner's tenant.

    Returns the created user and the plaintext temporary password (generated if
    the owner did not supply one) so it can be shown to the owner exactly once.

    Raises ValueError if the email is taken or the role is not assignable.
    """
    if role not in _ASSIGNABLE:
        raise ValueError("Role must be 'manager' or 'staff'")

    # email is globally unique in the schema, so check across all tenants.
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"Email already registered: {email}")

    password = temp_password or generate_temp_password()
    member = User(
        tenant_id=owner.tenant_id,
        email=email,
        hashed_password=hash_password(password),
        role=UserRole(role),
        is_active=True,
        is_admin=False,
        must_change_password=True,
    )
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member, password


async def update_team_member(
    session: AsyncSession,
    owner: User,
    user_id: int,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> User:
    """Update a teammate's preset role and/or active status (tenant-scoped).

    Guards: an owner cannot change their own role/status here, and owner
    accounts cannot be modified via team management.
    """
    member = await _get_tenant_user(session, owner.tenant_id, user_id)
    if member is None:
        raise ValueError("Team member not found")
    if member.id == owner.id:
        raise ValueError("You cannot change your own role or status")
    if member.role == UserRole.OWNER:
        raise ValueError("Owner accounts cannot be modified here")

    if role is not None:
        if role not in _ASSIGNABLE:
            raise ValueError("Role must be 'manager' or 'staff'")
        member.role = UserRole(role)
    if is_active is not None:
        member.is_active = is_active

    await session.commit()
    await session.refresh(member)
    return member


async def delete_team_member(
    session: AsyncSession, owner: User, user_id: int
) -> None:
    """Delete a teammate (tenant-scoped). Cannot delete self or an owner."""
    member = await _get_tenant_user(session, owner.tenant_id, user_id)
    if member is None:
        raise ValueError("Team member not found")
    if member.id == owner.id:
        raise ValueError("You cannot delete your own account")
    if member.role == UserRole.OWNER:
        raise ValueError("Owner accounts cannot be deleted here")

    await session.delete(member)
    await session.commit()


async def change_password(
    session: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Change the user's own password and clear the must-change flag.

    Verifies the current (or temporary) password, then rotates it and revokes
    all of the user's outstanding refresh tokens so sessions minted with the old
    credentials cannot outlive the change. Does not commit token issuance — the
    caller reissues a fresh pair after this returns.

    Raises ValueError on a bad current password or an unchanged new password.
    """
    if not verify_password(current_password, user.hashed_password):
        raise ValueError("Current password is incorrect")
    if current_password == new_password:
        raise ValueError("New password must be different from the current one")

    user.hashed_password = hash_password(new_password)
    user.must_change_password = False

    tokens = await session.execute(
        select(RefreshToken).where(
            (RefreshToken.user_id == user.id) & (RefreshToken.revoked == False)
        )
    )
    for token in tokens.scalars().all():
        token.revoked = True

    await session.commit()
