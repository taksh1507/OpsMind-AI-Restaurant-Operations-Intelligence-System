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
from app.models import User, Review
from app.services.analytics import (
    calculate_revenue_and_profit,
    calculate_profit_margin,
    get_top_selling_items,
    get_daily_sales_trend
)
from app.services.ai_agent import forecast_revenue, analyze_profit_margins, process_review
from app.services.margin_analysis import (
    get_all_menu_items_with_costs,
    get_margin_report_summary
)
from sqlalchemy import select, func, desc


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

