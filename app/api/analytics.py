"""Analytics API Router

Exposes restaurant performance insights via secure endpoints.
All endpoints are scoped to the authenticated user's tenant.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal

from app.database import get_db
from app.api.deps import get_current_user
from app.models import User
from app.services.analytics import (
    calculate_revenue_and_profit,
    calculate_profit_margin,
    get_top_selling_items
)


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_restaurant_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get restaurant performance summary.
    
    Returns a comprehensive overview of the restaurant's performance including:
    - Total revenue and profit for the period
    - Profit margin percentage
    - Top 5 best-selling menu items
    
    The data is strictly scoped to the authenticated user's restaurant.
    This is the bridge between raw database rows and high-level insights.
    
    Args:
        current_user: Authenticated user with tenant context (injected)
        db: Database session (injected)
        start_date: Start date for analysis (YYYY-MM-DD format). Optional.
        end_date: End date for analysis (YYYY-MM-DD format). Optional.
        
    Returns:
        JSON summary with revenue, profit, margin, and top items
        
    Raises:
        HTTPException 400: If date format is invalid
        HTTPException 401: If user is not authenticated
        HTTPException 500: If analytics calculation fails
    """
    
    try:
        # Parse dates if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc,
                    hour=23,
                    minute=59,
                    second=59
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        
        # Calculate revenue and profit
        metrics = await calculate_revenue_and_profit(
            db,
            current_user.tenant_id,
            parsed_start_date,
            parsed_end_date
        )
        
        # Calculate profit margin
        margin = await calculate_profit_margin(
            db,
            current_user.tenant_id,
            parsed_start_date,
            parsed_end_date
        )
        
        # Get top 5 selling items
        top_items = await get_top_selling_items(
            db,
            current_user.tenant_id,
            limit=5,
            start_date=parsed_start_date,
            end_date=parsed_end_date
        )
        
        # Format response
        return {
            "status": "success",
            "tenant_id": current_user.tenant_id,
            "period": {
                "start_date": metrics["start_date"].isoformat(),
                "end_date": metrics["end_date"].isoformat()
            },
            "metrics": {
                "total_revenue": float(metrics["revenue"]),
                "total_profit": float(metrics["profit"]),
                "profit_margin_percent": float(margin),
                "cost_of_goods_sold": float(metrics["cost_of_goods"]),
                "transaction_count": metrics["transaction_count"],
                "total_items_sold": metrics["item_count"]
            },
            "top_selling_items": [
                {
                    "menu_item_id": item["menu_item_id"],
                    "name": item["name"],
                    "quantity_sold": item["quantity_sold"],
                    "revenue_generated": float(item["revenue"])
                }
                for item in top_items
            ],
            "message": "Restaurant performance summary for the selected period"
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate analytics summary. Please try again."
        )


@router.get("/metrics/revenue")
async def get_revenue_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get detailed revenue metrics.
    
    Returns comprehensive revenue and profit analysis for the restaurant.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        
    Returns:
        Detailed revenue breakdown
    """
    
    try:
        # Parse dates
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        
        if end_date:
            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc,
                hour=23,
                minute=59,
                second=59
            )
        
        # Get metrics
        metrics = await calculate_revenue_and_profit(
            db,
            current_user.tenant_id,
            parsed_start_date,
            parsed_end_date
        )
        
        margin = await calculate_profit_margin(
            db,
            current_user.tenant_id,
            parsed_start_date,
            parsed_end_date
        )
        
        return {
            "status": "success",
            "period": {
                "start_date": metrics["start_date"].isoformat(),
                "end_date": metrics["end_date"].isoformat()
            },
            "revenue": float(metrics["revenue"]),
            "cost_of_goods_sold": float(metrics["cost_of_goods"]),
            "profit": float(metrics["profit"]),
            "profit_margin_percent": float(margin),
            "transaction_count": metrics["transaction_count"],
            "total_items_sold": metrics["item_count"],
            "average_transaction_value": float(
                metrics["revenue"] / metrics["transaction_count"]
                if metrics["transaction_count"] > 0
                else 0
            )
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve revenue metrics"
        )


@router.get("/top-items")
async def get_top_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 5,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get top-selling menu items.
    
    Returns the best-performing dishes by quantity sold.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        limit: Maximum items to return (default 5, max 50)
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        
    Returns:
        List of top-selling items
    """
    
    try:
        # Validate limit
        limit = min(max(limit, 1), 50)  # Between 1 and 50
        
        # Parse dates
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        
        if end_date:
            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc,
                hour=23,
                minute=59,
                second=59
            )
        
        # Get top items
        items = await get_top_selling_items(
            db,
            current_user.tenant_id,
            limit=limit,
            start_date=parsed_start_date,
            end_date=parsed_end_date
        )
        
        return {
            "status": "success",
            "limit_requested": limit,
            "items_returned": len(items),
            "period": {
                "start_date": parsed_start_date.isoformat() if parsed_start_date else "from_beginning",
                "end_date": parsed_end_date.isoformat() if parsed_end_date else "to_now"
            },
            "top_items": [
                {
                    "menu_item_id": item["menu_item_id"],
                    "name": item["name"],
                    "quantity_sold": item["quantity_sold"],
                    "revenue_generated": float(item["revenue"])
                }
                for item in items
            ]
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top items"
        )


