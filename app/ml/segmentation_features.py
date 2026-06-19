"""Customer Behavioral Segmentation Features.

Calculates behavioral features for each customer to replace the rule-based persona engine.
Features computed:
- order_frequency: total orders in the last 90 days
- avg_spend: average order value
- recency_days: days since last order
- top_category: most-ordered menu category (tie-broken alphabetically)
- total_items: total items ordered
- avg_items_per_order: average items per order
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales import Sale, SaleItem
from app.models.menu import MenuItem, Category


def _to_naive(dt: Optional[datetime]) -> Optional[datetime]:
    """Strip timezone info to make comparison safe."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


async def build_segmentation_features(
    session: AsyncSession,
    tenant_id: int,
    reference_date: Optional[datetime] = None
) -> pd.DataFrame:
    """Query database and compute customer behavioral segmentation features.
    
    Args:
        session: AsyncSession for database operations
        tenant_id: The tenant identifier
        reference_date: The reference point for calculating recency and frequency
        
    Returns:
        pd.DataFrame containing:
            customer_id (int)
            order_frequency (int)
            avg_spend (float)
            recency_days (float)
            top_category (str)
            total_items (int)
            avg_items_per_order (float)
        Only returns rows for customers with 2 or more orders.
    """
    if reference_date is None:
        reference_date = datetime.utcnow()
    reference_date = _to_naive(reference_date)

    # 1. Query Sales
    sales_stmt = select(
        Sale.customer_id,
        Sale.id.label("sale_id"),
        Sale.total_amount,
        Sale.timestamp
    ).where(
        Sale.tenant_id == tenant_id,
        Sale.customer_id.isnot(None)
    )
    sales_result = await session.execute(sales_stmt)
    sales_rows = sales_result.all()

    # 2. Query SaleItems with Category names
    items_stmt = select(
        Sale.customer_id,
        SaleItem.sale_id,
        SaleItem.quantity,
        Category.name.label("category_name")
    ).select_from(
        SaleItem
    ).join(
        Sale, SaleItem.sale_id == Sale.id
    ).join(
        MenuItem, SaleItem.menu_item_id == MenuItem.id
    ).join(
        Category, MenuItem.category_id == Category.id
    ).where(
        Sale.tenant_id == tenant_id,
        Sale.customer_id.isnot(None)
    )
    items_result = await session.execute(items_stmt)
    items_rows = items_result.all()

    # Columns list
    cols = [
        "customer_id",
        "order_frequency",
        "avg_spend",
        "recency_days",
        "top_category",
        "total_items",
        "avg_items_per_order"
    ]

    # If no sales or items are returned, return an empty DataFrame with expected columns
    if not sales_rows:
        return pd.DataFrame(columns=cols)

    # Convert to DataFrames
    df_sales = pd.DataFrame([
        {
            "customer_id": r.customer_id,
            "sale_id": r.sale_id,
            "total_amount": float(r.total_amount) if isinstance(r.total_amount, (Decimal, float, int)) else 0.0,
            "timestamp": _to_naive(r.timestamp)
        }
        for r in sales_rows
    ])

    df_items = pd.DataFrame([
        {
            "customer_id": r.customer_id,
            "sale_id": r.sale_id,
            "quantity": int(r.quantity),
            "category_name": r.category_name
        }
        for r in items_rows
    ])

    # Calculate features per customer
    features_list = []
    unique_customers = df_sales["customer_id"].unique()

    for cust_id in unique_customers:
        cust_sales = df_sales[df_sales["customer_id"] == cust_id]
        total_orders = len(cust_sales)

        # Drop/handle separately: customers with 0 or 1 orders
        if total_orders < 2:
            continue

        # order_frequency: total orders in the last 90 days
        cutoff_date = reference_date - timedelta(days=90)
        freq_orders = cust_sales[
            (cust_sales["timestamp"] >= cutoff_date) & 
            (cust_sales["timestamp"] <= reference_date)
        ]
        order_frequency = len(freq_orders)

        # avg_spend: average order value
        avg_spend = round(float(cust_sales["total_amount"].mean()), 2)

        # recency_days: days since last order
        last_order_time = cust_sales["timestamp"].max()
        recency_diff = reference_date - last_order_time
        recency_days = round(max(0.0, recency_diff.total_seconds() / 86400.0), 2)

        # items calculations
        cust_items = df_items[df_items["customer_id"] == cust_id]
        total_items = int(cust_items["quantity"].sum()) if not cust_items.empty else 0
        avg_items_per_order = round(total_items / total_orders, 2) if total_orders > 0 else 0.0

        # top_category: most ordered menu category
        if not cust_items.empty and "category_name" in cust_items.columns:
            cat_grouped = cust_items.groupby("category_name")["quantity"].sum()
            if not cat_grouped.empty:
                max_qty = cat_grouped.max()
                top_cats = cat_grouped[cat_grouped == max_qty].index.tolist()
                # Resolve ties alphabetically
                top_category = sorted(top_cats)[0]
            else:
                top_category = "Unknown"
        else:
            top_category = "Unknown"

        features_list.append({
            "customer_id": int(cust_id),
            "order_frequency": int(order_frequency),
            "avg_spend": float(avg_spend),
            "recency_days": float(recency_days),
            "top_category": str(top_category),
            "total_items": int(total_items),
            "avg_items_per_order": float(avg_items_per_order)
        })

    if not features_list:
        return pd.DataFrame(columns=cols)

    return pd.DataFrame(features_list)
