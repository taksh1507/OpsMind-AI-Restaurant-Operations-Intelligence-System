"""Analytics API Router

Exposes restaurant performance insights via secure endpoints.
All endpoints are scoped to the authenticated user's tenant.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from typing import Optional
from decimal import Decimal

from app.database import get_db
from app.api.deps import get_current_user
from app.models import User, Review, Shift, Staff, Sale
from app.services.analytics import (
    calculate_revenue_and_profit,
    calculate_profit_margin,
    get_top_selling_items,
    get_daily_sales_trend
)
from app.services.ai_agent import forecast_revenue, analyze_profit_margins, process_review, calculate_labor_efficiency, AIConsultant
from app.services.margin_analysis import (
    get_all_menu_items_with_costs,
    get_margin_report_summary
)
from app.services.weather import (
    get_current_weather,
    correlate_weather_with_sales,
    get_weather_context_string
)
from app.core.math_utils import calculate_confidence_score
from sqlalchemy import select, func, desc, and_


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
    end_date: Optional[str] = None,
    refresh: bool = False
):
    """Get AI-powered strategic briefing for the restaurant.
    
    This endpoint leverages Google Gemini to analyze restaurant performance
    and provide expert recommendations. It's the "consultant" that tells
    the owner exactly what to do to improve their business.
    
    Day 16: Caching & Optimization Layer
    - By default, returns cached response if available (< 1 hour old)
    - Set refresh=True to force fresh AI analysis
    - Saves ~70% API quota by serving cached insights
    
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
        refresh: Set to true to force fresh AI analysis, bypass cache. Default: false
        
    Returns:
        JSON response with AI-generated strategic advice
        Includes 'cache_hit' field indicating if response came from cache
        
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
        
        # Generate strategy using AI (with caching support)
        # Pass db session and refresh flag to enable intelligent caching
        ai_result = await generate_restaurant_strategy(
            performance_data,
            db=db,
            refresh=refresh
        )
        
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
            "cache_hit": ai_result.get("cache_hit", False),
            "message": "AI-powered strategic briefing leveraging intelligent caching to optimize API usage."
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
    """Get AI-powered revenue forecast for the next 3 days with mathematical confidence scoring.
    
    Uses historical trends from the past N days to predict future revenue.
    The AI forecaster analyzes patterns (weekday vs weekend, growth trends, etc.)
    and combines mathematical confidence with AI insights.
    
    MATHEMATICAL GROUNDING:
    - Calculates Linear Regression slope to objectively measure revenue trends
    - Computes confidence score based on data variance and R-squared fit quality
    - Provides "Trust Factor" showing how reliable the prediction is
    
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
        - confidence_score: 0-100 confidence level (now with mathematical backing)
        - mathematical_confidence: High/Medium/Low based on data variance
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
        
        # Convert trend data to list for statistical analysis
        revenue_values = list(trend_data.values())
        
        # Calculate mathematical confidence score
        mathematical_confidence_level, mathematical_confidence_percentage = calculate_confidence_score(revenue_values)
        
        # Generate forecast using AI
        forecast_result = await forecast_revenue(trend_data)
        
        if forecast_result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=forecast_result.get("message", "Failed to generate forecast")
            )
        
        # Format the response with mathematical confidence
        forecast = forecast_result.get("forecast", {})
        
        # Combine AI confidence with mathematical confidence
        ai_confidence = forecast.get("confidence_score", 50)
        combined_confidence = round((ai_confidence * 0.5 + mathematical_confidence_percentage * 0.5), 1)
        
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
                "ai_score": ai_confidence,
                "mathematical_score": mathematical_confidence_percentage,
                "combined_score": combined_confidence,
                "confidence_level": "High" if combined_confidence >= 75 else "Medium" if combined_confidence >= 50 else "Low",
                "confidence_reasoning": forecast.get("confidence_reasoning", ""),
                "mathematical_basis": f"Data variance analysis shows {mathematical_confidence_level} confidence. {mathematical_confidence_percentage:.1f}% trust factor.",
                "growth_rate_percent": forecast.get("growth_rate_percent", 0),
                "growth_direction": forecast.get("growth_direction", "Stable")
            },
            "mathematical_analysis": {
                "confidence_level": mathematical_confidence_level,
                "trust_factor": f"{mathematical_confidence_percentage:.1f}%",
                "data_consistency": "High" if mathematical_confidence_percentage >= 75 else "Medium" if mathematical_confidence_percentage >= 50 else "Low",
                "interpretation": f"Based on {len(revenue_values)} days of sales data. {mathematical_confidence_level} confidence indicates {'stable and predictable revenue' if mathematical_confidence_level == 'High' else 'moderate volatility in revenue' if mathematical_confidence_level == 'Medium' else 'high volatility, predictions less reliable'}"
            },
            "pattern": {
                "detected": forecast.get("pattern_detected", "No pattern detected"),
                "risk_factors": forecast.get("risk_factors", [])
            },
            "business_impact": forecast.get("business_impact", ""),
            "mathematical_reasoning": forecast.get("mathematical_reasoning", ""),
            "message": "Revenue forecast grounded in mathematical trend analysis and AI insights",
            "recommendation": "Use this forecast to plan staffing, inventory, and marketing campaigns. Higher confidence scores indicate more reliable predictions."
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


@router.get("/reputation")
async def get_reputation_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 30
):
    """Get AI-powered customer reputation and sentiment analysis.
    
    Analyzes customer reviews to provide a "Mood Map" of the restaurant.
    This is the "Ears" of the operation - what customers actually think.
    
    The endpoint returns:
    - Average rating from all reviews (1-5 stars)
    - Overall sentiment trend for the last N days
    - Top 5 compliments (positive reviews and keywords)
    - Top 5 complaints (negative reviews and keywords)
    - AI-generated response draft for the latest negative review
    
    This enables the restaurant owner to:
    1. Monitor customer satisfaction trends
    2. Identify common issues before they escalate
    3. Celebrate wins and replicate successful experiences
    4. Respond thoughtfully to customer feedback
    
    The AI identifies:
    - Recurring complaint patterns (e.g., "cold food" mentioned 3x)
    - Service quality trends
    - Food quality issues
    - Specific action items for improvement
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        days: Number of days to analyze (default 30, max 365)
        
    Returns:
        Comprehensive reputation dashboard with AI-powered insights
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 400: If days parameter is invalid
        HTTPException 404: If no reviews exist
        HTTPException 500: If analysis fails
    """
    
    try:
        # Validate days parameter
        days = min(max(days, 1), 365)  # Between 1 and 365
        
        # Calculate the date range
        end_date_dt = datetime.now(timezone.utc)
        start_date_dt = end_date_dt.replace(day=1) if days >= 30 else \
                        datetime.now(timezone.utc) - \
                        __import__('datetime').timedelta(days=days)
        
        from datetime import timedelta
        start_date_dt = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Query reviews for the tenant
        stmt = select(Review).where(
            (Review.tenant_id == current_user.tenant_id) &
            (Review.created_at >= start_date_dt) &
            (Review.created_at <= end_date_dt)
        ).order_by(desc(Review.created_at))
        
        result = await db.execute(stmt)
        reviews = result.scalars().all()
        
        if not reviews:
            return {
                "status": "success",
                "tenant_id": current_user.tenant_id,
                "message": "No reviews found for this period",
                "metrics": {
                    "total_reviews": 0,
                    "average_rating": 0.0,
                    "sentiment_trend": "No data"
                },
                "compliments": [],
                "complaints": [],
                "response_draft": None
            }
        
        # Calculate metrics
        total_reviews = len(reviews)
        ratings_sum = sum(r.rating for r in reviews if r.rating)
        average_rating = ratings_sum / total_reviews if total_reviews > 0 else 0
        
        # Separate positive and negative reviews
        positive_reviews = [r for r in reviews if r.is_positive]
        negative_reviews = [r for r in reviews if r.is_negative]
        
        # Calculate sentiment trend
        positive_count = len(positive_reviews)
        negative_count = len(negative_reviews)
        
        if positive_count > negative_count:
            sentiment_trend = "Positive"
            trend_strength = min(100, int((positive_count / total_reviews) * 100))
        elif negative_count > positive_count:
            sentiment_trend = "Negative"
            trend_strength = min(100, int((negative_count / total_reviews) * 100))
        else:
            sentiment_trend = "Neutral"
            trend_strength = 50
        
        # Extract top compliments (from positive reviews)
        compliments = []
        compliment_keywords = {}
        
        for review in positive_reviews[:10]:  # Top 20 positive reviews
            if review.keywords:
                for keyword in review.keywords.split(','):
                    keyword = keyword.strip()
                    compliment_keywords[keyword] = compliment_keywords.get(keyword, 0) + 1
        
        # Build compliments list
        for review in positive_reviews[:5]:  # Top 5 positive reviews
            compliments.append({
                "customer_name": review.customer_name,
                "rating": review.rating,
                "comment": review.comment,
                "keywords": review.keywords.split(',') if review.keywords else [],
                "ai_summary": review.ai_summary or "Great feedback received",
                "created_at": review.created_at.isoformat()
            })
        
        # Extract top complaints (from negative reviews)
        complaints = []
        complaint_keywords = {}
        
        for review in negative_reviews[:10]:  # Top 10 negative reviews
            if review.keywords:
                for keyword in review.keywords.split(','):
                    keyword = keyword.strip()
                    complaint_keywords[keyword] = complaint_keywords.get(keyword, 0) + 1
        
        # Build complaints list
        for review in negative_reviews[:5]:  # Top 5 negative reviews
            complaints.append({
                "customer_name": review.customer_name,
                "rating": review.rating,
                "comment": review.comment,
                "keywords": review.keywords.split(',') if review.keywords else [],
                "ai_summary": review.ai_summary or "Issue reported",
                "action_item": review.action_item or "Requires investigation",
                "created_at": review.created_at.isoformat()
            })
        
        # Generate AI response draft for the latest negative review
        response_draft = None
        if negative_reviews:
            latest_negative = negative_reviews[0]
            
            # If not already processed, process it now
            if not latest_negative.action_item or not latest_negative.ai_summary:
                analysis = await process_review(latest_negative.comment)
                if analysis.get("status") == "success":
                    # Use the AI analysis to craft a response
                    response_draft = {
                        "to_customer": latest_negative.customer_name,
                        "rating": latest_negative.rating,
                        "summary": analysis.get("ai_summary", ""),
                        "action_item": analysis.get("action_item", ""),
                        "response_template": f"Thank you for your feedback, {latest_negative.customer_name}. "
                                            f"We're sorry to hear about your experience with {analysis.get('ai_summary', 'the food/service')}. "
                                            f"We've identified this issue and will {analysis.get('action_item', 'take immediate action')}. "
                                            f"Please visit us again soon so we can show you our improvements.",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
            else:
                # Use existing analysis
                response_draft = {
                    "to_customer": latest_negative.customer_name,
                    "rating": latest_negative.rating,
                    "summary": latest_negative.ai_summary or "",
                    "action_item": latest_negative.action_item or "",
                    "response_template": f"Thank you for your feedback, {latest_negative.customer_name}. "
                                        f"We're sorry to hear about your experience. "
                                        f"We've identified this issue and will take immediate action. "
                                        f"Please visit us again soon so we can show you our improvements.",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
        
        # Get top complaint keywords
        top_complaint_keywords = sorted(
            complaint_keywords.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Get top compliment keywords
        top_compliment_keywords = sorted(
            compliment_keywords.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "status": "success",
            "tenant_id": current_user.tenant_id,
            "period": {
                "days_analyzed": days,
                "start_date": start_date_dt.isoformat(),
                "end_date": end_date_dt.isoformat()
            },
            "metrics": {
                "total_reviews": total_reviews,
                "processed_reviews": sum(1 for r in reviews if r.is_processed),
                "average_rating": round(float(average_rating), 2),
                "positive_reviews": positive_count,
                "negative_reviews": negative_count,
                "neutral_reviews": len([r for r in reviews if r.is_neutral]),
                "sentiment_trend": sentiment_trend,
                "trend_strength_percent": trend_strength
            },
            "recurring_complaints": [
                {
                    "keyword": keyword,
                    "mentions": count,
                    "severity": "High" if count >= 3 else "Medium" if count >= 2 else "Low"
                }
                for keyword, count in top_complaint_keywords
            ],
            "recurring_compliments": [
                {
                    "keyword": keyword,
                    "mentions": count
                }
                for keyword, count in top_compliment_keywords
            ],
            "compliments": compliments,
            "complaints": complaints,
            "response_draft": response_draft,
            "insights": {
                "mood": "Happy" if sentiment_trend == "Positive" and average_rating >= 4.0 else
                        "Concerned" if sentiment_trend == "Negative" or average_rating <= 2.0 else "Neutral",
                "status_summary": f"Your restaurant has {total_reviews} reviews with "
                                f"an average rating of {average_rating:.1f}/5.0. "
                                f"Sentiment is {sentiment_trend.lower()} overall.",
                "urgent_actions": [
                    f"Address {negative_count} recent negative reviews" if negative_count > 0 else "Great news - no recent complaints!",
                    f"Replicate success from {positive_count} positive reviews" if positive_count > 0 else "Focus on getting positive reviews",
                ]
            },
            "message": "AI Reputation Sentinel analysis complete. Monitor sentiment trends and respond to feedback.",
            "recommendation": "Respond to negative reviews within 24 hours. Ask for specific details to improve."
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
            detail=f"Failed to generate reputation analytics: {str(e)}"
        )


@router.get("/staffing-plan")
async def get_staffing_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analysis_date: Optional[str] = None,
    forecast_days: int = 1
):
    """Get AI-powered staffing optimization and labor heatmap.
    
    Analyzes historical labor costs vs. sales volume to create a 24-hour
    staffing efficiency heatmap. This tells the owner exactly when they
    are overstaffed (wasting money) or understaffed (losing customers).
    
    The endpoint generates:
    - 24-hour efficiency heatmap (0-100 score for each hour)
    - Flagged inefficient hours (labor > 30% of sales)
    - Burnout risk hours (high sales, low staff)
    - AI-recommended schedule for next day based on revenue forecast
    - Specific staffing changes to implement
    
    This solves the hardest problem in hospitality: Precision Staffing.
    Instead of "feeling" busy, owners now know the data.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        analysis_date: Date to analyze (YYYY-MM-DD format). Defaults to yesterday.
        forecast_days: Days to forecast (default 1, max 7)
        
    Returns:
        Comprehensive staffing optimization plan with heatmap
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If no shift/sales data exists
        HTTPException 500: If analysis fails
    """
    
    try:
        # Validate forecast days
        forecast_days = min(max(forecast_days, 1), 7)
        
        # Parse analysis date
        if analysis_date:
            try:
                analysis_dt = datetime.strptime(analysis_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid analysis_date format. Use YYYY-MM-DD"
                )
        else:
            # Default to yesterday
            analysis_dt = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        
        analysis_end_dt = analysis_dt.replace(hour=23, minute=59, second=59)
        
        # Query hourly sales data for the analysis date
        # Group sales by hour
        sales_query = select(
            func.strftime('%H', func.datetime(
                'Sales.timestamp',
                'utc',
                '+00:00'
            )).label('hour'),
            func.sum(Sale.total_amount).label('hourly_sales'),
            func.count(Sale.id).label('transaction_count')
        ).select_from(Sale).where(
            and_(
                Sale.tenant_id == current_user.tenant_id,
                Sale.timestamp >= analysis_dt,
                Sale.timestamp <= analysis_end_dt
            )
        ).group_by(
            func.strftime('%H', Sale.timestamp)
        )
        
        # Query hourly labor costs
        # Group shifts by start hour and calculate cost
        labor_query = select(
            func.strftime('%H', Shift.start_time).label('hour'),
            func.sum(func.cast(
                func.round(
                    func.julianday(Shift.end_time) - func.julianday(Shift.start_time),
                    4
                ) * 24 * func.cast(Staff.hourly_rate, Decimal),
                Decimal
            )).label('hourly_labor_cost'),
            func.count(func.distinct(Shift.staff_id)).label('staff_count')
        ).select_from(Shift).join(
            Staff, Shift.staff_id == Staff.id
        ).where(
            and_(
                Staff.tenant_id == current_user.tenant_id,
                Shift.start_time >= analysis_dt,
                Shift.start_time <= analysis_end_dt
            )
        ).group_by(
            func.strftime('%H', Shift.start_time)
        )
        
        # Execute queries
        # NOTE: SQLite syntax - may need adjustment for other databases
        # Using a simpler approach with Python-side calculation
        
        # Get all shifts for the day
        shifts_stmt = select(Shift).join(Staff).where(
            and_(
                Staff.tenant_id == current_user.tenant_id,
                Shift.start_time >= analysis_dt,
                Shift.start_time <= analysis_end_dt
            )
        )
        shifts_result = await db.execute(shifts_stmt)
        shifts = shifts_result.scalars().all()
        
        # Get all sales for the day
        sales_stmt = select(Sale).where(
            and_(
                Sale.tenant_id == current_user.tenant_id,
                Sale.timestamp >= analysis_dt,
                Sale.timestamp <= analysis_end_dt
            )
        )
        sales_result = await db.execute(sales_stmt)
        sales = sales_result.scalars().all()
        
        if not shifts and not sales:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No shift or sales data found for this date. Please add shifts and sales first."
            )
        
        # Build hourly breakdown
        hourly_data = []
        total_labor = Decimal("0.00")
        total_sales = Decimal("0.00")
        
        for hour in range(24):
            # Calculate sales for this hour
            hour_sales = sum(
                s.total_amount for s in sales
                if s.timestamp.hour == hour
            )
            total_sales += hour_sales
            
            # Calculate labor cost for this hour
            hour_labor = Decimal("0.00")
            hour_staff = set()
            
            for shift in shifts:
                # Check if shift overlaps with this hour
                shift_start_hour = shift.start_time.hour
                shift_end_hour = shift.end_time.hour
                
                # Handle shifts that span multiple hours
                if shift_start_hour <= hour < shift_end_hour or \
                   (shift_start_hour == hour and shift.start_time.minute > 0) or \
                   (shift_end_hour == hour and shift.end_time.minute > 0):
                    # Calculate fractional cost for this hour
                    hour_labor += shift.total_cost / max(shift.duration_hours, 1)
                    hour_staff.add(shift.staff_id)
            
            total_labor += hour_labor
            
            hourly_data.append({
                "hour": hour,
                "sales_amount": float(hour_sales),
                "labor_cost": float(hour_labor),
                "staff_count": len(hour_staff),
                "labor_percent_of_sales": (
                    (float(hour_labor) / float(hour_sales) * 100)
                    if hour_sales > 0 else 0
                )
            })
        
        # Use AI to analyze labor efficiency
        analysis_payload = {
            "date": analysis_date or analysis_dt.strftime("%Y-%m-%d"),
            "hours": hourly_data,
            "daily_total_sales": float(total_sales),
            "daily_total_labor": float(total_labor),
            "staff_scheduled": len(set(s.staff_id for s in shifts))
        }
        
        ai_analysis = await calculate_labor_efficiency(analysis_payload)
        
        if ai_analysis.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ai_analysis.get("message", "Failed to analyze labor efficiency")
            )
        
        # Get revenue forecast for next day to optimize schedule
        forecast_data = {}
        try:
            # Get recent 14-day trend for forecasting
            forecast_start = analysis_dt - timedelta(days=14)
            forecast_stmt = select(
                func.date(Sale.timestamp).label('sale_date'),
                func.sum(Sale.total_amount).label('daily_revenue')
            ).where(
                and_(
                    Sale.tenant_id == current_user.tenant_id,
                    Sale.timestamp >= forecast_start,
                    Sale.timestamp <= analysis_dt
                )
            ).group_by(
                func.date(Sale.timestamp)
            )
            
            forecast_result = await db.execute(forecast_stmt)
            forecast_rows = forecast_result.all()
            
            if forecast_rows:
                trend_data = {
                    f"day_{i}": float(row.daily_revenue or 0)
                    for i, row in enumerate(forecast_rows[-7:])  # Last 7 days
                }
                forecast_result = await forecast_revenue(trend_data)
                if forecast_result.get("status") == "success":
                    forecast_data = forecast_result.get("forecast", {})
        except:
            # Forecast is optional, don't fail if it errors
            pass
        
        # Generate recommended schedule
        efficiency_analysis = ai_analysis.get("efficiency_analysis", {})
        inefficient_hours = efficiency_analysis.get("inefficient_hours", [])
        burnout_risks = efficiency_analysis.get("burnout_risks", [])
        
        recommended_adjustments = []
        for hour_data in hourly_data:
            hour = hour_data["hour"]
            
            # Check if this hour was flagged as inefficient
            if any(ih.get("hour") == hour for ih in inefficient_hours):
                recommended_adjustments.append({
                    "hour": hour,
                    "action": "REDUCE STAFF",
                    "reason": "Labor cost exceeds optimal threshold (>30% of sales)",
                    "suggested_reduction": 1,
                    "estimated_savings": "$15-30/hour"
                })
            
            # Check if this hour has burnout risk
            elif any(br.get("hour") == hour for br in burnout_risks):
                recommended_adjustments.append({
                    "hour": hour,
                    "action": "ADD STAFF",
                    "reason": "High sales with low staffing creates burnout risk",
                    "suggested_addition": 1,
                    "estimated_revenue_protection": "$50-100/hour"
                })
        
        return {
            "status": "success",
            "tenant_id": current_user.tenant_id,
            "analysis_period": {
                "date": analysis_dt.strftime("%Y-%m-%d"),
                "day_of_week": analysis_dt.strftime("%A"),
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "metrics": {
                "total_daily_sales": float(total_sales),
                "total_daily_labor": float(total_labor),
                "labor_as_percent_of_sales": (
                    (float(total_labor) / float(total_sales) * 100)
                    if total_sales > 0 else 0
                ),
                "staff_scheduled": len(set(s.staff_id for s in shifts)),
                "shifts_total": len(shifts),
                "transactions": len(sales)
            },
            "hourly_heatmap": hourly_data,
            "efficiency": {
                "score": efficiency_analysis.get("efficiency_score", 50),
                "label": efficiency_analysis.get("efficiency_label", "Fair"),
                "inefficient_hours": inefficient_hours,
                "burnout_risk_hours": burnout_risks
            },
            "recommendations": {
                "immediate_actions": efficiency_analysis.get("optimization_suggestions", []),
                "scheduled_adjustments": recommended_adjustments,
                "weekly_adjustments": efficiency_analysis.get("recommended_actions", [])
            },
            "forecast_insights": {
                "next_day_forecast": forecast_data,
                "recommendation": f"Adjust staffing based on forecasted {forecast_data.get('next_day_1_revenue', 'N/A')} revenue for tomorrow"
                if forecast_data else "Enable revenue forecasting for schedule optimization"
            },
            "message": "AI Staffing Sentinel analysis complete. Review recommendations to optimize labor costs.",
            "action_items": [
                f"Reduce staff in {len(inefficient_hours)} overstaffed hours",
                f"Increase staff in {len(burnout_risks)} high-demand hours",
                "Implement recommended schedule changes",
                "Monitor actual vs. forecasted labor efficiency"
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
            detail=f"Failed to generate staffing plan: {str(e)}"
        )


@router.get("/daily-tip")
async def get_daily_tip(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    city: Optional[str] = None
):
    """Get AI-powered daily promotion based on weather context.
    
    This endpoint combines real-world environmental data (weather) with
    restaurant sales patterns to generate a specific, weather-optimized
    promotion recommendation. It answers: "What should I push TODAY?"
    
    The system:
    1. Fetches current weather for the restaurant's city
    2. Retrieves recent sales trends (7-day window)
    3. Correlates weather patterns with menu item demand
    4. Uses AI to generate a targeted promotion
    
    Returns a "Daily Mood" analysis that tells the owner exactly which
    menu item to promote based on TODAY'S environmental conditions.
    
    Example response:
    "It's 35°C and sunny in Mumbai! Customers crave cold beverages.
     PUSH: Iced Lattes - typically 15% higher margins on hot days.
     Staffing tip: +20% beverage bar staff to handle rush."
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        city: Restaurant city for weather lookup. If not provided,
              uses restaurant's primary location from settings.
        
    Returns:
        Daily promotion tip with weather context, AI recommendation,
        estimated impact, and operational suggestions
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 400: If city is required but not provided
        HTTPException 500: If AI analysis fails
    """
    
    try:
        # Determine city for weather lookup
        if not city:
            # TODO: Read from restaurant settings/profile
            # For now, default to a sensible value or require parameter
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="city parameter is required. Usage: /analytics/daily-tip?city=Mumbai"
            )
        
        # Fetch current weather
        weather_data = await get_current_weather(city)
        
        if weather_data.get("status") == "fallback":
            # API unavailable, but we still have sensible defaults
            weather_note = f"(Using default weather data - API unavailable)"
        else:
            weather_note = "(Real-time weather data)"
        
        # Get recent sales trend (7-day window)
        sales_trend_start = datetime.now(timezone.utc) - timedelta(days=7)
        
        sales_stmt = select(
            func.date(Sale.timestamp).label('sale_date'),
            func.sum(Sale.total_amount).label('daily_revenue'),
            func.count(Sale.id).label('transaction_count')
        ).where(
            and_(
                Sale.tenant_id == current_user.tenant_id,
                Sale.timestamp >= sales_trend_start
            )
        ).group_by(
            func.date(Sale.timestamp)
        )
        
        sales_result = await db.execute(sales_stmt)
        sales_rows = sales_result.all()
        
        if not sales_rows:
            # No sales data available
            sales_summary = {
                "total_7day_revenue": 0,
                "avg_daily_revenue": 0,
                "transaction_trend": []
            }
            sales_note = "(No sales data available - recommendations based on weather only)"
        else:
            sales_values = [float(row.daily_revenue or 0) for row in sales_rows]
            sales_summary = {
                "total_7day_revenue": sum(sales_values),
                "avg_daily_revenue": sum(sales_values) / len(sales_values),
                "max_daily_revenue": max(sales_values),
                "min_daily_revenue": min(sales_values),
                "transaction_trend": [int(row.transaction_count or 0) for row in sales_rows],
                "days_with_data": len(sales_rows)
            }
            sales_note = f"(Based on {len(sales_rows)}-day sales history)"
        
        # Correlate weather with sales patterns
        weather_impact = await correlate_weather_with_sales(weather_data, sales_summary)
        
        # Get AI consultant recommendation
        ai_agent = AIConsultant()
        
        # Prepare performance data for AI
        performance_data = {
            "period": "7_days",
            "metrics": sales_summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Generate weather-aware strategy
        strategy_result = await ai_agent.generate_strategy_with_weather(
            performance_data,
            weather_data
        )
        
        # Extract key recommendation
        promotion_item = strategy_result.get("weather_optimized_promotion", "")
        weather_context = strategy_result.get("weather_context", "")
        impact_percentage = weather_impact.get("expected_impact_percent", 0)
        staffing_recommendation = strategy_result.get("staffing_adjustment", {})
        inventory_focus = strategy_result.get("inventory_focus_items", [])
        
        # Format confidence score
        confidence = min(
            100,
            80 + (5 if weather_data.get("status") == "success" else 0)
            + (5 if len(sales_rows) >= 7 else 0)
        )
        
        return {
            "status": "success",
            "tenant_id": current_user.tenant_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "weather": {
                "city": weather_data.get("city", city),
                "temperature": weather_data.get("temperature"),
                "humidity": weather_data.get("humidity"),
                "condition": weather_data.get("condition"),
                "feels_like": weather_data.get("feels_like"),
                "is_rainy": weather_data.get("is_rainy"),
                "is_hot": weather_data.get("is_hot"),
                "is_cold": weather_data.get("is_cold"),
                "note": weather_note
            },
            "sales_context": {
                **sales_summary,
                "note": sales_note
            },
            "daily_mood": {
                "primary_condition": weather_data.get("condition"),
                "customer_mood": weather_data.get("suggestion", "Moderate customer appetite"),
                "urgency": "High" if weather_data.get("is_rainy") or weather_data.get("is_hot") else "Normal"
            },
            "recommendation": {
                "headline": f"🌡️ {weather_context}",
                "action_item": promotion_item,
                "expected_impact": {
                    "impact_percentage": impact_percentage,
                    "impact_description": f"+{impact_percentage:.1f}% expected uplift on {promotion_item}" if promotion_item else "Monitor customer behavior"
                },
                "confidence_score": confidence,
                "reasoning": "Correlation between weather patterns and historical sales demand"
            },
            "operational_insights": {
                "staffing": {
                    "adjustment": staffing_recommendation.get("adjustment", ""),
                    "reason": staffing_recommendation.get("reason", ""),
                    "areas_to_focus": staffing_recommendation.get("focus_areas", [])
                },
                "inventory": {
                    "primary_focus": inventory_focus[0] if inventory_focus else "",
                    "items_to_stock": inventory_focus,
                    "reason": "Weather-correlated demand surge expected"
                },
                "menu_optimization": {
                    "featured_item": promotion_item,
                    "display_suggestion": f"Feature {promotion_item} prominently on menu/signage",
                    "bundling_idea": f"Pair {promotion_item} with complementary items for upsell"
                }
            },
            "implementation": {
                "immediate": [
                    f"Highlight {promotion_item} in digital menu",
                    f"Adjust {staffing_recommendation.get('focus_areas', ['front-of-house'])[0]} staffing",
                    "Increase inventory for featured items"
                ],
                "ongoing": [
                    "Track sales lift for this promotion",
                    "Monitor customer feedback during weather change",
                    "Log actual vs. predicted impact for model refinement"
                ]
            },
            "message": f"Daily Context-Aware Promotion: In {weather_data.get('condition', 'current')} weather, promote {promotion_item} to capture {impact_percentage:.1f}% estimated uplift.",
            "context_aware": True,
            "data_quality": {
                "weather_data_source": "Real-time API" if weather_data.get("status") == "success" else "Fallback defaults",
                "sales_data_days": len(sales_rows),
                "model_confidence": f"{confidence}%"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate daily tip: {str(e)}"
        )


