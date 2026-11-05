"""AI Usage Service - metering, monthly cap enforcement, and reporting.

Phase 4: AI usage metering + guardrails.

This module ties together three things:

1. **Capture** — token counts collected at the Anthropic adapter chokepoint via
   ``app.services.ai_agent.capture_usage`` (a context-local sink).
2. **Record** — one ``AIUsage`` row per billable call, scoped to a tenant.
3. **Enforce** — atomically reserve a per-tenant monthly token budget before a
   provider call, then commit actual usage and release unused reservation.

``metered_ai_call`` is the single wrapper the API layer uses around any AI call:
it enforces the quota first, captures usage during the call, and records it after.
Recording is best-effort — a metering failure never breaks the underlying feature.
"""

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.config import settings
from app.models.ai_usage import AIUsage
from app.models.ai_usage_budget import AIUsageBudget
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


async def enforce_quota(session: AsyncSession, tenant_id: int) -> Optional[datetime]:
    """Atomically reserve a conservative token budget before a paid AI call."""
    cap = _cap()
    if cap <= 0:
        return None
    reservation = min(settings.ai_request_token_reservation, cap)
    period_start = _month_start()
    table = AIUsageBudget.__table__
    values = {
        "tenant_id": tenant_id,
        "period_start": period_start,
        "tokens_reserved": reservation,
        "tokens_committed": 0,
    }
    if session.bind.dialect.name == "postgresql":
        insert_statement = pg_insert(table).values(**values)
    elif session.bind.dialect.name == "sqlite":
        insert_statement = sqlite_insert(table).values(**values)
    else:
        raise RuntimeError("Atomic AI token reservations require PostgreSQL or SQLite.")
    statement = insert_statement.on_conflict_do_update(
        index_elements=[table.c.tenant_id, table.c.period_start],
        set_={"tokens_reserved": table.c.tokens_reserved + reservation},
        where=(
            table.c.tokens_committed + table.c.tokens_reserved + reservation <= cap
        ),
    ).returning(table.c.tenant_id)
    reservation_session = AsyncSession(bind=session.bind, expire_on_commit=False)
    try:
        result = await reservation_session.execute(statement)
        reserved = result.scalar_one_or_none() is not None
        if reserved:
            # Publish the reservation before starting the billable request.
            await reservation_session.commit()
        else:
            await reservation_session.rollback()
    finally:
        await reservation_session.close()
    if not reserved:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Monthly AI usage limit reached or the remaining allowance is "
                "reserved for an in-flight request. "
                "AI features resume at the start of next month. If you need more, "
                "an administrator can raise AI_MONTHLY_TOKEN_CAP."
            ),
        )
    return period_start


async def record_events(
    session: AsyncSession,
    tenant_id: int,
    feature: str,
    events: List[AIUsageEvent],
    reservation_tokens: int = 0,
    period_start: Optional[datetime] = None,
) -> None:
    """Commit actual usage and release the reservation in one transaction."""
    if not events and not reservation_tokens:
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
        if reservation_tokens:
            budget = AIUsageBudget.__table__
            await session.execute(
                update(budget)
                .where(
                    budget.c.tenant_id == tenant_id,
                    budget.c.period_start == (period_start or _month_start()),
                )
                .values(
                    tokens_reserved=case(
                        (budget.c.tokens_reserved >= reservation_tokens,
                         budget.c.tokens_reserved - reservation_tokens),
                        else_=0,
                    ),
                    tokens_committed=budget.c.tokens_committed
                    + sum(event.total_tokens for event in events),
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
        if reservation_tokens:
            try:
                budget = AIUsageBudget.__table__
                await session.execute(
                    update(budget)
                    .where(
                        budget.c.tenant_id == tenant_id,
                        budget.c.period_start == (period_start or _month_start()),
                    )
                    .values(tokens_reserved=case(
                        (budget.c.tokens_reserved >= reservation_tokens,
                         budget.c.tokens_reserved - reservation_tokens),
                        else_=0,
                    ))
                )
                await session.commit()
            except Exception:
                logger.error("Failed to release AI reservation for tenant %s", tenant_id, exc_info=True)
                await session.rollback()


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
        enforce: Kept for source compatibility. Every paid request reserves quota,
            including secondary calls, to prevent concurrent bypass.

    Returns:
        Whatever the awaited coroutine returns.

    Raises:
        HTTPException: 429 when the monthly cap is already reached (enforce=True).
    """
    cap = _cap()
    reservation = min(settings.ai_request_token_reservation, cap) if cap > 0 else 0
    # ``enforce=False`` was used for a second paid request in a compound feature;
    # it still needs a reservation so concurrent calls cannot bypass the cap.
    period_start = await enforce_quota(session, tenant_id)

    with capture_usage() as sink:
        try:
            return await factory()
        finally:
            # Record even if the call raised downstream: any tokens the API
            # already billed us for are in the sink and should be metered.
            await record_events(
                session, tenant_id, feature, list(sink),
                reservation_tokens=reservation, period_start=period_start,
            )


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
