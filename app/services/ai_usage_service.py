"""AI Usage Service - metering, monthly cap enforcement, and reporting.

Phase 4: AI usage metering + guardrails.

This module ties together three things:

1. **Capture** — token counts collected at the Anthropic adapter chokepoint via
   ``app.services.ai_agent.capture_usage`` (a context-local sink).
2. **Record** — one ``AIUsage`` row per billable call, scoped to a tenant.
3. **Enforce** — a per-tenant monthly token cap (``settings.ai_monthly_token_cap``)
   that returns HTTP 429 once a restaurant has spent its allowance for the month.

``metered_ai_call`` is the single wrapper the API layer uses around any AI call:
it enforces the quota first, captures usage during the call, and records it after.
Recording is best-effort — a metering failure never breaks the underlying feature.
"""

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_usage import AIUsage
from app.services.ai_agent import AIUsageEvent, capture_usage

logger = logging.getLogger("opsmind.ai_usage")


def _month_start(now: Optional[datetime] = None) -> datetime:
    """Start of the current UTC month (inclusive lower bound for month-to-date)."""
    now = now or datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def _cap() -> int:
    """The configured monthly cap; <= 0 means enforcement is disabled."""
    try:
        return int(settings.ai_monthly_token_cap)
    except (TypeError, ValueError):
        return 0


async def get_month_to_date_tokens(session: AsyncSession, tenant_id: int) -> int:
    """Total input+output tokens this tenant has used since the month began."""
    stmt = select(func.coalesce(func.sum(AIUsage.total_tokens), 0)).where(
        AIUsage.tenant_id == tenant_id,
        AIUsage.created_at >= _month_start(),
    )
    result = await session.execute(stmt)
    return int(result.scalar() or 0)


async def enforce_quota(session: AsyncSession, tenant_id: int) -> None:
    """Raise HTTP 429 if the tenant has reached its monthly AI token cap.

    No-op when the cap is disabled (<= 0). Called before an AI request runs so no
    tokens are spent once the limit is hit.
    """
    cap = _cap()
    if cap <= 0:
        return
    used = await get_month_to_date_tokens(session, tenant_id)
    if used >= cap:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly AI usage limit reached ({used:,} of {cap:,} tokens). "
                "AI features resume at the start of next month. If you need more, "
                "an administrator can raise AI_MONTHLY_TOKEN_CAP."
            ),
        )


async def record_events(
    session: AsyncSession,
    tenant_id: int,
    feature: str,
    events: List[AIUsageEvent],
) -> None:
    """Persist captured usage events as AIUsage rows. Best-effort; never raises."""
    if not events:
        return
    try:
        for ev in events:
            session.add(
                AIUsage(
                    tenant_id=tenant_id,
                    feature=(feature or "unknown")[:50],
                    model=(ev.model or "unknown")[:100],
                    input_tokens=ev.input_tokens,
                    output_tokens=ev.output_tokens,
                    total_tokens=ev.total_tokens,
                )
            )
        await session.commit()
    except Exception:
        # Metering must never break the feature it is measuring.
        logger.warning("Failed to record AI usage for tenant %s", tenant_id, exc_info=True)
        try:
            await session.rollback()
        except Exception:
            logger.debug("Rollback after usage-record failure also failed", exc_info=True)


async def metered_ai_call(
    session: AsyncSession,
    tenant_id: int,
    feature: str,
    factory: Callable[[], Awaitable],
    *,
    enforce: bool = True,
):
    """Run an AI call with quota enforcement and usage metering.

    Args:
        session: DB session used to read usage and record new rows.
        tenant_id: Restaurant the usage belongs to.
        feature: Short label for the feature spending tokens (stored per row).
        factory: Zero-arg callable returning the coroutine to await. Passing a
            factory (not an already-created coroutine) guarantees nothing runs
            until AFTER the quota check passes.
        enforce: When False, skip the cap check but still record usage. Use for a
            secondary call inside a request whose primary call already enforced.

    Returns:
        Whatever the awaited coroutine returns.

    Raises:
        HTTPException: 429 when the monthly cap is already reached (enforce=True).
    """
    if enforce:
        await enforce_quota(session, tenant_id)

    with capture_usage() as sink:
        try:
            return await factory()
        finally:
            # Record even if the call raised downstream: any tokens the API
            # already billed us for are in the sink and should be metered.
            await record_events(session, tenant_id, feature, list(sink))


async def get_usage_summary(session: AsyncSession, tenant_id: int) -> dict:
    """Build the Owner-facing month-to-date usage summary for a tenant."""
    cap = _cap()
    enforced = cap > 0
    period_start = _month_start()

    totals_stmt = select(
        func.coalesce(func.sum(AIUsage.input_tokens), 0),
        func.coalesce(func.sum(AIUsage.output_tokens), 0),
        func.coalesce(func.sum(AIUsage.total_tokens), 0),
        func.count(AIUsage.id),
    ).where(
        AIUsage.tenant_id == tenant_id,
        AIUsage.created_at >= period_start,
    )
    input_tokens, output_tokens, total_tokens, total_calls = (
        await session.execute(totals_stmt)
    ).one()
    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)
    total_tokens = int(total_tokens or 0)
    total_calls = int(total_calls or 0)

    breakdown_stmt = (
        select(
            AIUsage.feature,
            func.coalesce(func.sum(AIUsage.total_tokens), 0),
            func.count(AIUsage.id),
        )
        .where(
            AIUsage.tenant_id == tenant_id,
            AIUsage.created_at >= period_start,
        )
        .group_by(AIUsage.feature)
        .order_by(func.sum(AIUsage.total_tokens).desc())
    )
    by_feature = [
        {"feature": feature, "total_tokens": int(tokens or 0), "calls": int(calls or 0)}
        for feature, tokens, calls in (await session.execute(breakdown_stmt)).all()
    ]

    remaining = max(cap - total_tokens, 0) if enforced else None
    percent_used = round(total_tokens / cap * 100, 1) if enforced else None

    return {
        "tenant_id": tenant_id,
        "period_start": period_start.isoformat(),
        "period_label": period_start.strftime("%B %Y"),
        "enforced": enforced,
        "monthly_token_cap": cap if enforced else None,
        "tokens_used": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tokens_remaining": remaining,
        "percent_used": percent_used,
        "total_calls": total_calls,
        "by_feature": by_feature,
    }
