from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func, text

from app.api.deps import get_current_user
from app.core.sql_dates import utc_date
from app.database import get_db
from app.main import create_app
from app.models import Tenant, User, UserRole, Sale, SaleItem, Category, MenuItem
from app.models.staff import Staff, Shift
from app.services.staffing import hourly_staffing
from app.services.analytics import (
    calculate_daily_revenue,
    get_daily_sales_trend,
    get_daily_revenue_and_cost,
)
from app.ml.features import build_training_frame

DAY = datetime(2026, 10, 20, tzinfo=timezone.utc)


@pytest.fixture
async def staffing(db_session):
    db_session.add_all(
        [
            Tenant(id=1, tenant_id="staffing-one", name="First"),
            Tenant(id=2, tenant_id="staffing-two", name="Second"),
        ]
    )
    await db_session.flush()
    owner = User(
        tenant_id=1,
        email="staffing@example.com",
        hashed_password="unused",
        role=UserRole.OWNER,
    )
    db_session.add_all(
        [
            owner,
            Staff(id=1, tenant_id=1, name="One", hourly_rate=Decimal("120")),
            Staff(id=2, tenant_id=2, name="Foreign", hourly_rate=Decimal("9999")),
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            Shift(
                staff_id=1,
                start_time=DAY - timedelta(minutes=30),
                end_time=DAY + timedelta(minutes=15),
            ),
            Shift(
                staff_id=1,
                start_time=DAY + timedelta(hours=10, minutes=30),
                end_time=DAY + timedelta(hours=11, minutes=15),
            ),
            Shift(
                staff_id=1,
                start_time=DAY + timedelta(hours=23, minutes=45),
                end_time=DAY + timedelta(days=1, minutes=30),
            ),
            Shift(staff_id=2, start_time=DAY, end_time=DAY + timedelta(days=1)),
            Shift(staff_id=1, start_time=DAY - timedelta(hours=1), end_time=DAY),
            Shift(
                staff_id=1,
                start_time=DAY + timedelta(days=1),
                end_time=DAY + timedelta(days=1, hours=1),
            ),
            Sale(
                tenant_id=1,
                timestamp=DAY + timedelta(hours=10, minutes=45),
                total_amount=Decimal("200"),
            ),
            Sale(
                tenant_id=1,
                timestamp=DAY + timedelta(days=1) - timedelta(microseconds=1),
                total_amount=Decimal("50"),
            ),
            Sale(
                tenant_id=1,
                timestamp=DAY + timedelta(days=1),
                total_amount=Decimal("1000"),
            ),
            Sale(
                tenant_id=2,
                timestamp=DAY + timedelta(hours=10),
                total_amount=Decimal("99999"),
            ),
        ]
    )
    await db_session.commit()
    app = create_app()

    async def database():
        yield db_session

    async def user():
        return owner

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = user
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client, owner


async def test_exact_hourly_overlap_costs_and_tenant_scoping(db_session, staffing):
    data = await hourly_staffing(db_session, 1, DAY)
    assert data["total_sales"] == Decimal("250")
    assert data["total_labor"] == Decimal("150")
    assert data["staff_scheduled"] == 1 and data["shifts_total"] == 3
    assert data["transactions"] == 2
    assert [data["hours"][hour]["labor_cost"] for hour in (0, 10, 11, 23)] == [
        30,
        60,
        30,
        30,
    ]
    assert data["hours"][10]["sales_amount"] == 200
    assert data["hours"][23]["sales_amount"] == 50
    assert data["hours"][10]["labor_percent_of_sales"] == 30
    assert sum(hour["staff_count"] for hour in data["hours"]) == 4


