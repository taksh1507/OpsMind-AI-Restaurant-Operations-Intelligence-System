"""Authentication API Router

Handles user authentication endpoints: register, login, logout.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RevokeRequest,
    ChangePasswordRequest,
)
from app.services.auth_service import (
    register_user,
    authenticate_user,
    issue_token_pair,
    refresh_access_token,
    revoke_refresh_token,
)
from app.services import user_service
from app.core import create_access_token
from app.models import User
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import _get_ip, is_rate_limited, record_failed_attempt, clear_failures

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger("opsmind.auth")


# --- httpOnly refresh-token cookie helpers ----------------------------------

def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Attach the refresh token to the response as an httpOnly cookie.

    httpOnly keeps it out of reach of JavaScript/XSS; SameSite blocks it on
    cross-site POSTs (our CSRF defense); Secure must be enabled over HTTPS.
    """
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh-token cookie (used on logout)."""
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
    )


def _extract_refresh_token(raw_request: Request, body_token: str | None) -> str | None:
    """Resolve the refresh token from the httpOnly cookie, then the body.

    Browser clients send it via the cookie; the body fallback keeps non-browser
    API consumers (scripts, mobile) working.
    """
    cookie_token = raw_request.cookies.get(settings.refresh_cookie_name)
    return cookie_token or body_token


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Register a new restaurant owner and create their tenant.

    Args:
        request: Registration request with restaurant name, email, and password
        response: Response used to set the httpOnly refresh-token cookie
        db: Database session (injected)

    Returns:
        RegisterResponse with user, tenant, and access token. The refresh token
        is delivered as an httpOnly cookie, not in the body.

    Raises:
        HTTPException 400: If email already exists or validation fails
        HTTPException 500: If database error occurs
    """
    try:
        user, tenant, access_token, refresh_token = await register_user(db, request)

        # Refresh token goes out only as an httpOnly cookie (kept out of JS/XSS).
        _set_refresh_cookie(response, refresh_token)

        return RegisterResponse(
            user=user,
            tenant=tenant,
            access_token=access_token,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log the real cause server-side (never leak internals to the client).
        logger.exception("Registration failed for email=%s: %s", request.email, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    raw_request: Request = None,
):
    """Login a user and return an access token (refresh token set as httpOnly cookie).

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

    # Refresh token goes out only as an httpOnly cookie (kept out of JS/XSS).
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        must_change_password=user.must_change_password,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    raw_request: Request,
    request: Optional[RefreshRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access token (rotation).

    The refresh token is read from the httpOnly cookie (falling back to the
    request body for non-browser clients). The presented token is revoked and a
    fresh pair is issued, so a refresh token can only ever be used once; the new
    refresh token is written back as an httpOnly cookie.

    Args:
        response: Response used to set the rotated refresh-token cookie
        raw_request: Raw request carrying the refresh cookie
        request: Optional body containing the refresh token (non-browser clients)
        db: Database session (injected)

    Returns:
        TokenResponse with a new access token (refresh token set as cookie)

    Raises:
        HTTPException 401: If the refresh token is missing, invalid, revoked, or expired
    """
    presented_token = _extract_refresh_token(
        raw_request, request.refresh_token if request else None
    )
    if not presented_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        _, access_token, refresh_token = await refresh_access_token(db, presented_token)
        _set_refresh_cookie(response, refresh_token)
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.access_token_expire_minutes * 60
        )
    except ValueError as e:
        # On failure the client receives 401 and clears its own session; the stale
        # cookie is already invalid server-side (revoked/expired), so it is inert.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    raw_request: Request,
    request: Optional[RevokeRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Revoke a refresh token (server-side logout) and clear the cookie.

    Reads the refresh token from the httpOnly cookie (falling back to the body),
    revokes it, and always clears the cookie so the browser session ends.

    Args:
        response: Response used to clear the refresh-token cookie
        raw_request: Raw request carrying the refresh cookie
        request: Optional body containing the refresh token (non-browser clients)
        db: Database session (injected)

    Returns:
        204 No Content
    """
    presented_token = _extract_refresh_token(
        raw_request, request.refresh_token if request else None
    )
    if presented_token:
        await revoke_refresh_token(db, presented_token)

    _clear_refresh_cookie(response)
    return None


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    request: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's own password.

    Used both for the forced first-login change (temporary password → real one,
    which clears must_change_password) and for ordinary password changes. On
    success every existing refresh token for the user is revoked and a fresh
    token pair is issued, so the caller stays logged in with new credentials
    while any old sessions are invalidated.
    """
    try:
        await user_service.change_password(
            db,
            user=current_user,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    # Issue a brand-new pair now that old refresh tokens are revoked.
    access_token, refresh_token = await issue_token_pair(db, current_user)
    await db.commit()
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        must_change_password=False,
    )


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
            # Real RBAC role (owner/manager/staff) drives frontend permissions;
            # the is_admin boolean is retained separately for backward-compat.
            "role": current_user.role.value,
            "is_admin": current_user.is_admin,
            "is_active": current_user.is_active,
            "must_change_password": current_user.must_change_password
        },
        "tenant": {
            "id": current_user.tenant_id,
            "multi_tenant_isolation": True,
            "message": "This user can only see their own restaurant's data"
        }
    }
