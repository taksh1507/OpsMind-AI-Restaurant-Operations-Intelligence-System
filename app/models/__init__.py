"""Database Models Module

SQLAlchemy ORM models for multi-tenant architecture:
- base.py: Base model with common fields (created_at, updated_at)
- tenant.py: Tenant (Restaurant) model
- user.py: User account model
- menu.py: Category, MenuItem, Ingredient, and Recipe models
- sales.py: Sale and SaleItem models for transaction tracking
- review.py: Review model
- staff.py: Staff, Shift models
- recommendation.py: AI-generated recommendations tracking
- schemas.py: Pydantic request/response schemas
"""

from .base import Base, BaseModel
from .tenant import Tenant, SubscriptionStatus
from .user import User
from .menu import Category, MenuItem, Ingredient, Recipe
from .sales import Sale, SaleItem, PaymentMethod
from .review import Review
from .staff import Staff, Shift, StaffRole
from .recommendation import Recommendation, RecommendationCategory, RecommendationStatus
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
    "Ingredient",
    "Recipe",
    "Sale",
    "SaleItem",
    "PaymentMethod",
    "Review",
    "Staff",
    "Shift",
    "StaffRole",
    "Recommendation",
    "RecommendationCategory",
    "RecommendationStatus",
    "RegisterRequest",
    "LoginRequest",
    "TenantSchema",
    "UserSchema",
    "TokenResponse",
    "RegisterResponse",
]
