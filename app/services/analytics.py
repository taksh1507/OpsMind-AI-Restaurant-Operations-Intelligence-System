"""Analytics Service

Business logic for calculating restaurant performance metrics.
Handles revenue, profit, and sales aggregation for insights.
"""

from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.models import Sale, SaleItem, MenuItem


async def calculate_revenue_and_profit(
    session: AsyncSession,
    tenant_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Decimal]:
    """Calculate total revenue and profit for a restaurant in a time range.
    
    Revenue = Sum of (SaleItem.quantity * SaleItem.unit_price_at_sale)
    
    Profit = Revenue - Cost of Goods Sold (COGS)
           = Revenue - Sum of (SaleItem.quantity * MenuItem.cost_price)
    
    Args:
        session: AsyncSession for database operations
        tenant_id: The restaurant's tenant ID
        start_date: Start of date range (inclusive). If None, from beginning of time.
        end_date: End of date range (inclusive). If None, through now.
        
    Returns:
        Dictionary with:
        - revenue: Total revenue in the period
        - cost_of_goods: Total cost of goods sold
        - profit: Gross profit (revenue - COGS)
        - transaction_count: Number of sales in period
        - item_count: Total items sold
    """
    
    # Default date range: last 30 days if not specified
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    
    # Ensure datetimes are timezone-aware
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    try:
        # Query to calculate revenue
        # Revenue = SUM(SaleItem.quantity * SaleItem.unit_price_at_sale)
        revenue_result = await session.execute(
            select(
                func.sum(
                    SaleItem.quantity * SaleItem.unit_price_at_sale
                ).label("total_revenue"),
                func.count(SaleItem.id).label("item_count"),
                func.count(Sale.id.distinct()).label("transaction_count")
            ).select_from(SaleItem).join(
                Sale, SaleItem.sale_id == Sale.id
            ).where(
                and_(
                    SaleItem.tenant_id == tenant_id,
                    Sale.timestamp >= start_date,
                    Sale.timestamp <= end_date
                )
            )
        )
        
        revenue_row = revenue_result.one()
        total_revenue = revenue_row.total_revenue or Decimal("0.00")
        item_count = revenue_row.item_count or 0
        transaction_count = revenue_row.transaction_count or 0
        
        # Query to calculate cost of goods sold
        # COGS = SUM(SaleItem.quantity * MenuItem.cost_price)
        cogs_result = await session.execute(
            select(
                func.sum(
                    SaleItem.quantity * MenuItem.cost_price
                ).label("total_cogs")
            ).select_from(SaleItem).join(
                Sale, SaleItem.sale_id == Sale.id
            ).join(
                MenuItem, SaleItem.menu_item_id == MenuItem.id
            ).where(
                and_(
                    SaleItem.tenant_id == tenant_id,
                    Sale.timestamp >= start_date,
                    Sale.timestamp <= end_date
                )
            )
        )
        
        cogs_row = cogs_result.one()
        total_cogs = cogs_row.total_cogs or Decimal("0.00")
        
        # Calculate profit
        profit = total_revenue - total_cogs
        
        return {
            "revenue": total_revenue,
            "cost_of_goods": total_cogs,
            "profit": profit,
            "transaction_count": transaction_count,
            "item_count": item_count,
            "start_date": start_date,
            "end_date": end_date
        }
    
    except Exception as e:
        raise ValueError(f"Failed to calculate revenue and profit: {str(e)}")


