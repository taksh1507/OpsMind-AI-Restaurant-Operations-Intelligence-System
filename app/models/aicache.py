"""AI Cache Model - Store AI responses to reduce API quota usage

Day 16: Caching & Optimization Layer
- Stores Gemini API responses indexed by request_hash
- Implements TTL-based cache expiration
- Reduces redundant API calls and saves quota
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import String, JSON, DateTime, Integer, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import BaseModel


class AICache(BaseModel):
    """Cache for AI-generated responses to reduce API quota usage.
    
    Strategy:
    1. Hash incoming request data to create a unique key
    2. Check if cache entry exists for this request_hash
    3. If found and not expired, serve cached response
    4. If not found or expired, call Gemini, cache result, serve response
    
    TTL: 1 hour (3600 seconds) by default, configurable per request type
    """
    
    __tablename__ = "ai_cache"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Tenant isolation - cache is per-restaurant
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Hash of the request (input data) - acts as cache key
    # Format: SHA256 hash of JSON-serialized request parameters
    # Ensures identical requests hit the same cache entry
    request_hash: Mapped[str] = mapped_column(
        String(64),  # SHA256 hash length
        nullable=False,
        index=True
    )
    
    # The actual AI response cached as JSON
    # Contains the complete Gemini API response parsed as JSON
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Cache expiration timestamp
    # When expires_at < now(), the cache is considered stale and will be refreshed
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    # Request type for analytics and management
    # Examples: "briefing", "forecast", "recommendation", "weather_aware"
    request_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="briefing"
    )
    
    # Optional: Store the request data for debugging/audit
    # Useful for investigating why certain caches behave unexpectedly
    request_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Hit count - how many times this cache was accessed
    # For analytics: shows cache effectiveness
    hit_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    
    # Indexed for fast lookup
    __table_args__ = (
        Index('idx_tenant_request_hash', 'tenant_id', 'request_hash'),
        Index('idx_expires_at', 'expires_at'),
    )
    
    @staticmethod
    def is_expired() -> datetime:
        """Calculate expiration time (1 hour from now in UTC)."""
        return datetime.now(timezone.utc) + timedelta(hours=1)
    
    @staticmethod
    def is_valid(cache_entry: 'AICache') -> bool:
        """Check if cache entry is still valid (not expired)."""
        if cache_entry is None:
            return False
        return cache_entry.expires_at > datetime.now(timezone.utc)


__all__ = ["AICache"]
