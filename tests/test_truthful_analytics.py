from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from app.api.deps import get_current_user
from app.database import get_db
from app.main import create_app
from app.models import (
    Tenant,
    User,
    UserRole,
    Sale,
    SaleItem,
    Category,
    MenuItem,
    Recommendation,
)


@pytest.fixture
async def reporting(db_session):
    db_session.add_all(
        [
            Tenant(id=1, tenant_id="truth-one", name="One"),
            Tenant(id=2, tenant_id="truth-two", name="Two"),
        ]
    )
    await db_session.flush()
    owner = User(
        tenant_id=1,
        email="truth@example.com",
        hashed_password="unused",
        role=UserRole.OWNER,
    )
    db_session.add(owner)
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


async def test_empty_tenant_has_no_invented_metrics(reporting):
    client, _ = reporting
    data = (await client.get("/api/v1/analytics/summary")).json()
    assert data["currency"] == "INR"
    assert all(value == 0 for value in data["metrics"].values())
    assert data["top_selling_items"] == []
    hourly = (await client.get("/api/v1/analytics/hourly-sales")).json()["hours"]
    assert len(hourly) == 24
    assert sum(row["revenue"] + row["transactions"] for row in hourly) == 0
    counts = (await client.get("/api/v1/recommendations/summary")).json()
    assert [counts[key] for key in ("pending", "accepted", "rejected", "verified")] == [
        0,
        0,
        0,
        0,
    ]
    assert counts["model"]
    assert (await client.get("/api/v1/recommendations")).json() == []


@pytest.mark.parametrize("contents", [None, "", "naive_mae,xgb_mae,xgb_rmse\n"])
async def test_shared_or_empty_report_never_supplies_metrics(reporting, contents):
    client, _ = reporting
    Path("reports").mkdir(exist_ok=True)
    Path("reports/backtest.csv").write_text("naive_mae,xgb_mae,xgb_rmse\n999,999,999\n")
    Path("reports/2").mkdir(exist_ok=True)
    Path("reports/2/backtest.csv").write_text(
        "naive_mae,xgb_mae,xgb_rmse\n888,888,888\n"
    )
    if contents is not None:
        Path("reports/1").mkdir(exist_ok=True)
        Path("reports/1/backtest.csv").write_text(contents)
    response = await client.get("/api/v1/analytics/model-performance")
    assert response.status_code == 404
    assert "999" not in response.text and "888" not in response.text


async def test_recorded_inr_period_changes_and_hourly_boundaries(reporting, db_session):
    client, _ = reporting
    day = datetime(2026, 10, 20, tzinfo=timezone.utc)
    category = Category(tenant_id=1, name="Meals")
    db_session.add(category)
    await db_session.flush()
    item = MenuItem(
        tenant_id=1, category_id=category.id, name="Meal", price=100, cost_price=20
    )
    db_session.add(item)
    await db_session.flush()
    sales = [
        Sale(tenant_id=1, timestamp=day, total_amount=300),
        Sale(
            tenant_id=1,
            timestamp=datetime(2026, 10, 19, tzinfo=timezone.utc),
            total_amount=100,
        ),
        Sale(
            tenant_id=1,
            timestamp=datetime(2026, 10, 21, tzinfo=timezone.utc),
            total_amount=900,
        ),
        Sale(tenant_id=2, timestamp=day, total_amount=99999),
    ]
    db_session.add_all(sales)
    await db_session.flush()
    db_session.add_all(
        [
            SaleItem(
                tenant_id=1,
                sale_id=sales[0].id,
                menu_item_id=item.id,
                quantity=3,
                unit_price_at_sale=100,
            ),
            SaleItem(
                tenant_id=1,
                sale_id=sales[1].id,
                menu_item_id=item.id,
                quantity=1,
                unit_price_at_sale=100,
            ),
        ]
    )
    await db_session.commit()
    response = await client.get(
        "/api/v1/analytics/summary?start_date=2026-10-20&end_date=2026-10-20"
    )
    assert response.status_code == 200, response.text
    metrics = response.json()["metrics"]
    assert metrics["total_revenue_inr"] == 300
    assert metrics["total_profit_inr"] == 240
    assert metrics["total_items_sold"] == 3
    assert metrics["transaction_count"] == 1
    assert metrics["revenue_change"] == 200
    assert metrics["profit_change"] == 200
    assert 0 < metrics["total_revenue_usd"] < 300
    hours = (
        await client.get("/api/v1/analytics/hourly-sales?analysis_date=2026-10-20")
    ).json()["hours"]
    assert hours[0]["revenue"] == 300
    assert sum(row["transactions"] for row in hours) == 1


async def test_recommendation_counts_are_scoped_and_not_paginated(
    reporting, db_session
):
    client, owner = reporting
    db_session.add_all(
        [
            Recommendation(
                tenant_id=1, category="Menu", content="Recorded advice", impact_score=0
            )
            for _ in range(205)
        ]
    )
    db_session.add(
        Recommendation(
            tenant_id=2, category="Menu", content="Foreign advice", impact_score=0
        )
    )
    await db_session.commit()
    response = await client.get("/api/v1/recommendations/summary")
    assert response.status_code == 200, response.text
    assert response.json()["pending"] == 205
    owner.role = UserRole.STAFF
    assert (await client.get("/api/v1/recommendations/summary")).status_code == 403


@pytest.mark.parametrize(
    "url",
    [
        "/analytics/summary?start_date=bad",
        "/analytics/summary?start_date=2026-10-22&end_date=2026-10-20",
        "/analytics/hourly-sales?analysis_date=bad",
    ],
)
async def test_invalid_dates_are_client_errors(reporting, url):
    assert (await reporting[0].get("/api/v1" + url)).status_code == 400


async def test_only_own_report_is_returned(reporting):
    client, _ = reporting
    Path("reports/1").mkdir(parents=True, exist_ok=True)
    Path("reports/1/backtest.csv").write_text(
        "naive_mae,xgb_mae,xgb_rmse\n10,4,5\n20,6,7\n"
    )
    response = await client.get("/api/v1/analytics/model-performance")
    assert response.status_code == 200, response.text
    assert response.json()["naive_mae"] == 15
    assert response.json()["xgboost_mae"] == 5


def test_growth_without_previous_sales_is_unavailable():
    from app.services.sales_reporting import percent_change

    assert percent_change(Decimal(100), Decimal(0)) is None
    assert percent_change(Decimal(0), Decimal(0)) == 0


async def test_recorded_statuses_and_configured_model(reporting, db_session):
    from app.models import TenantSettings

    client, _ = reporting
    db_session.add_all(
        [
            TenantSettings(tenant_id=1, ai_model="configured-model"),
            TenantSettings(tenant_id=2, ai_model="foreign-model"),
            Recommendation(
                tenant_id=1,
                category="Menu",
                content="Accepted advice",
                impact_score=123,
                status="Accepted",
                applied_date=datetime.now(timezone.utc),
                verified_impact=0,
            ),
            Recommendation(
                tenant_id=1,
                category="Menu",
                content="Rejected advice",
                impact_score=456,
                status="Rejected",
            ),
        ]
    )
    await db_session.commit()
    response = await client.get("/api/v1/recommendations/summary")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "pending": 0,
        "accepted": 1,
        "rejected": 1,
        "verified": 1,
        "model": "configured-model",
    }