@router.get("/ai-briefing")
async def get_ai_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get AI-powered strategic briefing for the restaurant.
    
    This endpoint leverages Google Gemini to analyze restaurant performance
    and provide expert recommendations. It's the "consultant" that tells
    the owner exactly what to do to improve their business.
    
    The AI analyzes:
    - Total revenue and profit
    - Top-selling and underperforming items
    - Profit margins and cost structure
    - Market opportunities
    
    Returns strategic recommendations for:
    - Star dish identification
    - Pricing optimization
    - Inventory cost savings
    - Overall health assessment
    
    Args:
        current_user: Authenticated restaurant owner (injected)
        db: Database session (injected)
        start_date: Start date for analysis (YYYY-MM-DD format). Optional.
        end_date: End date for analysis (YYYY-MM-DD format). Optional.
        
    Returns:
        JSON response with AI-generated strategic advice
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 400: If date format is invalid
        HTTPException 503: If AI service is unavailable
    """
    try:
        # Import here to avoid circular imports and handle missing API key gracefully
        from app.services.ai_agent import generate_restaurant_strategy
        
        # Get the restaurant summary (same data as /summary endpoint)
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        
        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc,
                    hour=23,
                    minute=59,
                    second=59
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        
        # Calculate revenue and profit
        metrics = await calculate_revenue_and_profit(
            db,
            current_user.tenant_id,
            parsed_start_date,
            parsed_end_date
        )
        
        # Calculate profit margin
        margin = await calculate_profit_margin(
            db,
            current_user.tenant_id,
            parsed_start_date,
            parsed_end_date
        )
        
        # Get top 5 selling items
        top_items = await get_top_selling_items(
            db,
            current_user.tenant_id,
            limit=5,
            start_date=parsed_start_date,
            end_date=parsed_end_date
        )
        
        # Build performance data for AI analysis
        performance_data = {
            "tenant_id": current_user.tenant_id,
            "period": {
                "start_date": metrics["start_date"].isoformat(),
                "end_date": metrics["end_date"].isoformat()
            },
            "total_revenue": float(metrics["revenue"]),
            "total_profit": float(metrics["profit"]),
            "profit_margin_percent": float(margin),
            "cost_of_goods_sold": float(metrics["cost_of_goods"]),
            "transaction_count": metrics["transaction_count"],
            "total_items_sold": metrics["item_count"],
            "top_selling_items": [
                {
                    "menu_item_id": item["menu_item_id"],
                    "name": item["name"],
                    "quantity_sold": item["quantity_sold"],
                    "revenue_generated": float(item["revenue"])
                }
                for item in top_items
            ]
        }
        
        # Generate strategy using AI
        ai_result = await generate_restaurant_strategy(performance_data)
        
        if ai_result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ai_result.get("message", "AI service temporarily unavailable")
            )
        
        return {
            "status": "success",
            "tenant_id": current_user.tenant_id,
            "briefing": ai_result.get("strategy", {}),
            "data_period": performance_data.get("period", {}),
            "timestamp": ai_result.get("timestamp", ""),
            "message": "AI-powered strategic briefing. Click 'Ask OpsMind' for expert analysis."
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI briefing: {str(e)}"
        )
