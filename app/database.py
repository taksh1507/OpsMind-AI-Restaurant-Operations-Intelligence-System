"""Database Connection and Session Factory

Manages SQLAlchemy async engine and session creation.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Database URL will be configured via environment variables
# Example: postgresql+asyncpg://user:password@localhost/opsmind_ai

engine = None
AsyncSessionLocal = None


async def init_db(database_url: str) -> None:
    """Initialize the database engine and session factory.
    
    Args:
        database_url: The async database URL (e.g., postgresql+asyncpg://...)
    """
    global engine, AsyncSessionLocal
    
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        future=True,
        pool_pre_ping=True,
        poolclass=NullPool,  # Good for serverless/lightweight setups
    )
    
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
