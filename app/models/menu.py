"""Menu Models - Categories and Menu Items

Represents the restaurant's menu structure.
Each category and menu item belongs to exactly one tenant (restaurant).
"""

from typing import Optional
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Boolean, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Category(BaseModel):
    """
    Menu category (e.g., "Starters", "Main Course", "Desserts").
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant) - CRITICAL FOR ISOLATION
        name: Category name (e.g., "Starters")
        description: Optional description of the category
        is_active: Whether this category is available in the menu
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    menu_items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class MenuItem(BaseModel):
    """
    Menu item (dish) within a category.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant) - CRITICAL FOR ISOLATION
        category_id: Foreign key to parent category
        name: Dish name
        description: Description of the dish
        price: Selling price
        cost_price: Cost to prepare (for profit calculation)
        is_available: Whether this item can be ordered
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "menu_items"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Price stored as Numeric for financial accuracy (not float)
    price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False
    )
    
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False
    )
    
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    category = relationship("Category", back_populates="menu_items")
    
    def __repr__(self) -> str:
        return f"<MenuItem(id={self.id}, name={self.name}, category_id={self.category_id}, tenant_id={self.tenant_id})>"
    
    @property
    def profit_margin(self) -> Decimal:
        """Calculate profit margin as percentage (price - cost_price) / price * 100"""
        if self.price == 0:
            return Decimal(0)
        return ((self.price - self.cost_price) / self.price) * 100
