"""AI Usage Model - Per-tenant metering of Claude API token consumption.

Phase 4: AI usage metering + guardrails.

Every billable AI call (one Anthropic ``messages.create`` request) records one row
here so an Owner can see how much AI their restaurant is using and so the system
can enforce a monthly per-tenant token cap. Rows are written by
``app.services.ai_usage_service`` using token counts captured at the single
Anthropic adapter chokepoint in ``app.services.ai_agent``.

Notes:
- This is a brand-new table, so it is created automatically by
  ``Base.metadata.create_all`` on startup (the app ships without Alembic).
- ``created_at`` (from BaseModel) is the meter timestamp; month-to-date usage is
  summed by comparing it against the start of the current UTC month.
"""

from sqlalchemy import String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class AIUsage(BaseModel):
    """One row per billable AI call, scoped to a single restaurant (tenant)."""

    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Tenant isolation - usage is per-restaurant. Indexed for fast month-to-date
    # aggregation and for the (tenant_id, created_at) composite index below.
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Which product feature spent the tokens (e.g. "daily_tip", "margin_analysis").
    # Used for the per-feature breakdown in the Owner usage view.
    feature: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")

    # The resolved Claude model ID that served the request (e.g. "claude-opus-4-8").
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")

    # Token counts reported by the Anthropic API for this single call.
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Denormalized sum (input + output) so cap enforcement can SUM a single column.
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        # Every quota check filters by tenant_id and a created_at lower bound, so a
        # composite index on exactly those columns keeps the month-to-date SUM fast.
        Index("idx_ai_usage_tenant_created", "tenant_id", "created_at"),
    )


__all__ = ["AIUsage"]
