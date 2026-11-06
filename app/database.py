"""Database Connection and Session Factory

Manages SQLAlchemy async engine and session creation.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import inspect, text
from app.core.config import settings

# Database URL will be configured via environment variables
# Example: postgresql+asyncpg://user:password@localhost/opsmind_ai

engine = None
AsyncSessionLocal = None


async def migrate_auth_schema(connection) -> None:
    """Add token_version to existing SQLite/Postgres user tables, preserving rows.

    Startup already serializes DDL on PostgreSQL with its advisory lock. This
    narrow additive migration is idempotent; formal migrations follow in Step 4.
    """
    def needs_column(sync_connection):
        schema = inspect(sync_connection)
        return schema.has_table("users") and "token_version" not in {
            column["name"] for column in schema.get_columns("users")
        }

    if await connection.run_sync(needs_column):
        await connection.execute(text(
            "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"
        ))


async def init_db(database_url: str) -> None:
    """Initialize the database engine and session factory.
    
    Args:
        database_url: The async database URL (e.g., postgresql+asyncpg://...)
    """
    global engine, AsyncSessionLocal
    
    engine_options = {"echo": False, "future": True, "pool_pre_ping": True}
    if "sqlite" in database_url:
        engine_options.update(
            poolclass=StaticPool,
            connect_args={"timeout": 30},
        )
    else:
        engine_options.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=1800,
        )
    engine = create_async_engine(database_url, **engine_options)
    
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to inject database session.
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    
    async with AsyncSessionLocal() as session:
        yield session


async def close_db() -> None:
    """Close the database connection pool."""
    if engine is not None:
        await engine.dispose()
