"""Authentication Service

Business logic for user registration, login, and token validation.
"""

from typing import Optional, Tuple
import hashlib
import re
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Tenant, User, RefreshToken, SubscriptionStatus, UserRole
from app.core import hash_password, verify_password, create_access_token, create_refresh_token
from app.models.schemas import RegisterRequest


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.
    
    Args:
        text: Text to slugify
        
    Returns:
        Slugified text
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def hash_refresh_token(raw_token: str) -> str:
    """Return a SHA-256 hex digest of a refresh token.

    Only the digest is stored in the database so a leaked DB cannot be used to
    mint sessions.

    Args:
        raw_token: The raw refresh token string

    Returns:
        SHA-256 hex digest
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def _store_refresh_token(
    session: AsyncSession,
    user: User,
    raw_token: str,
) -> None:
    """Persist a refresh token record for a user."""
    from app.core.config import settings

    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
        revoked=False,
    )
    session.add(token)


async def issue_token_pair(
    session: AsyncSession,
    user: User,
) -> Tuple[str, str]:
    """Issue a new access + refresh token pair for a user.

    Creates the refresh token with a unique jti, persists a digest record for
    server-side validation/revocation, and returns both tokens.

    Args:
        session: AsyncSession for database operations
        user: The authenticated User

    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "role": user.role.value,
        }
    )

    refresh_token = create_refresh_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "role": user.role.value,
        }
    )

    await _store_refresh_token(session, user, refresh_token)
    await session.flush()

    return access_token, refresh_token


async def register_user(
    session: AsyncSession,
    request: RegisterRequest
) -> Tuple[User, Tenant, str, str]:
    """Register a new user and create their tenant (restaurant).
    
    Args:
        session: AsyncSession for database operations
        request: RegisterRequest with restaurant_name, email, password
        
    Returns:
        Tuple of (user, tenant, access_token, refresh_token)
        
    Raises:
        ValueError: If email already exists or registration fails
    """
    
    # Check if email already exists
    email_exists = await session.execute(
        select(User).where(User.email == request.email)
    )
    if email_exists.scalar_one_or_none() is not None:
        raise ValueError(f"Email already registered: {request.email}")
    
    # Create tenant (restaurant)
    tenant_id = _slugify(request.restaurant_name)
    
    # Check if tenant_id already exists
    tenant_exists = await session.execute(
        select(Tenant).where(Tenant.tenant_id == tenant_id)
    )
    if tenant_exists.scalar_one_or_none() is not None:
        # If slug exists, append a random suffix
        tenant_id = f"{tenant_id}-{int(func.random() * 10000)}"
    
    tenant = Tenant(
        tenant_id=tenant_id,
        name=request.restaurant_name,
        subscription_status=SubscriptionStatus.TRIAL
    )
    session.add(tenant)
    await session.flush()  # Flush to get the tenant.id before creating user
    
    # Hash password and create user
    hashed_password = hash_password(request.password)
    user = User(
        tenant_id=tenant.id,
        email=request.email,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=True,  # First user is admin
        role=UserRole.OWNER
    )
    session.add(user)

    # Flush to assign user.id before issuing tokens referencing the user
    await session.flush()

    # Create token pair (access + refresh)
    access_token, refresh_token = await issue_token_pair(session, user)

    await session.commit()

    return user, tenant, access_token, refresh_token


async def get_user_by_email(
    session: AsyncSession,
    email: str
) -> Optional[User]:
    """Get a user by email address.
    
    Args:
        session: AsyncSession for database operations
        email: User email to look up
        
    Returns:
        User object if found, None otherwise
    """
    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str
) -> Optional[User]:
    """Authenticate a user by email and password.
    
    Args:
        session: AsyncSession for database operations
        email: User email
        password: Plain text password to verify
        
    Returns:
        User if authenticated, None if credentials are invalid
    """
    user = await get_user_by_email(session, email)
    
    if user is None or not user.is_active:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


async def refresh_access_token(
    session: AsyncSession,
    raw_refresh_token: str,
) -> Tuple[User, str, str]:
    """Validate a refresh token and issue a new token pair (rotation).

    Server-side validation checks that the token:
    - Exists and is not revoked
    - Belongs to an active user
    - Has not expired

    On success the used refresh token is revoked and a brand-new pair is issued,
    so a refresh token can only ever be used once (rotation/revocation).

    Args:
        session: AsyncSession for database operations
        raw_refresh_token: The raw refresh token from the client

    Returns:
        Tuple of (user, new_access_token, new_refresh_token)

    Raises:
        ValueError: If the token is invalid, revoked, expired, or user inactive
    """
    token_row = (
        await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(raw_refresh_token)
            )
        )
    ).scalar_one_or_none()

    if token_row is None:
        raise ValueError("Invalid refresh token")

    if token_row.revoked:
        raise ValueError("Refresh token has been revoked")

    now = datetime.now(timezone.utc)
    if token_row.expires_at.tzinfo is None:
        expires_at = token_row.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = token_row.expires_at

    if expires_at < now:
        raise ValueError("Refresh token has expired")

    user = (
        await session.execute(select(User).where(User.id == token_row.user_id))
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        raise ValueError("User account is inactive or missing")

    # Rotate: revoke the used token and issue a fresh pair
    await revoke_refresh_token(session, raw_refresh_token)

    access_token, new_refresh_token = await issue_token_pair(session, user)
    await session.commit()

    return user, access_token, new_refresh_token


async def revoke_refresh_token(
    session: AsyncSession,
    raw_refresh_token: str,
) -> bool:
    """Revoke (invalidate) a refresh token by its digest.

    Args:
        session: AsyncSession for database operations
        raw_refresh_token: The raw refresh token to revoke

    Returns:
        True if a token was revoked, False if it did not exist
    """
    token_row = (
        await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(raw_refresh_token)
            )
        )
    ).scalar_one_or_none()

    if token_row is None:
        return False

    token_row.revoked = True
    token_row.revoked_at = datetime.now(timezone.utc)
    await session.commit()
    return True
