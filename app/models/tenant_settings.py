"""Tenant Settings Model - Per-Restaurant Preferences

Holds the owner-managed configuration for a single tenant (restaurant): which
Claude model the AI agent should use, whether AI insights / weather-aware
reasoning are enabled, the default city used for weather lookups, and the
restaurant's timezone.

One row per tenant (1:1). Created lazily with sensible defaults the first time
the owner opens the Settings page, so existing tenants don't need a data
backfill. The AI-model default mirrors the process-wide configured model
(settings.anthropic_model) so behaviour is unchanged until the owner picks
something else.
"""

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class TenantSettings(BaseModel):
    """Owner-configurable AI / operational preferences for one tenant."""

    __tablename__ = "tenant_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 1:1 with tenants; unique so a tenant can never have two settings rows.
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # Claude model ID the AI agent uses for this tenant. Validated against the
    # server's allow-list (see settings_service.AVAILABLE_MODELS) before it is
    # ever written, so this always holds a known-selectable value.
    ai_model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Master switch for the AI recommendation surface (daily tip / strategy).
    ai_insights_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Whether the AI agent folds live weather into its recommendations.
    weather_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Default city for weather lookups when a request doesn't supply one.
    default_city: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Display timezone for the restaurant (informational for now).
    timezone: Mapped[str] = mapped_column(
        String(64), default="America/New_York", nullable=False
    )

    tenant = relationship("Tenant", back_populates="settings")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<TenantSettings(tenant_id={self.tenant_id}, "
            f"ai_model={self.ai_model!r}, ai_insights_enabled={self.ai_insights_enabled})>"
        )
