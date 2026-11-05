"""Shared pytest fixtures for the OpsMind test suite.

Provides a fresh SQLite database per test by default, or an isolated PostgreSQL
schema when TEST_DATABASE_URL is set. No test shares persisted database state.
"""

from pathlib import Path
import shutil
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text

from app.models.base import Base

# Importing the models package registers every table on Base.metadata, so
# create_all below builds the full schema (users, tenants, ai_cache, ...).
import app.models  # noqa: F401


@pytest.fixture(autouse=True)
def isolated_artifacts(tmp_path, monkeypatch):
    """Keep relative model, report and dataset writes outside the checkout.

    Copy input datasets only; never copy tenant models or reports. This also
    protects legacy code that has not yet gained configurable artifact paths.
    """
    root = Path(__file__).resolve().parents[1]
    for relative in ("data", "tests/data"):
        source = root / relative
        if source.exists():
            shutil.copytree(source, tmp_path / relative)
    (tmp_path / "models").mkdir()
    (tmp_path / "reports").mkdir()
    monkeypatch.chdir(tmp_path)

    # A developer's .env must never turn offline tests into paid AI requests.
    from app.core.config import settings

    for name in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(settings, "anthropic_auth_token", None)
    monkeypatch.setattr(settings, "anthropic_api_key", None)

    # No test can inherit another test's lockout or use a developer Redis URL.
    from app.core import rate_limit

    monkeypatch.setattr(settings, "redis_url", None)
    monkeypatch.setattr(settings, "trusted_proxies", [])
    monkeypatch.setattr(rate_limit, "_memory_store", rate_limit.MemoryStore())


@pytest.fixture
def anyio_backend() -> str:
    """Pin every ``@pytest.mark.anyio`` test to the asyncio backend.

    OpsMind runs exclusively on asyncio (FastAPI/uvicorn, asyncpg, and the
    apscheduler AsyncIOScheduler), so there is no Trio code path to exercise.
    Without this override anyio also parametrizes the suite under Trio, where
    the AsyncIOScheduler cannot bind to the loop and the scheduler test fails
    with "Event loop is closed". Forcing asyncio tests only what we ship.
    """
    return "asyncio"


@pytest_asyncio.fixture
async def test_database_engine(tmp_path):
    """Opt into PostgreSQL with a fresh, randomly named schema per test."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite'}")
        try:
            yield engine
        finally:
            await engine.dispose()
        return
    if not url.startswith("postgresql+asyncpg://"):
        raise ValueError("TEST_DATABASE_URL must use postgresql+asyncpg")
    schema = "opsmind_test_" + uuid.uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


@pytest_asyncio.fixture
async def db_session(test_database_engine) -> AsyncSession:
    """Yield a session bound to a throwaway SQLite database or PostgreSQL schema."""
    engine = test_database_engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()
