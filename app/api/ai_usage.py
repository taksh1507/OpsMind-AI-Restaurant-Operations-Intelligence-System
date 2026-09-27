"""AI Usage API Router

Owner-facing view of this restaurant's month-to-date AI consumption and its
monthly cap (Phase 4).

- GET /ai-usage    Month-to-date token usage, remaining allowance, and a
                   per-feature breakdown (OWNER only).

Owner-gated because AI spend is an operational/billing concern, consistent with
the product model where the Owner controls configuration and spend
(see also the OWNER-gated /settings router).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_owner
from app.models import User
from app.services import ai_usage_service

router = APIRouter(prefix="/ai-usage", tags=["ai-usage"])


@router.get("")
async def get_ai_usage(
    current_user: User = Depends(get_current_owner),
    db: AsyncSession = Depends(get_db),
):
    """Return this tenant's month-to-date AI usage and remaining allowance."""
    return await ai_usage_service.get_usage_summary(db, current_user.tenant_id)
