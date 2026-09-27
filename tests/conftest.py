"""Shared pytest fixtures for the OpsMind test suite.

Provides a fresh in-memory SQLite database (one per test) so security- and
persistence-focused unit tests can run without a real Postgres instance and
without leaking state between tests.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool

from app.models.base import Base

# Importing the models package registers every table on Base.metadata, so
# create_all below builds the full schema (users, tenants, ai_cache, ...).
import app.models  # noqa: F401


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Yield an AsyncSession bound to a throwaway in-memory SQLite database.

    StaticPool keeps a single underlying connection alive for the lifetime of
    the engine, which is what makes ``:memory:`` usable across statements.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()
