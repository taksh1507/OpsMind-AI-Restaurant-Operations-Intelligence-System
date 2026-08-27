"""User Model - Multi-Tenant User Account with Role-Based Access Control

Represents a user (restaurant owner/staff) in the OpsMind AI system.
Each user belongs to exactly one tenant and has a specific role with permissions.
"""

from typing import Optional
from enum import Enum
from sqlalchemy import String, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class UserRole(str, Enum):
    """
    Role enumeration for Role-Based Access Control (RBAC).
    
    Roles define what operations a user can perform:
    - OWNER: Full access to all restaurant data and operations
    - MANAGER: Access to inventory, staff, and operational analytics
    - STAFF: Access to order taking, table management, basic operations
    """
    OWNER = "owner"          # Full access
    MANAGER = "manager"      # Inventory, staff, operational data
    STAFF = "staff"          # Orders, tables, customer service


class User(BaseModel):
    """
    Multi-tenant user account with Role-Based Access Control.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant)
        email: User email (unique within tenant)
        hashed_password: Bcrypt hashed password
        role: UserRole enum - OWNER, MANAGER, or STAFF (Day 25 RBAC)
        is_active: Whether user account is active
        is_admin: Deprecated (kept for backward compatibility, use role instead)
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        nullable=False,
        default=UserRole.STAFF,
        index=True  # Index for fast role-based queries
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationship to tenant
    tenant = relationship("Tenant", back_populates="users")

    # Relationship to refresh tokens
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role}, tenant_id={self.tenant_id})>"
    
    def has_role(self, *roles: UserRole) -> bool:
        """Check if user has any of the specified roles."""
        return self.role in roles
    
    def is_owner(self) -> bool:
        """Check if user is an owner."""
        return self.role == UserRole.OWNER
    
    def is_manager(self) -> bool:
        """Check if user is a manager or owner."""
        return self.role in (UserRole.MANAGER, UserRole.OWNER)
    
    def can_view_financials(self) -> bool:
        """Check if user can view financial data (profit, margins, costs)."""
        return self.role in (UserRole.OWNER, UserRole.MANAGER)
