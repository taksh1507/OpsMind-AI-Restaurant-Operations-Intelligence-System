"""Review Model - Customer Feedback and Sentiment Analysis

Represents customer reviews with AI-generated sentiment scores and insights.
Supports reviews from multiple sources: Google, Yelp, or in-house feedback forms.
"""

from typing import Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, ForeignKey, Numeric, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Review(BaseModel):
    """
    A customer review with AI-analyzed sentiment and action items.
    
    Attributes:
        id: Unique auto-incremented identifier
        tenant_id: Foreign key to parent tenant (restaurant) - CRITICAL FOR ISOLATION
        customer_name: Name of the customer who left the review
        rating: Numerical rating (1-5 stars)
        comment: Full text of the customer's feedback
        sentiment_score: AI-computed sentiment (-1.0 = very negative, 0.0 = neutral, 1.0 = very positive)
        ai_summary: One-sentence AI summary of the review's main point
        source: Where the review came from (google, yelp, internal, etc.)
        keywords: Comma-separated keywords extracted by AI (e.g., "cold food,great service")
        action_item: Specific actionable recommendation for the manager
        is_processed: Whether the review has been analyzed by AI
        processed_at: When the review was analyzed
        created_at: When the review was submitted/created
        updated_at: When the review record was last updated
    """
    
    __tablename__ = "reviews"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True  # Index for fast filtering by tenant
    )
    
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    rating: Mapped[int] = mapped_column(nullable=False)  # 1-5
    
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    
    sentiment_score: Mapped[Decimal] = mapped_column(
        Numeric(precision=3, scale=2),
        nullable=True,  # Null until processed
        default=None
    )
    
    ai_summary: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default=None
    )
    
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="internal"  # google, yelp, internal, etc.
    )
    
    keywords: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default=None
    )
    
    action_item: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default=None
    )
    
    is_processed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )
    
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    
    def __repr__(self) -> str:
        return f"<Review(id={self.id}, tenant_id={self.tenant_id}, rating={self.rating}, sentiment={self.sentiment_score})>"
    
    @property
    def sentiment_label(self) -> str:
        """Get human-readable sentiment label."""
        if self.sentiment_score is None:
            return "unprocessed"
        score = float(self.sentiment_score)
        if score >= 0.5:
            return "positive"
        elif score <= -0.5:
            return "negative"
        else:
            return "neutral"
    
    @property
    def is_positive(self) -> bool:
        """Check if sentiment is positive."""
        return self.sentiment_score is not None and float(self.sentiment_score) >= 0.5
    
    @property
    def is_negative(self) -> bool:
        """Check if sentiment is negative."""
        return self.sentiment_score is not None and float(self.sentiment_score) <= -0.5
    
    @property
    def is_neutral(self) -> bool:
        """Check if sentiment is neutral."""
        return self.sentiment_score is not None and -0.5 < float(self.sentiment_score) < 0.5
