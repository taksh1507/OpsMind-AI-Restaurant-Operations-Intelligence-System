"""Rebuild historical customer totals during maintenance."""

from sqlalchemy import func, select

from app.models import Customer, Sale


async def rebuild_customer_totals(db, tenant_id: int) -> int:
    """Caller owns the transaction. Locks share checkout's customer-first order."""
    customers = (
        await db.scalars(
            select(Customer)
            .where(Customer.tenant_id == tenant_id)
            .order_by(Customer.id)
            .with_for_update()
        )
    ).all()
    for customer in customers:
        visits, spending = (
            await db.execute(
                select(
                    func.count(Sale.id),
                    func.coalesce(func.sum(Sale.total_amount + Sale.tax_amount), 0),
                ).where(Sale.tenant_id == tenant_id, Sale.customer_id == customer.id)
            )
        ).one()
        customer.visit_count = visits
        customer.total_spent_inr = spending
    await db.flush()
    return len(customers)
