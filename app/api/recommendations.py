"""Recommendations API Router

Exposes AI-generated recommendations for user feedback and tracking.
Allows users to accept/reject recommendations and view their impact.
All endpoints are scoped to the authenticated user's tenant.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.api.deps import get_current_user
from app.models import User, Recommendation, RecommendationStatus

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class RecommendationCreate(BaseModel):
    """Schema for creating a new recommendation."""
    category: str
    content: str
    impact_score: float


class RecommendationUpdate(BaseModel):
    """Schema for updating recommendation status."""
    status: str
    applied_date: Optional[datetime] = None


class RecommendationResponse(BaseModel):
    """Schema for returning recommendation data."""
    id: int
    category: str
    content: str
    impact_score: float
    status: str
    applied_date: Optional[datetime]
    verified_impact: Optional[float]
    verification_summary: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
async def create_recommendation(
    rec: RecommendationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new AI-generated recommendation.
    
    This endpoint is typically called by the AI agent to save recommendations.
    
    Args:
        rec: Recommendation data (category, content, impact_score)
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        Created recommendation with all fields
        
    Raises:
        HTTPException 400: If validation fails
        HTTPException 401: If user is not authenticated
        HTTPException 500: If database error occurs
    """
    try:
        # Validate status is one of the allowed values
        if rec.status not in [RecommendationStatus.PENDING.value]:
            raise ValueError(f"status must be {RecommendationStatus.PENDING.value}")
        
        # Create new recommendation
        new_rec = Recommendation(
            tenant_id=current_user.tenant_id,
            category=rec.category,
            content=rec.content,
            impact_score=rec.impact_score,
            status=RecommendationStatus.PENDING.value
        )
        
        db.add(new_rec)
        await db.commit()
        await db.refresh(new_rec)
        
        return RecommendationResponse.model_validate(new_rec)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create recommendation: {str(e)}"
        )


@router.get("", response_model=List[RecommendationResponse])
async def list_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    limit: int = 50
):
    """List all recommendations for the authenticated user's tenant.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        status_filter: Filter by status (Pending, Accepted, Rejected)
        category_filter: Filter by category
        limit: Maximum number of results (default 50, max 100)
        
    Returns:
        List of recommendations matching filters
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 500: If database error occurs
    """
    try:
        # Cap limit
        limit = min(limit, 100)
        
        # Build query
        query = select(Recommendation).where(
            Recommendation.tenant_id == current_user.tenant_id
        )
        
        # Apply filters
        if status_filter:
            query = query.where(Recommendation.status == status_filter)
        
        if category_filter:
            query = query.where(Recommendation.category == category_filter)
        
        # Order by created_at descending (newest first)
        from sqlalchemy import desc
        query = query.order_by(desc(Recommendation.created_at)).limit(limit)
        
        result = await db.execute(query)
        recommendations = result.scalars().all()
        
        return [RecommendationResponse.model_validate(rec) for rec in recommendations]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommendations: {str(e)}"
        )


@router.get("/{rec_id}", response_model=RecommendationResponse)
async def get_recommendation(
    rec_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific recommendation by ID.
    
    Security: User can only view recommendations from their tenant.
    
    Args:
        rec_id: Recommendation ID
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        Recommendation with all fields
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If recommendation belongs to different tenant
        HTTPException 404: If recommendation not found
        HTTPException 500: If database error occurs
    """
    try:
        query = select(Recommendation).where(
            and_(
                Recommendation.id == rec_id,
                Recommendation.tenant_id == current_user.tenant_id
            )
        )
        
        result = await db.execute(query)
        recommendation = result.scalars().first()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {rec_id} not found or does not belong to your tenant"
            )
        
        return RecommendationResponse.model_validate(recommendation)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recommendation: {str(e)}"
        )


@router.patch("/{rec_id}", response_model=RecommendationResponse)
async def update_recommendation(
    rec_id: int,
    update: RecommendationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update recommendation status (Accept or Reject).
    
    This endpoint allows users to provide feedback on AI recommendations.
    When set to "Accepted", applies the applied_date timestamp.
    
    Security: User can only update recommendations from their tenant.
    
    Args:
        rec_id: Recommendation ID
        update: Update data with new status (Accepted or Rejected)
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        Updated recommendation with new status
        
    Raises:
        HTTPException 400: If status is invalid
        HTTPException 401: If user is not authenticated
        HTTPException 403: If recommendation belongs to different tenant
        HTTPException 404: If recommendation not found
        HTTPException 409: If trying to change status of already accepted/rejected recommendation
        HTTPException 500: If database error occurs
    """
    try:
        # Validate status
        valid_statuses = [
            RecommendationStatus.PENDING.value,
            RecommendationStatus.ACCEPTED.value,
            RecommendationStatus.REJECTED.value
        ]
        if update.status not in valid_statuses:
            raise ValueError(f"status must be one of: {', '.join(valid_statuses)}")
        
        # Fetch recommendation
        query = select(Recommendation).where(
            and_(
                Recommendation.id == rec_id,
                Recommendation.tenant_id == current_user.tenant_id
            )
        )
        
        result = await db.execute(query)
        recommendation = result.scalars().first()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {rec_id} not found or does not belong to your tenant"
            )
        
        # Check if trying to change an already decided recommendation
        if recommendation.status in [RecommendationStatus.ACCEPTED.value, RecommendationStatus.REJECTED.value]:
            if update.status != recommendation.status:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot change status from {recommendation.status} to {update.status}. "
                            f"Once a recommendation is accepted or rejected, it cannot be changed."
                )
        
        # Update status
        recommendation.status = update.status
        
        # Set applied_date if accepting
        if update.status == RecommendationStatus.ACCEPTED.value:
            recommendation.applied_date = update.applied_date or datetime.now(timezone.utc)
        
        # Ensure updated_at is set
        recommendation.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(recommendation)
        
        return RecommendationResponse.model_validate(recommendation)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update recommendation: {str(e)}"
        )


@router.delete("/{rec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recommendation(
    rec_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a recommendation (only if in Pending status).
    
    Security: User can only delete recommendations from their tenant.
    
    Args:
        rec_id: Recommendation ID
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If recommendation belongs to different tenant
        HTTPException 404: If recommendation not found
        HTTPException 409: If recommendation is not in Pending status
        HTTPException 500: If database error occurs
    """
    try:
        query = select(Recommendation).where(
            and_(
                Recommendation.id == rec_id,
                Recommendation.tenant_id == current_user.tenant_id
            )
        )
        
        result = await db.execute(query)
        recommendation = result.scalars().first()
        
        if not recommendation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommendation {rec_id} not found or does not belong to your tenant"
            )
        
        # Only allow deleting Pending recommendations
        if recommendation.status != RecommendationStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Can only delete recommendations in {RecommendationStatus.PENDING.value} status. "
                        f"This recommendation is {recommendation.status}."
            )
        
        await db.delete(recommendation)
        await db.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete recommendation: {str(e)}"
        )
