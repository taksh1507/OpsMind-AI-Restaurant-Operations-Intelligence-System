"""User Model - Multi-Tenant User Account

Represents a user (restaurant owner/staff) in the OpsMind AI system.
Each user belongs to exactly one tenant.
"""

from typing import Optional
from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class User(BaseModel):
    """
    Multi-tenant user account.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant)
        email: User email (unique within tenant)
        hashed_password: Bcrypt hashed password
        is_active: Whether user account is active
        is_admin: Whether user has admin privileges in the tenant
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
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationship to tenant
    tenant = relationship("Tenant", back_populates="users")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"
