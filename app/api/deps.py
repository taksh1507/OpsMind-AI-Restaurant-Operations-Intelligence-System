"""FastAPI Dependencies for Authentication and Authorization

Provides reusable dependency functions for protecting routes and extracting
user/tenant context from JWT tokens, plus role-based access control.

Day 25: Role-Based Access Control (RBAC)
- get_current_user: Basic authentication
- role_required: Fine-grained access control based on user role
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Callable

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User, UserRole


# HTTP Bearer security scheme for extracting Authorization header
security = HTTPBearer()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate JWT token, return authenticated User with tenant context.
    
    This is the core multi-tenant dependency. Every protected endpoint uses this
    to ensure:
    1. User identity is verified via JWT
    2. User exists in database and is active
    3. Tenant context (tenant_id) is available for data isolation
    
    Args:
        request: HTTP request containing Authorization header
        db: Database session for user lookup
        
    Returns:
        User object with tenant_id for use in other endpoints
        
    Raises:
        HTTPException 401: If token is invalid, expired, or user not found
        HTTPException 403: If user account is inactive
    """
    
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token from "Bearer <token>"
    token = auth_header.split(" ")[1]
    
    # Decode JWT token
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract user email from 'sub' claim
    user_email: str = payload.get("sub")
    
    if user_email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user email",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Query database to verify user exists and is active
    from sqlalchemy import select
    result = await db.execute(
        select(User).where(User.email == user_email)
    )
    user: Optional[User] = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Return user with tenant_id for endpoint use
    # This ensures all operations are scoped to the user's tenant
    return user


def role_required(*allowed_roles: UserRole) -> Callable:
    """
    FastAPI dependency to enforce role-based access control (RBAC).
    
    This is a factory that returns a dependency function, enabling clean,
    reusable role checking on protected endpoints.
    
    Usage:
        @router.get("/analytics/profit", dependencies=[Depends(role_required(UserRole.OWNER, UserRole.MANAGER))])
        async def get_profit(user: User = Depends(get_current_user)):
            ...
    
    Args:
        *allowed_roles: Variable number of allowed UserRole enums
        
    Returns:
        Dependency function that validates user role
        
    Raises:
        HTTPException 403: If user's role is not in allowed_roles
        
    Security Pattern: Implements Principle of Least Privilege (PoLP)
    - OWNER: Full access to all data
    - MANAGER: Access to operational analytics and staff/inventory
    - STAFF: Access only to order taking and table management
    """
    
    async def check_role(user: User = Depends(get_current_user)) -> User:
        """Check if user has one of the required roles."""
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join([r.value for r in allowed_roles])}. User role: {user.role.value}"
            )
        return user
    
    return check_role


async def get_current_owner(
    user: User = Depends(role_required(UserRole.OWNER))
) -> User:
    """Dependency for endpoints restricted to OWNER role only."""
    return user


async def get_current_manager(
    user: User = Depends(role_required(UserRole.OWNER, UserRole.MANAGER))
) -> User:
    """Dependency for endpoints requiring OWNER or MANAGER role."""
    return user
