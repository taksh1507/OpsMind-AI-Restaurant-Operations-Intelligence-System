"""Tenant Model - Multi-Tenant Root (Restaurant)

Represents a restaurant/business in the OpsMind AI system.
Each restaurant is isolated at the database level.
"""

from typing import Optional
from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import BaseModel


class SubscriptionStatus(str, enum.Enum):
    """Subscription statuses for a tenant."""
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class Tenant(BaseModel):
    """
    Multi-tenant root: represents a restaurant/business.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Unique string identifier for the restaurant (slugified name)
        name: Restaurant name
        subscription_status: Current subscription status
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "tenants"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus),
        default=SubscriptionStatus.TRIAL,
        nullable=False
    )
    
    # Relationship to users
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, tenant_id={self.tenant_id}, name={self.name})>"
