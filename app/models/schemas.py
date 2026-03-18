"""Authentication Schemas

Pydantic models for request/response validation in authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class TenantSchema(BaseModel):
    """Tenant response schema."""
    
    id: int
    tenant_id: str
    name: str
    subscription_status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserSchema(BaseModel):
    """User response schema (safe - no password)."""
    
    id: int
    email: str
    tenant_id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    """Registration request schema."""
    
    restaurant_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the restaurant"
    )
    email: EmailStr = Field(
        ...,
        description="Owner's email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimum 8 characters)"
    )


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration time in seconds")


class RegisterResponse(BaseModel):
    """Registration response schema."""
    
    user: UserSchema
    tenant: TenantSchema
    access_token: str
    token_type: str = "bearer"
