"""Authentication Service

Business logic for user registration, login, and token validation.
"""

from typing import Optional, Tuple
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Tenant, User, SubscriptionStatus
from app.core import hash_password, verify_password, create_access_token
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


async def register_user(
    session: AsyncSession,
    request: RegisterRequest
) -> Tuple[User, Tenant, str]:
    """Register a new user and create their tenant (restaurant).
    
    Args:
        session: AsyncSession for database operations
        request: RegisterRequest with restaurant_name, email, password
        
    Returns:
        Tuple of (user, tenant, access_token)
        
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
        is_admin=True  # First user is admin
    )
    session.add(user)
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "tenant_id": tenant.id
        }
    )
    
    await session.commit()
    
    return user, tenant, access_token


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
