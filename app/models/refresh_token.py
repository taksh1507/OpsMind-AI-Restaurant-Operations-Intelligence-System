"""Refresh Token Model for Secure Session Management

Stores issued refresh tokens so they can be rotated, revoked (logged-out), and
expired server-side. The raw token is stored only as a SHA-256 digest so a
database leak does not expose usable credentials.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class RefreshToken(BaseModel):
    """
    Server-side record for a refresh token.

    Attributes:
        id: Unique identifier
        user_id: Foreign key to the owning user
        token_hash: SHA-256 hex digest of the raw refresh token
        expires_at: When the token becomes invalid
        revoked: Whether the token has been explicitly revoked (logout)
        revoked_at: Timestamp of revocation, if any
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to user
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.revoked})>"