async def test_staffing_endpoint_returns_seeded_results_without_live_ai(
    db_session, staffing
):
    analysis = AsyncMock(
        return_value={
            "status": "success",
            "efficiency_analysis": {"efficiency_score": 80, "efficiency_label": "Good"},
        }
    )
    with patch("app.api.analytics.calculate_labor_efficiency", analysis):
        response = await staffing[0].get(
            "/api/v1/analytics/staffing-plan", params={"analysis_date": "2026-10-20"}
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["metrics"]["total_daily_labor"] == 150
    assert payload["metrics"]["total_daily_sales"] == 250
    assert len(payload["hourly_heatmap"]) == 24
    assert analysis.call_args.args[0]["staff_scheduled"] == 1


async def test_staffing_missing_shifts_is_helpful_404(staffing, db_session):
    db_session.add(
        Sale(
            tenant_id=1,
            timestamp=datetime(2026, 11, 1, 12, tzinfo=timezone.utc),
            total_amount=Decimal("50"),
        )
    )
    await db_session.commit()
    response = await staffing[0].get(
        "/api/v1/analytics/staffing-plan", params={"analysis_date": "2026-11-01"}
    )
    assert response.status_code == 404
    assert "Add staff shifts" in response.json()["detail"]


async def test_optional_forecast_reads_chronological_tenant_history(
    staffing, db_session
):
    db_session.add_all(
        [
            Sale(
                tenant_id=1,
                timestamp=DAY - timedelta(days=1),
                total_amount=Decimal("100"),
            ),
            Sale(
                tenant_id=1,
                timestamp=DAY - timedelta(days=2),
                total_amount=Decimal("150"),
            ),
            Sale(
                tenant_id=2,
                timestamp=DAY - timedelta(days=1),
                total_amount=Decimal("99999"),
            ),
        ]
    )
    await db_session.commit()
    with patch(
        "app.api.analytics.calculate_labor_efficiency",
        AsyncMock(return_value={"status": "success"}),
    ), patch(
        "app.api.analytics.forecast_revenue",
        AsyncMock(
            return_value={"status": "success", "forecast": {"next_day_1_revenue": 125}}
        ),
    ) as forecast:
        response = await staffing[0].get(
            "/api/v1/analytics/staffing-plan", params={"analysis_date": "2026-10-20"}
        )
    assert response.status_code == 200
    assert forecast.call_args.args[0] == {"day_0": 150.0, "day_1": 100.0}


async def test_sustainability_months_use_utc_boundaries(staffing, db_session):
    from app.models.menu import Ingredient, WasteLog, WasteReason

    ingredient = Ingredient(tenant_id=1, name="Rice", unit_cost=Decimal("10"))
    db_session.add(ingredient)
    await db_session.flush()
    db_session.add(
        WasteLog(
            ingredient_id=ingredient.id,
            timestamp=datetime(2026, 10, 1, 0, 15, tzinfo=timezone.utc),
            reason=WasteReason.EXPIRED,
            quantity_wasted=1,
            cost_lost_inr=Decimal("10"),
        )
    )
    await db_session.commit()
    if db_session.bind.dialect.name == "postgresql":
        await db_session.execute(text("SET TIME ZONE 'Pacific/Honolulu'"))
    response = await staffing[0].get(
        "/api/v1/analytics/sustainability", params={"month": 10, "year": 2026}
    )
    assert response.status_code == 200
    assert response.json()["details"] == {
        "current_month_waste_logs": 1,
        "previous_month_waste_logs": 0,
    }


@pytest.mark.parametrize(
    "query,status",
    [("analysis_date=bad", 400), ("forecast_days=0", 422), ("forecast_days=8", 422)],
)
async def test_staffing_parameter_validation(staffing, query, status):
    assert (
        await staffing[0].get("/api/v1/analytics/staffing-plan?" + query)
    ).status_code == status


async def test_staff_cannot_read_staffing_plan(staffing):
    staffing[1].role = UserRole.STAFF
    assert (await staffing[0].get("/api/v1/analytics/staffing-plan")).status_code == 403


async def test_utc_date_grouping_is_typed_and_independent_of_postgres_timezone(
    db_session, staffing
):
    if db_session.bind.dialect.name == "postgresql":
        await db_session.execute(text("SET TIME ZONE 'Pacific/Honolulu'"))
    rows = (
        await db_session.execute(
            select(utc_date(Sale.timestamp).label("day"), func.sum(Sale.total_amount))
            .where(Sale.tenant_id == 1)
            .group_by(utc_date(Sale.timestamp))
            .order_by(utc_date(Sale.timestamp))
        )
    ).all()
    assert rows == [
        (date(2026, 10, 20), Decimal("250")),
        (date(2026, 10, 21), Decimal("1000")),
    ]


async def test_daily_services_and_ml_normalize_dates(db_session, staffing):
    category = Category(tenant_id=1, name="Dates")
    db_session.add(category)
    await db_session.flush()
    item = MenuItem(
        tenant_id=1,
        category_id=category.id,
        name="Meal",
        price=Decimal("10"),
        cost_price=Decimal("2"),
    )
    db_session.add(item)
    await db_session.flush()
    now = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
        hour=0, minute=15, second=0, microsecond=0
    )
    for offset in range(16):
        sale = Sale(
            tenant_id=1,
            timestamp=now - timedelta(days=offset),
            total_amount=Decimal("20"),
        )
        db_session.add(sale)
        await db_session.flush()
        db_session.add(
            SaleItem(
                tenant_id=1,
                sale_id=sale.id,
                menu_item_id=item.id,
                quantity=2,
                unit_price_at_sale=Decimal("10"),
            )
        )
    await db_session.commit()
    if db_session.bind.dialect.name == "postgresql":
        await db_session.execute(text("SET TIME ZONE 'Pacific/Honolulu'"))
    key = now.date().isoformat()
    daily = await calculate_daily_revenue(
        db_session, 1, now - timedelta(seconds=1), now + timedelta(seconds=1)
    )
    assert daily == [{"date": key, "revenue": Decimal("20"), "transactions": 1}]
    assert (await get_daily_sales_trend(db_session, 1, 2))[key] == 20
    assert any(
        row == {"date": key, "revenue": 20.0, "cost": 4.0}
        for row in await get_daily_revenue_and_cost(db_session, 1, 2)
    )
    frame = await build_training_frame(1, db_session)
    assert frame["date"].iloc[-1].isoformat() == key
    assert type(frame["date"].iloc[-1]) is date
