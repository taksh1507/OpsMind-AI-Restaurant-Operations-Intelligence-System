"""Tenant Settings Service

Owner-managed, per-tenant AI/operational preferences: which Claude model the AI
agent uses, whether AI insights and weather-aware reasoning are enabled, the
default city for weather lookups, and the restaurant's timezone (plus the
editable restaurant name, which lives on the Tenant row itself).

Settings rows are created lazily with sensible defaults the first time they are
read, so existing tenants need no data backfill. The AI-model default mirrors
the process-wide configured model (settings.anthropic_model), keeping behaviour
unchanged until an owner picks something else.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Tenant, TenantSettings


# Curated set of models an owner may select. Labels/descriptions are shown in
# the Settings dropdown. The configured default model is always merged in (see
# available_models) so the known-working model is never missing from the list.
_CURATED_MODELS: list[dict] = [
    {
        "id": "claude-opus-4-8",
        "label": "Claude Opus 4.8",
        "description": "Most capable — deepest operational analysis (default).",
    },
    {
        "id": "claude-sonnet-5",
        "label": "Claude Sonnet 5",
        "description": "Balanced speed and capability for everyday insights.",
    },
    {
        "id": "claude-haiku-4-5-20251001",
        "label": "Claude Haiku 4.5",
        "description": "Fastest and most economical for high-volume use.",
    },
]


def _default_model() -> str:
    """The process-wide configured model, used as the per-tenant default."""
    return settings.anthropic_model or "claude-opus-4-8"


def available_models() -> list[dict]:
    """Return the selectable models, guaranteeing the configured default is present.

    The deployed Anthropic-compatible endpoint may only serve a subset of these;
    the configured default is known-working, so it is always offered (and moved
    to the front) even if it isn't in the curated list.
    """
    default_id = _default_model()
    models = [dict(m) for m in _CURATED_MODELS]
    if not any(m["id"] == default_id for m in models):
        models.insert(
            0,
            {
                "id": default_id,
                "label": default_id,
                "description": "Configured default model.",
            },
        )
    return models


def available_model_ids() -> set[str]:
    """Set of model IDs an owner is allowed to select."""
    return {m["id"] for m in available_models()}


async def get_or_create_settings(
    session: AsyncSession, tenant_id: int
) -> TenantSettings:
    """Fetch this tenant's settings row, creating it with defaults if absent."""
    result = await session.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    row = TenantSettings(
        tenant_id=tenant_id,
        ai_model=_default_model(),
        ai_insights_enabled=True,
        weather_enabled=settings.weather_enabled,
        default_city=None,
        timezone="America/New_York",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def build_settings_view(session: AsyncSession, tenant_id: int) -> dict:
    """Assemble the owner-facing settings payload (tenant name + prefs + models)."""
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Tenant not found")
    prefs = await get_or_create_settings(session, tenant_id)
    return {
        "restaurant_name": tenant.name,
        "timezone": prefs.timezone,
        "ai_model": prefs.ai_model,
        "ai_insights_enabled": prefs.ai_insights_enabled,
        "weather_enabled": prefs.weather_enabled,
        "default_city": prefs.default_city,
        "available_models": available_models(),
    }


async def update_settings(
    session: AsyncSession,
    tenant_id: int,
    *,
    restaurant_name: Optional[str] = None,
    timezone: Optional[str] = None,
    ai_model: Optional[str] = None,
    ai_insights_enabled: Optional[bool] = None,
    weather_enabled: Optional[bool] = None,
    default_city: Optional[str] = None,
) -> dict:
    """Apply a partial update to the tenant's settings (and restaurant name).

    Raises ValueError if ai_model is not one of the selectable model IDs.
    Returns the refreshed settings view.
    """
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Tenant not found")
    prefs = await get_or_create_settings(session, tenant_id)

    if ai_model is not None:
        if ai_model not in available_model_ids():
            raise ValueError(f"Unknown AI model: {ai_model}")
        prefs.ai_model = ai_model
    if timezone is not None:
        prefs.timezone = timezone
    if ai_insights_enabled is not None:
        prefs.ai_insights_enabled = ai_insights_enabled
    if weather_enabled is not None:
        prefs.weather_enabled = weather_enabled
    if default_city is not None:
        # Normalise empty string to NULL so "clear the city" round-trips cleanly.
        prefs.default_city = default_city.strip() or None
    if restaurant_name is not None:
        name = restaurant_name.strip()
        if not name:
            raise ValueError("Restaurant name cannot be empty")
        tenant.name = name

    await session.commit()
    return await build_settings_view(session, tenant_id)


# --- Helpers used by the AI agent wiring -----------------------------------


async def resolve_ai_model(session: AsyncSession, tenant_id: int) -> str:
    """Return the model this tenant's AI calls should use (falls back to default)."""
    prefs = await get_or_create_settings(session, tenant_id)
    return prefs.ai_model or _default_model()


async def get_ai_flags(session: AsyncSession, tenant_id: int) -> TenantSettings:
    """Return the tenant's settings row so callers can read feature toggles."""
    return await get_or_create_settings(session, tenant_id)
