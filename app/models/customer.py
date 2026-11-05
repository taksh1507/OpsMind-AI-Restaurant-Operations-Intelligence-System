"""Customer Model - Hyper-Personalized Customer Profile

Stores customer contact info, spending, visit count, and flexible preferences (tastes, vibes, allergies, etc).
"""

from sqlalchemy import String, Numeric, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import BaseModel

class Customer(BaseModel):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_customers_tenant_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    total_spent_inr: Mapped[float] = mapped_column(Numeric(precision=12, scale=2), default=0, nullable=False)
    visit_count: Mapped[int] = mapped_column(default=0, nullable=False)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name={self.name}, email={self.email})>"
