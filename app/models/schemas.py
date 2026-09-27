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


class RefreshRequest(BaseModel):
    """Refresh token request schema.

    Optional: browser clients present the refresh token via the httpOnly cookie
    instead of the body, so this may be empty.
    """

    refresh_token: Optional[str] = None


class RevokeRequest(BaseModel):
    """Revoke (logout) request schema.

    Optional: browser clients present the refresh token via the httpOnly cookie
    instead of the body, so this may be empty.
    """

    refresh_token: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration time in seconds")
    must_change_password: bool = Field(
        default=False,
        description="True when the user is still on a temporary password and must "
        "change it before continuing.",
    )


class RegisterResponse(BaseModel):
    """Registration response schema."""

    user: UserSchema
    tenant: TenantSchema
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


# =============== TEAM / STAFF MANAGEMENT SCHEMAS ===============

from typing import Literal  # noqa: E402  (kept local to the team schemas)

# Roles an owner may assign to a teammate. An owner cannot mint another OWNER
# through team management — ownership stays with the account that registered.
AssignableRole = Literal["manager", "staff"]


class TeamMemberResponse(BaseModel):
    """A teammate as shown in the owner's team management view (no secrets)."""

    id: int
    email: str
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateTeamMemberRequest(BaseModel):
    """Owner request to create a staff/manager login."""

    email: EmailStr = Field(..., description="Teammate's login email")
    role: AssignableRole = Field(
        default="staff", description="Preset role: manager or staff"
    )
    temp_password: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Optional one-time password. If omitted, the server generates "
        "one and returns it once so the owner can share it.",
    )


class CreateTeamMemberResponse(BaseModel):
    """Created teammate plus the one-time password to hand off (shown once)."""

    member: TeamMemberResponse
    temp_password: str = Field(
        description="Share this with the teammate. They must change it on first login."
    )


class UpdateTeamMemberRequest(BaseModel):
    """Owner update to a teammate's preset role or active status."""

    role: Optional[AssignableRole] = None
    is_active: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    """A user changing their own password (also clears must_change_password)."""

    current_password: str = Field(..., description="Current (or temporary) password")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password (min 8 chars)"
    )


# =============== TENANT SETTINGS SCHEMAS ===============


class ModelOption(BaseModel):
    """A selectable AI model offered to the owner in Settings."""

    id: str
    label: str
    description: str


class SettingsResponse(BaseModel):
    """The owner-facing view of a tenant's settings.

    Combines the editable restaurant name (stored on the tenant) with the
    per-tenant AI/operational preferences, plus the server's allow-list of
    selectable models so the frontend can render the model dropdown.
    """

    restaurant_name: str
    timezone: str
    ai_model: str
    ai_insights_enabled: bool
    weather_enabled: bool
    default_city: Optional[str] = None
    available_models: list[ModelOption] = []


class UpdateSettingsRequest(BaseModel):
    """Owner update to tenant settings. Every field is optional (partial update)."""

    restaurant_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    ai_model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Must be one of the server's available model IDs.",
    )
    ai_insights_enabled: Optional[bool] = None
    weather_enabled: Optional[bool] = None
    default_city: Optional[str] = Field(default=None, max_length=120)


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
        description="Selling price (must be > 0)"
    )
    cost_price: Decimal = Field(
        ...,
        ge=0,
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
        gt=0
    )
    cost_price: Optional[Decimal] = Field(
        None,
        ge=0
    )
    is_available: Optional[bool] = None


# =============== SALE SCHEMAS ===============


class SaleItemRequest(BaseModel):
    """Schema for a single line item in a sale request."""
    
    menu_item_id: int = Field(
        ...,
        description="ID of the menu item being purchased"
    )
    quantity: int = Field(
        ...,
        gt=0,
        description="Quantity must be greater than 0"
    )


class SaleCreateRequest(BaseModel):
    """Schema for creating a new sale (checkout).
    
    Accepts a list of items with quantities.
    The system will fetch current prices, calculate total, and save the transaction.
    """
    
    items: list[SaleItemRequest] = Field(
        ...,
        min_items=1,
        description="List of items being purchased (at least 1)"
    )
    payment_method: str = Field(
        default="cash",
        description="Payment method: cash, card, digital_wallet, upi, bank_transfer"
    )
    tax_rate: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Optional tax rate as percentage (e.g., 0.05 for 5%)"
    )


class SaleItemResponse(BaseModel):
    """Schema for a line item in sale response (read)."""
    
    id: int
    sale_id: int
    menu_item_id: int
    quantity: int
    unit_price_at_sale: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True
    
    @property
    def line_total(self) -> Decimal:
        """Calculate line total."""
        return self.quantity * self.unit_price_at_sale


class SaleResponse(BaseModel):
    """Schema for sale response (read)."""
    
    id: int
    tenant_id: int
    total_amount: Decimal
    tax_amount: Decimal
    payment_method: str
    timestamp: datetime
    sale_items: list[SaleItemResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @property
    def grand_total(self) -> Decimal:
        """Calculate grand total (subtotal + tax)."""
        return self.total_amount + self.tax_amount
    
    @property
    def item_count(self) -> int:
        """Count total items in this sale."""
        return sum(item.quantity for item in self.sale_items) if self.sale_items else 0
