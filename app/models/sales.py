"""Sales Models - Sale and SaleItem

Represents completed transactions and their line items.
Each sale belongs to exactly one tenant (restaurant).
Sales are immutable records of historical transactions.
"""

from typing import Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, ForeignKey, Numeric, DateTime, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import BaseModel


class PaymentMethod(str, enum.Enum):
    """Payment method enumeration."""
    CASH = "cash"
    CARD = "card"
    DIGITAL_WALLET = "digital_wallet"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"


class Sale(BaseModel):
    """
    A completed sale/transaction/bill.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant) - CRITICAL FOR ISOLATION
        total_amount: Total amount charged (before tax)
        tax_amount: Tax calculated on the sale
        payment_method: How the customer paid (cash, card, digital, etc.)
        timestamp: When the sale was completed
        sale_items: Relationship to items in this sale
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "sales"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        default=Decimal("0.00")
    )
    
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod),
        nullable=False,
        default=PaymentMethod.CASH
    )
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
        index=True  # Index for time-based analytics queries
    )
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    sale_items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Sale(id={self.id}, tenant_id={self.tenant_id}, total={self.total_amount}, timestamp={self.timestamp})>"
    
    @property
    def grand_total(self) -> Decimal:
        """Calculate grand total (subtotal + tax)."""
        return self.total_amount + self.tax_amount
    
    @property
    def item_count(self) -> int:
        """Count total items (sum of all quantities) in this sale."""
        if not self.sale_items:
            return 0
        return sum(item.quantity for item in self.sale_items)


class SaleItem(BaseModel):
    """
    A line item in a sale.
    
    Preserves historical pricing: if menu item price changes later,
    this record keeps the exact price that was charged at time of sale.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant - For data isolation
        sale_id: Foreign key to parent sale
        menu_item_id: Reference to the menu item sold (not FK, allows deletion of menu items)
        quantity: How many units sold
        unit_price_at_sale: The price per unit at time of sale (immutable history)
        created_at: Timestamp when created
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "sale_items"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    menu_item_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True
        # NOTE: Not a foreign key - allows menu item deletion without breaking sales history
    )
    
    quantity: Mapped[int] = mapped_column(
        nullable=False,
        default=1
    )
    
    unit_price_at_sale: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False
    )
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    sale = relationship("Sale", back_populates="sale_items")
    
    def __repr__(self) -> str:
        return f"<SaleItem(id={self.id}, sale_id={self.sale_id}, menu_item_id={self.menu_item_id}, qty={self.quantity})>"
    
    @property
    def line_total(self) -> Decimal:
        """Calculate line total (quantity * unit_price_at_sale)."""
        return self.quantity * self.unit_price_at_sale
