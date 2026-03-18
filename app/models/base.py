"""Base SQLAlchemy Model and Registry Setup

Provides the declarative base for all ORM models with async support.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

# Declarative base for all models
Base = declarative_base()


class BaseModel(Base):
    """Abstract base model with common fields for all tables."""
    
    __abstract__ = True
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=datetime.utcnow,
        nullable=False
    )
