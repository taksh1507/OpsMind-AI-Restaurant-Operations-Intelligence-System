"""Tenant-scoped import receipts enforce idempotency across workers."""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import BaseModel


class ImportedOrder(BaseModel):
    __tablename__ = "imported_orders"
    __table_args__ = (
        UniqueConstraint("tenant_id", "order_id", name="uq_imported_order"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[str] = mapped_column(String(128))
    content_hash: Mapped[str] = mapped_column(String(64))
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="RESTRICT"))
