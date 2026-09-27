"""Tests for the AI response cache (Phase 2 upsert + robust lookup).

Covers the module-level cache helpers in ``app.services.ai_agent``:
- a fresh response is stored and served back (with hit_count incremented),
- re-saving the same (tenant_id, request_hash) upserts in place rather than
  creating a duplicate row,
- expired entries are treated as a miss,
- the cache is isolated per tenant.

These call the real functions and touch a real (in-memory) DB, so they exercise
the actual persistence path with no Gemini/network dependency.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.models import AICache
from app.services.ai_agent import get_cached_response, save_to_cache


async def test_save_then_get_roundtrip(db_session):
    ok = await save_to_cache(
        db_session, tenant_id=1, request_hash="h1", response={"insight": "sell more chai"}
    )
    assert ok is True

    cached = await get_cached_response(db_session, tenant_id=1, request_hash="h1")
    assert cached == {"insight": "sell more chai"}


async def test_get_increments_hit_count(db_session):
    await save_to_cache(db_session, tenant_id=1, request_hash="h1", response={"v": 1})

    await get_cached_response(db_session, tenant_id=1, request_hash="h1")
    await get_cached_response(db_session, tenant_id=1, request_hash="h1")

    row = (
        await db_session.execute(
            select(AICache).where(
                AICache.tenant_id == 1, AICache.request_hash == "h1"
            )
        )
    ).scalars().one()
    assert row.hit_count == 2


async def test_resave_upserts_in_place(db_session):
    await save_to_cache(db_session, tenant_id=1, request_hash="h1", response={"v": 1})
    await save_to_cache(db_session, tenant_id=1, request_hash="h1", response={"v": 2})

    rows = (
        await db_session.execute(
            select(AICache).where(
                AICache.tenant_id == 1, AICache.request_hash == "h1"
            )
        )
    ).scalars().all()

    # Exactly one row survives, holding the latest response with a reset hit count.
    assert len(rows) == 1
    assert rows[0].response_json == {"v": 2}
    assert rows[0].hit_count == 0


async def test_expired_entry_is_a_miss(db_session):
    await save_to_cache(db_session, tenant_id=1, request_hash="h1", response={"v": 1})

    row = (
        await db_session.execute(
            select(AICache).where(
                AICache.tenant_id == 1, AICache.request_hash == "h1"
            )
        )
    ).scalars().one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    await db_session.commit()

    assert await get_cached_response(db_session, tenant_id=1, request_hash="h1") is None


async def test_cache_is_tenant_isolated(db_session):
    await save_to_cache(db_session, tenant_id=1, request_hash="h1", response={"v": 1})

    # A different tenant with the same request hash must not read tenant 1's row.
    assert await get_cached_response(db_session, tenant_id=2, request_hash="h1") is None
