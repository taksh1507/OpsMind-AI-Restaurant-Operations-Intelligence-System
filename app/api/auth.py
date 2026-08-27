"""Authentication API Router

Handles user authentication endpoints: register, login, logout.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RevokeRequest,
)
from app.services.auth_service import (
    register_user,
    authenticate_user,
    issue_token_pair,
    refresh_access_token,
    revoke_refresh_token,
)
from app.core import create_access_token
from app.models import User
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import _get_ip, is_rate_limited, record_failed_attempt, clear_failures

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new restaurant owner and create their tenant.
    
    Args:
        request: Registration request with restaurant name, email, and password
        db: Database session (injected)
        
    Returns:
        RegisterResponse with user, tenant, access token, and refresh token
        
    Raises:
        HTTPException 400: If email already exists or validation fails
        HTTPException 500: If database error occurs
    """
    try:
        user, tenant, access_token, refresh_token = await register_user(db, request)
        
        return RegisterResponse(
            user=user,
            tenant=tenant,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    raw_request: Request = None,
):
    """Login a user and return an access + refresh token pair.

    Rate-limited: max 5 failed attempts per IP per 5-minute window.
    """
    # Rate-limit check
    client_ip = _get_ip(raw_request) if raw_request else "unknown"
    limited, remaining = is_rate_limited(client_ip)
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {remaining}s."
        )

    user = await authenticate_user(db, request.email, request.password)

    if not user:
        record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    clear_failures(client_ip)
    access_token, refresh_token = await issue_token_pair(db, user)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Exchange a valid refresh token for a new access + refresh token pair (rotation).

    The presented refresh token is revoked and a fresh pair is returned, so a
    refresh token can only ever be used once.

    Args:
        request: Refresh request containing the refresh token
        db: Database session (injected)

    Returns:
        TokenResponse with new access + refresh token pair

    Raises:
        HTTPException 401: If the refresh token is invalid, revoked, or expired
    """
    try:
        _, access_token, refresh_token = await refresh_access_token(db, request.refresh_token)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: RevokeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Revoke a refresh token (server-side logout).

    Args:
        request: Revoke request containing the refresh token to invalidate
        db: Database session (injected)

    Returns:
        204 No Content
    """
    await revoke_refresh_token(db, request.refresh_token)
    return None


@router.get("/me")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user's profile.
    
    This is a protected endpoint that proves the multi-tenant auth logic works.
    Only accessible with a valid JWT token in the Authorization header.
    
    The get_current_user dependency handles:
    1. Extracting JWT from Authorization header
    2. Validating token and decoding claims
    3. Verifying user exists in database
    4. Returning User object with tenant_id for data isolation
    
    Args:
        current_user: Authenticated User injected by get_current_user dependency
        
    Returns:
        User profile with email, role, and tenant_id to confirm session scoping
    """
    return {
        "status": "authenticated",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": "admin" if current_user.is_admin else "staff",
            "is_active": current_user.is_active
        },
        "tenant": {
            "id": current_user.tenant_id,
            "multi_tenant_isolation": True,
            "message": "This user can only see their own restaurant's data"
        }
    }
