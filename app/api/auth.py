"""Authentication API Router

Handles user authentication endpoints: register, login, logout.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import RegisterRequest, RegisterResponse, LoginRequest, TokenResponse
from app.services.auth_service import register_user, authenticate_user, get_user_by_email
from app.core import create_access_token
from app.models import User, Tenant
from app.api.deps import get_current_user

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
        RegisterResponse with user, tenant, and access token
        
    Raises:
        HTTPException 400: If email already exists or validation fails
        HTTPException 500: If database error occurs
    """
    try:
        user, tenant, access_token = await register_user(db, request)
        
        return RegisterResponse(
            user=user,
            tenant=tenant,
            access_token=access_token
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
    db: AsyncSession = Depends(get_db)
):
    """Login a user and return an access token.
    
    Args:
        request: Login request with email and password
        db: Database session (injected)
        
    Returns:
        TokenResponse with access token
        
    Raises:
        HTTPException 401: If credentials are invalid
    """
    user = await authenticate_user(db, request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "tenant_id": user.tenant_id
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=1440 * 60  # in seconds
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
            "role": "admin" if current_user.is_admin else "staff",
            "is_active": current_user.is_active
        },
        "tenant": {
            "id": current_user.tenant_id,
            "multi_tenant_isolation": True,
            "message": "This user can only see their own restaurant's data"
        }
    }
