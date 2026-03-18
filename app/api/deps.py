"""FastAPI Dependencies for Authentication and Authorization

Provides reusable dependency functions for protecting routes and extracting
user/tenant context from JWT tokens.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User


# HTTP Bearer security scheme for extracting Authorization header
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate JWT token, return authenticated User with tenant context.
    
    This is the core multi-tenant dependency. Every protected endpoint uses this
    to ensure:
    1. User identity is verified via JWT
    2. User exists in database and is active
    3. Tenant context (tenant_id) is available for data isolation
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session for user lookup
        
    Returns:
        User object with tenant_id for use in other endpoints
        
    Raises:
        HTTPException 401: If token is invalid, expired, or user not found
        HTTPException 403: If user account is inactive
    """
    
    token = credentials.credentials
    
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
