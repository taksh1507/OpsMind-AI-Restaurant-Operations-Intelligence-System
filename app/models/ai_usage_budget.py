"""Atomic per-tenant monthly AI token reservation counters."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AIUsageBudget(Base):
    __tablename__ = "ai_usage_budgets"

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    tokens_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_committed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
