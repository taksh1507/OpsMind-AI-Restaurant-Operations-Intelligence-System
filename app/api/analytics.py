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
    get_top_selling_items,
    get_daily_sales_trend
)
from app.services.ai_agent import forecast_revenue, analyze_profit_margins
from app.services.margin_analysis import (
    get_all_menu_items_with_costs,
    get_margin_report_summary
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


@router.get("/forecast")
async def get_revenue_forecast(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 14
):
    """Get AI-powered revenue forecast for the next 3 days.
    
    Uses historical trends from the past N days to predict future revenue.
    The AI forecaster analyzes patterns (weekday vs weekend, growth trends, etc.)
    and provides a confidence score for the predictions.
    
    This endpoint gives restaurant owners a "Crystal Ball" view of their 
    expected revenue, enabling better resource planning and marketing timing.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        days: Number of historical days to analyze (default 14)
        
    Returns:
        Forecast with predictions for next 3 days:
        - next_day_1_revenue: Predicted revenue for tomorrow
        - next_day_2_revenue: Predicted revenue for day after tomorrow
        - next_day_3_revenue: Predicted revenue for 3 days from now
        - confidence_score: 0-100 confidence level
        - growth_rate_percent: Daily trend as percentage
        - business_impact: Actionable insight for owner
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If no historical data found
        HTTPException 500: If forecast generation fails
    """
    
    try:
        # Get historical trend data
        trend_data = await get_daily_sales_trend(
            db,
            current_user.tenant_id,
            days=days
        )
        
        if not trend_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No sales data found for the past {days} days. A forecast requires at least 3 days of historical data."
            )
        
        if len(trend_data) < 3:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Insufficient historical data for accurate forecasting. Need at least 3 days of sales data."
            )
        
        # Generate forecast using AI
        forecast_result = await forecast_revenue(trend_data)
        
        if forecast_result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=forecast_result.get("message", "Failed to generate forecast")
            )
        
        # Format the response
        forecast = forecast_result.get("forecast", {})
        
        return {
            "status": "success",
            "tenant_id": current_user.tenant_id,
            "forecast_period": {
                "historical_days": days,
                "data_points": len(trend_data),
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "predictions": {
                "next_day_1_revenue": forecast.get("next_day_1_revenue", 0),
                "next_day_2_revenue": forecast.get("next_day_2_revenue", 0),
                "next_day_3_revenue": forecast.get("next_day_3_revenue", 0)
            },
            "confidence": {
                "score": forecast.get("confidence_score", 0),
                "reasoning": forecast.get("confidence_reasoning", ""),
                "growth_rate_percent": forecast.get("growth_rate_percent", 0),
                "growth_direction": forecast.get("growth_direction", "Stable")
            },
            "pattern": {
                "detected": forecast.get("pattern_detected", "No pattern detected"),
                "risk_factors": forecast.get("risk_factors", [])
            },
            "business_impact": forecast.get("business_impact", ""),
            "message": "Revenue forecast based on AI analysis of historical trends",
            "recommendation": "Use this forecast to plan staffing, inventory, and marketing campaigns"
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
            detail=f"Failed to generate revenue forecast: {str(e)}"
        )


@router.get("/margin-report")
async def get_margin_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI-powered margin optimization and waste report.
    
    Analyzes all menu items' profitability based on ingredient costs.
    Identifies items priced below healthy margins (< 3x cost) and provides
    specific recommendations for price adjustments or cost reductions.
    
    This endpoint calculates:
    - Cost of Goods Sold (COGS) for each menu item based on recipes
    - Profit margins with ingredient accuracy
    - Price-to-cost ratios (healthy = >3x)
    - Items in danger zones (losing money after overhead)
    - AI-generated optimization plan with specific actions
    
    The AI recommends:
    - Which items to price increase (with exact new prices)
    - Which ingredients to substitute or source differently
    - Product discontinuation if necessary
    - Estimated profit improvement from each action
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        Comprehensive margin report with risk analysis and AI optimization plan
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If no menu items exist
        HTTPException 500: If analysis fails
    """
    
    try:
        # Get all menu items with calculated COGS
        menu_items = await get_all_menu_items_with_costs(db, current_user.tenant_id)
        
        if not menu_items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No menu items found for this restaurant. Add menu items and recipes first."
            )
        
        # Get summary metrics
        summary = await get_margin_report_summary(db, current_user.tenant_id)
        
        # Use AI to generate optimization plan
        ai_result = await analyze_profit_margins(menu_items)
        
        if ai_result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ai_result.get("message", "Failed to generate margin analysis")
            )
        
        margin_analysis = ai_result.get("analysis", {})
        
        # Format the response
        return {
            "status": "success",
            "tenant_id": current_user.tenant_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_menu_items": summary["total_items"],
                "items_with_healthy_margins": summary["items_healthy"],
                "items_in_danger_zone": summary["items_at_risk"],
                "average_margin_percent": summary["average_margin_percent"],
                "total_revenue_from_risky_items": summary["total_revenue_at_risk"],
                "potential_monthly_improvement": summary["potential_improvement"]
            },
            "menu_items": menu_items,
            "margin_analysis": margin_analysis,
            "ai_reasoning": ai_result.get("reasoning", ""),
            "recommendations": {
                "immediate_actions": margin_analysis.get("optimization_plan", {}).get("top_3_actions", []),
                "executive_summary": margin_analysis.get("optimization_plan", {}).get("executive_summary", ""),
                "cost_strategies": margin_analysis.get("cost_strategies", [])
            },
            "message": "AI-powered margin analysis and waste optimization report",
            "action_items": [
                f"Review {summary['items_at_risk']} menu items with margin concerns",
                f"Potential to improve margins by ${summary['potential_improvement']}/month",
                "Implement suggested price changes and ingredient cost reductions"
            ]
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
            detail=f"Failed to generate margin report: {str(e)}"
        )
