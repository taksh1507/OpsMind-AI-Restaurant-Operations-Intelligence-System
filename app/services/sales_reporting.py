"""Tenant-scoped sales reporting in the stored INR currency."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select, func
from app.models import Sale, SaleItem, MenuItem
from app.core.time_utils import as_utc


async def period_totals(db, tenant_id, start, end):
    conditions = (
        Sale.tenant_id == tenant_id,
        Sale.timestamp >= start,
        Sale.timestamp < end,
    )
    revenue, orders = (
        await db.execute(
            select(
                func.coalesce(func.sum(Sale.total_amount), 0), func.count(Sale.id)
            ).where(*conditions)
        )
    ).one()
    cost, quantity = (
        await db.execute(
            select(
                func.coalesce(func.sum(SaleItem.quantity * MenuItem.cost_price), 0),
                func.coalesce(func.sum(SaleItem.quantity), 0),
            )
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(MenuItem, MenuItem.id == SaleItem.menu_item_id)
            .where(
                *conditions,
                SaleItem.tenant_id == tenant_id,
                MenuItem.tenant_id == tenant_id
            )
        )
    ).one()
    revenue, cost = Decimal(revenue), Decimal(cost)
    return {
        "revenue": revenue,
        "cost": cost,
        "profit": revenue - cost,
        "transaction_count": orders,
        "total_items_sold": int(quantity),
        "profit_margin_percent": (
            float((revenue - cost) / revenue * 100) if revenue else 0
        ),
    }


def percent_change(current, previous):
    if previous == 0:
        return 0.0 if current == 0 else None
    return float((current - previous) / abs(previous) * 100)


async def hourly_sales(db, tenant_id, start):
    end = start + timedelta(days=1)
    rows = (
        await db.execute(
            select(Sale.timestamp, Sale.total_amount).where(
                Sale.tenant_id == tenant_id,
                Sale.timestamp >= start,
                Sale.timestamp < end,
            )
        )
    ).all()
    buckets = [
        {"hour": hour, "revenue": Decimal(0), "transactions": 0} for hour in range(24)
    ]
    for timestamp, amount in rows:
        bucket = buckets[as_utc(timestamp).hour]
        bucket["revenue"] += amount
        bucket["transactions"] += 1
    return [{**bucket, "revenue": float(bucket["revenue"])} for bucket in buckets]
