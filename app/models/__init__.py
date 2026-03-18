"""Database Models Module

SQLAlchemy ORM models for multi-tenant architecture:
- base.py: Base model with common fields (created_at, updated_at)
- tenant.py: Tenant (Restaurant) model
- user.py: User account model
- menu.py: Category and MenuItem models for menu management
- sales.py: Sale and SaleItem models for transaction tracking
- schemas.py: Pydantic request/response schemas
"""

from .base import Base, BaseModel
from .tenant import Tenant, SubscriptionStatus
from .user import User
from .menu import Category, MenuItem
from .sales import Sale, SaleItem, PaymentMethod
from .schemas import (
    RegisterRequest,
    LoginRequest,
    TenantSchema,
    UserSchema,
    TokenResponse,
    RegisterResponse,
)

__all__ = [
    "Base",
    "BaseModel",
    "Tenant",
    "SubscriptionStatus",
    "User",
    "Category",
    "MenuItem",
    "Sale",
    "SaleItem",
    "PaymentMethod",
    "RegisterRequest",
    "LoginRequest",
    "TenantSchema",
    "UserSchema",
    "TokenResponse",
    "RegisterResponse",
]
