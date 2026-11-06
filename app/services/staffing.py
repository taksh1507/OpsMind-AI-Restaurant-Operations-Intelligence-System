"""UTC hourly sales and exact overlap-based labor costs on SQLite/PostgreSQL."""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.time_utils import as_utc
from app.models import Sale
from app.models.staff import Shift, Staff


async def hourly_staffing(session, tenant_id, day_start):
    start = as_utc(day_start)
    end = start + timedelta(days=1)
    shifts = (
        await session.execute(
            select(Shift.start_time, Shift.end_time, Shift.staff_id, Staff.hourly_rate)
            .join(Staff, Shift.staff_id == Staff.id)
            .where(
                Staff.tenant_id == tenant_id,
                Shift.start_time < end,
                Shift.end_time > start,
                Shift.end_time > Shift.start_time,
            )
        )
    ).all()
    sales = (
        await session.execute(
            select(Sale.timestamp, Sale.total_amount).where(
                Sale.tenant_id == tenant_id,
                Sale.timestamp >= start,
                Sale.timestamp < end,
            )
        )
    ).all()
    amounts = [Decimal(0) for _ in range(24)]
    for sale in sales:
        amounts[as_utc(sale.timestamp).hour] += sale.total_amount
    hours = []
    total_labor = Decimal(0)
    for hour in range(24):
        hour_start = start + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1)
        cost, workers = Decimal(0), set()
        for shift in shifts:
            overlap_start = max(hour_start, as_utc(shift.start_time))
            overlap_end = min(hour_end, as_utc(shift.end_time))
            if overlap_end <= overlap_start:
                continue
            duration = overlap_end - overlap_start
            seconds = Decimal(duration.days * 86400 + duration.seconds) + Decimal(
                duration.microseconds
            ) / Decimal(1000000)
            cost += seconds / Decimal(3600) * shift.hourly_rate
            workers.add(shift.staff_id)
        cost = cost.quantize(Decimal("0.01"))
        total_labor += cost
        hours.append(
            {
                "hour": hour,
                "sales_amount": float(amounts[hour]),
                "labor_cost": float(cost),
                "staff_count": len(workers),
                "labor_percent_of_sales": (
                    float(cost / amounts[hour] * 100) if amounts[hour] else 0
                ),
            }
        )
    return {
        "hours": hours,
        "total_sales": sum(amounts, Decimal(0)),
        "total_labor": total_labor,
        "staff_scheduled": len({shift.staff_id for shift in shifts}),
        "shifts_total": len(shifts),
        "transactions": len(sales),
    }