async def calculate_profit_margin(
    session: AsyncSession,
    tenant_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Decimal:
    """Calculate gross profit margin percentage for a restaurant.
    
    Profit Margin = (Profit / Revenue) * 100
    
    Args:
        session: AsyncSession for database operations
        tenant_id: The restaurant's tenant ID
        start_date: Start of date range
        end_date: End of date range
        
    Returns:
        Profit margin as percentage (e.g., 35.50 for 35.5%)
    """
    
    metrics = await calculate_revenue_and_profit(
        session,
        tenant_id,
        start_date,
        end_date
    )
    
    revenue = metrics["revenue"]
    profit = metrics["profit"]
    
    # Avoid division by zero
    if revenue == 0:
        return Decimal("0.00")
    
    margin = (profit / revenue) * Decimal("100")
    return margin.quantize(Decimal("0.01"))


async def calculate_daily_revenue(
    session: AsyncSession,
    tenant_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> list[Dict[str, Any]]:
    """Calculate revenue broken down by day.
    
    Useful for graphs showing daily trends.
    
    Args:
        session: AsyncSession for database operations
        tenant_id: The restaurant's tenant ID
        start_date: Start of date range
        end_date: End of date range
        
    Returns:
        List of dictionaries with date and revenue:
        [{"date": "2026-03-18", "revenue": Decimal("125.50"), "transactions": 10}, ...]
    """
    
    # Default date range
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    
    # Ensure timezone-aware
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    try:
        result = await session.execute(
            select(
                func.date(Sale.timestamp).label("sale_date"),
                func.sum(
                    SaleItem.quantity * SaleItem.unit_price_at_sale
                ).label("daily_revenue"),
                func.count(Sale.id.distinct()).label("transaction_count")
            ).select_from(SaleItem).join(
                Sale, SaleItem.sale_id == Sale.id
            ).where(
                and_(
                    SaleItem.tenant_id == tenant_id,
                    Sale.timestamp >= start_date,
                    Sale.timestamp <= end_date
                )
            ).group_by(func.date(Sale.timestamp)).order_by(
                func.date(Sale.timestamp).asc()
            )
        )
        
        daily_data = []
        for row in result.scalars().all():
            daily_data.append({
                "date": str(row.sale_date),
                "revenue": row.daily_revenue or Decimal("0.00"),
                "transactions": row.transaction_count or 0
            })
        
        return daily_data
    
    except Exception as e:
        raise ValueError(f"Failed to calculate daily revenue: {str(e)}")


async def get_top_selling_items(
    session: AsyncSession,
    tenant_id: int,
    limit: int = 5,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get the top-selling menu items for a restaurant.
    
    Groups sales by menu item name, sums quantities, and returns top sellers.
    This identifies the "Stars" of the restaurant's menu.
    
    Args:
        session: AsyncSession for database operations
        tenant_id: The restaurant's tenant ID
        limit: Maximum number of items to return (default 5)
        start_date: Start of date range
        end_date: End of date range
        
    Returns:
        List of top-selling items with quantities, sorted by sales descending:
        [
            {"menu_item_id": 1, "name": "Margherita Pizza", "quantity_sold": 450, "revenue": Decimal("4500.00")},
            {"menu_item_id": 2, "name": "Caesar Salad", "quantity_sold": 320, "revenue": Decimal("1920.00")},
            ...
        ]
    """
    
    # Default date range: last 30 days
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    
    # Ensure timezone-aware
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    try:
        result = await session.execute(
            select(
                SaleItem.menu_item_id,
                MenuItem.name,
                func.sum(SaleItem.quantity).label("quantity_sold"),
                func.sum(
                    SaleItem.quantity * SaleItem.unit_price_at_sale
                ).label("revenue")
            ).select_from(SaleItem).join(
                Sale, SaleItem.sale_id == Sale.id
            ).join(
                MenuItem, SaleItem.menu_item_id == MenuItem.id
            ).where(
                and_(
                    SaleItem.tenant_id == tenant_id,
                    Sale.timestamp >= start_date,
                    Sale.timestamp <= end_date
                )
            ).group_by(
                SaleItem.menu_item_id,
                MenuItem.name
            ).order_by(
                desc(func.sum(SaleItem.quantity))
            ).limit(limit)
        )
        
        top_items = []
        for row in result:
            top_items.append({
                "menu_item_id": row.menu_item_id,
                "name": row.name,
                "quantity_sold": row.quantity_sold,
                "revenue": row.revenue or Decimal("0.00")
            })
        
        return top_items
    
    except Exception as e:
        raise ValueError(f"Failed to get top-selling items: {str(e)}")


async def get_daily_sales_trend(
    session: AsyncSession,
    tenant_id: int,
    days: int = 14
) -> Dict[str, float]:
    """Get historical daily revenue trends for time-series analysis.
    
    Returns the last N days of total revenue, grouped by date.
    This data is used by the AI to identify patterns and predict future sales.
    
    Args:
        session: AsyncSession for database operations
        tenant_id: The restaurant's tenant ID
        days: Number of historical days to retrieve (default 14)
        
    Returns:
        Dictionary mapping dates to revenue totals:
        {
            "2026-03-19": 450.0,
            "2026-03-20": 510.0,
            "2026-03-21": 485.5,
            ...
        }
        Ordered chronologically from earliest to latest date.
    """
    
    # Calculate date range: last N days up to today
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Ensure timezone-aware
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    try:
        result = await session.execute(
            select(
                func.date(Sale.timestamp).label("sale_date"),
                func.sum(
                    SaleItem.quantity * SaleItem.unit_price_at_sale
                ).label("daily_revenue")
            ).select_from(SaleItem).join(
                Sale, SaleItem.sale_id == Sale.id
            ).where(
                and_(
                    SaleItem.tenant_id == tenant_id,
                    Sale.timestamp >= start_date,
                    Sale.timestamp <= end_date
                )
            ).group_by(func.date(Sale.timestamp)).order_by(
                func.date(Sale.timestamp).asc()
            )
        )
        
        # Build dictionary mapping date strings to revenue floats
        trend_data = {}
        for row in result:
            date_key = str(row.sale_date)
            revenue = float(row.daily_revenue or Decimal("0.00"))
            trend_data[date_key] = revenue
        
        return trend_data
    
    except Exception as e:
        raise ValueError(f"Failed to get daily sales trend: {str(e)}")
