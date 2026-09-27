"""Tenant Settings API Router

Owner-managed, per-tenant AI/operational preferences.

- GET /settings    Read this tenant's settings + selectable models (OWNER only)
- PUT /settings    Update AI model, feature toggles, name, timezone (OWNER only)

Both endpoints are OWNER-gated: settings (which AI model to spend on, whether AI
insights run at all) are the owner's domain, consistent with the "owner controls
staff and configuration" product model.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_owner
from app.models import User
from app.models.schemas import SettingsResponse, UpdateSettingsRequest
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Return the current tenant's settings and the selectable AI models."""
    return await settings_service.build_settings_view(db, current_user.tenant_id)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Apply a partial update to the tenant's settings (owner only)."""
    try:
        return await settings_service.update_settings(
            db,
            current_user.tenant_id,
            restaurant_name=request.restaurant_name,
            timezone=request.timezone,
            ai_model=request.ai_model,
            ai_insights_enabled=request.ai_insights_enabled,
            weather_enabled=request.weather_enabled,
            default_city=request.default_city,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
