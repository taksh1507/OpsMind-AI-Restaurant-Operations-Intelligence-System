"""Base SQLAlchemy Model and Registry Setup

Provides the declarative base for all ORM models with async support.
"""

from app.core.time_utils import utc_now

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

# Declarative base for all models
Base = declarative_base()


class BaseModel(Base):
    """Abstract base model with common fields for all tables."""
    
    __abstract__ = True
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=utc_now,
        nullable=False
    )
