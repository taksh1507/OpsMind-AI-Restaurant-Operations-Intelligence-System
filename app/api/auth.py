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
async def get_current_user(
    email: str = None,
    user_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user details.
    
    Note: In a real implementation, this would extract the user from JWT token.
    This is a placeholder for now.
    
    Args:
        email: User email (from token)
        user_id: User ID (from token)
        db: Database session (injected)
        
    Returns:
        User details
    """
    return {"message": "Implement JWT token extraction in dependency"}
