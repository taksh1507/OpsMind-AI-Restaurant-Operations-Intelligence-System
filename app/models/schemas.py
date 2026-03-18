"""Authentication and Menu Schemas

Pydantic models for request/response validation in authentication and menu endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal


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


# =============== CATEGORY SCHEMAS ===============


class CategoryCreate(BaseModel):
    """Schema for creating a new category."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Category name (e.g., 'Starters', 'Main Course')"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional category description"
    )
    is_active: bool = Field(
        default=True,
        description="Whether this category is available"
    )


class CategoryResponse(BaseModel):
    """Schema for category response (read)."""
    
    id: int
    tenant_id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        None,
        max_length=500
    )
    is_active: Optional[bool] = None


# =============== MENU ITEM SCHEMAS ===============


class MenuItemCreate(BaseModel):
    """Schema for creating a new menu item."""
    
    category_id: int = Field(
        ...,
        description="ID of the category this item belongs to"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Dish name"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Dish description"
    )
    price: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Selling price (must be > 0)"
    )
    cost_price: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Cost of preparation (must be >= 0)"
    )
    is_available: bool = Field(
        default=True,
        description="Whether this item is available to order"
    )
    
    def validate_price_gt_cost(self) -> "MenuItemCreate":
        """Validate that price > cost_price."""
        if self.price <= self.cost_price:
            raise ValueError("price must be greater than cost_price")
        return self


class MenuItemResponse(BaseModel):
    """Schema for menu item response (read)."""
    
    id: int
    tenant_id: int
    category_id: int
    name: str
    description: Optional[str]
    price: Decimal
    cost_price: Decimal
    is_available: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @property
    def profit_margin(self) -> Decimal:
        """Calculate profit margin as percentage."""
        if self.price == 0:
            return Decimal(0)
        return ((self.price - self.cost_price) / self.price) * 100


class MenuItemUpdate(BaseModel):
    """Schema for updating a menu item."""
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100
    )
    description: Optional[str] = Field(
        None,
        max_length=500
    )
    price: Optional[Decimal] = Field(
        None,
        gt=0,
        decimal_places=2
    )
    cost_price: Optional[Decimal] = Field(
        None,
        ge=0,
        decimal_places=2
    )
    is_available: Optional[bool] = None
