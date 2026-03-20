"""Margin Analysis Service

Calculates and analyzes menu item margins based on ingredient costs.
Provides COGS (Cost of Goods Sold) calculations and optimization recommendations.
"""

from decimal import Decimal
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import MenuItem, Recipe, Ingredient


async def calculate_menu_item_cost(
    session: AsyncSession,
    menu_item_id: int
) -> Decimal:
    """Calculate the total cost of goods sold (COGS) for a single menu item.
    
    Sums the cost of all ingredients used in the recipe:
    COGS = SUM(Ingredient.unit_cost * Recipe.quantity_used)
    
    Args:
        session: AsyncSession for database operations
        menu_item_id: The menu item to calculate cost for
        
    Returns:
        Total COGS as Decimal, or Decimal("0") if no recipe found
    """
    try:
        # Get all recipes for this menu item
        result = await session.execute(
            select(
                Recipe.quantity_used,
                Ingredient.unit_cost
            ).select_from(Recipe).join(
                Ingredient, Recipe.ingredient_id == Ingredient.id
            ).where(
                Recipe.menu_item_id == menu_item_id
            )
        )
        
        total_cost = Decimal("0")
        for row in result:
            quantity = Decimal(str(row.quantity_used))
            unit_cost = row.unit_cost
            total_cost += quantity * unit_cost
        
        return total_cost
    
    except Exception as e:
        raise ValueError(f"Failed to calculate menu item cost: {str(e)}")


async def get_all_menu_items_with_costs(
    session: AsyncSession,
    tenant_id: int
) -> List[Dict[str, Any]]:
    """Get all menu items for a tenant with their COGS and margin information.
    
    Returns menu items with calculated costs for margin analysis.
    
    Args:
        session: AsyncSession for database operations
        tenant_id: The restaurant's tenant ID
        
    Returns:
        List of menu items with:
        {
            "id": int,
            "name": str,
            "price": float,
            "cost_of_goods": float,
            "margin_percent": float,
            "price_to_cost_ratio": float
        }
    """
    try:
        # Get all menu items for this tenant
        result = await session.execute(
            select(MenuItem).where(
                MenuItem.tenant_id == tenant_id
            ).order_by(MenuItem.name)
        )
        
        menu_items = []
        for item in result.scalars().all():
            # Calculate COGS for this item
            cogs = await calculate_menu_item_cost(session, item.id)
            
            price = float(item.price)
            cogs_float = float(cogs)
            
            # Calculate margin percentage
            if price > 0:
                margin = ((price - cogs_float) / price) * 100
            else:
                margin = 0
            
            # Calculate price-to-cost ratio
            if cogs_float > 0:
                ratio = price / cogs_float
            else:
                ratio = 0
            
            menu_items.append({
                "id": item.id,
                "name": item.name,
                "price": price,
                "cost_of_goods": cogs_float,
                "margin_percent": margin,
                "price_to_cost_ratio": ratio
            })
        
        return menu_items
    
    except Exception as e:
        raise ValueError(f"Failed to get menu items with costs: {str(e)}")


async def get_margin_report_summary(
    session: AsyncSession,
    tenant_id: int
) -> Dict[str, Any]:
    """Get a summary of margin metrics for the restaurant.
    
    Provides overview statistics for margin health assessment.
    
    Args:
        session: AsyncSession for database operations
        tenant_id: The restaurant's tenant ID
        
    Returns:
        Dictionary with margin metrics:
        {
            "total_items": int,
            "items_healthy": int,
            "items_at_risk": int,
            "average_margin_percent": float,
            "total_revenue_at_risk": float,
            "potential_improvement": float
        }
    """
    items = await get_all_menu_items_with_costs(session, tenant_id)
    
    if not items:
        return {
            "total_items": 0,
            "items_healthy": 0,
            "items_at_risk": 0,
            "average_margin_percent": 0,
            "total_revenue_at_risk": 0,
            "potential_improvement": 0
        }
    
    total_items = len(items)
    items_at_risk = sum(1 for item in items if item["price_to_cost_ratio"] < 3.0)
    items_healthy = total_items - items_at_risk
    
    average_margin = sum(item["margin_percent"] for item in items) / total_items if items else 0
    
    total_revenue_at_risk = sum(
        item["price"] for item in items 
        if item["price_to_cost_ratio"] < 3.0
    )
    
    # Estimate potential improvement if all at-risk items are raised to 3x multiplier
    potential_improvement = 0.0
    for item in items:
        if item["price_to_cost_ratio"] < 3.0 and item["cost_of_goods"] > 0:
            suggested_price = item["cost_of_goods"] * 3.2
            improvement = suggested_price - item["price"]
            potential_improvement += improvement
    
    # Multiply by 30 to get rough monthly estimate (assuming 30 sales/item/month)
    potential_improvement *= 30
    
    return {
        "total_items": total_items,
        "items_healthy": items_healthy,
        "items_at_risk": items_at_risk,
        "average_margin_percent": round(average_margin, 2),
        "total_revenue_at_risk": round(total_revenue_at_risk, 2),
        "potential_improvement": round(potential_improvement, 2)
    }
