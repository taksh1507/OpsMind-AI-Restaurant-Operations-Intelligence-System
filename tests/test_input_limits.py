from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, event
from sqlalchemy.ext.asyncio import async_sessionmaker
import asyncio

from app.api.deps import get_current_user
from app.database import get_db
from app.main import create_app
from app.models import Tenant, User, UserRole, Category, MenuItem, Sale, PaymentMethod


@pytest.fixture
async def api(db_session):
    tenant = Tenant(tenant_id="limits", name="Limits")
    db_session.add(tenant)
    await db_session.flush()
    owner = User(
        tenant_id=tenant.id,
        email="limits@example.com",
        hashed_password="unused",
        role=UserRole.OWNER,
    )
    category = Category(tenant_id=tenant.id, name="Meals")
    db_session.add_all([owner, category])
    await db_session.flush()
    item = MenuItem(
        tenant_id=tenant.id,
        category_id=category.id,
        name="Meal",
        price=Decimal("10"),
        cost_price=Decimal("2"),
    )
    db_session.add(item)
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
        yield client, item, app


@pytest.mark.parametrize(
    "changes",
    [
        {"items": [{"menu_item_id": 1, "quantity": 999999999}]},
        {"tax_rate": 50},
        {"tax_rate": -0.1},
        {"payment_method": "invalid"},
        {"items": [{"menu_item_id": 1, "quantity": 1}] * 101},
        {"items": []},
    ],
)
async def test_sale_limits_return_422(api, changes):
    client, item, _ = api
    payload = {"items": [{"menu_item_id": item.id, "quantity": 1}], **changes}
    assert (await client.post("/api/v1/sales", json=payload)).status_code == 422


@pytest.mark.parametrize("query", ["limit=201", "limit=0", "offset=-1"])
@pytest.mark.parametrize(
    "endpoint", ["sales", "menu-items", "categories", "users", "recommendations"]
)
async def test_sales_pagination_bounds(api, query, endpoint):
    assert (await api[0].get(f"/api/v1/{endpoint}?" + query)).status_code == 422


HEADER = "order_id,date,item_name,quantity,unit_price,total_amount,payment_method,tax_amount\n"


async def upload(client, rows, prefix=""):
    return await client.post(
        "/api/v1/data/upload-sales",
        files={"file": ("sales.csv", prefix + HEADER + rows, "text/csv")},
    )


async def test_import_distinct_orders_payment_tax_retry_and_conflict(api, db_session):
    client, _, _ = api
    row = ",2026-10-23,Meal,1,10,10,card,0.50\n"
    response = await upload(client, "a" + row + "b" + row, "\ufeff")
    assert response.status_code == 201
    assert response.json()["rows_inserted"] == 2
    repeat = (await upload(client, "b" + row + "a" + row)).json()
    assert repeat["rows_inserted"] == 0 and repeat["orders_skipped"] == 2
    conflict = (await upload(client, "a" + row.replace("card", "upi"))).json()
    assert conflict["rows_inserted"] == 0 and conflict["validation_errors"]
    sales = (await db_session.execute(select(Sale))).scalars().all()
    assert len(sales) == 2
    assert all(
        s.tax_amount == Decimal("0.50") and s.payment_method == PaymentMethod.CARD
        for s in sales
    )


async def test_invalid_row_rejects_whole_order(api):
    response = await upload(
        api[0],
        "a,2026-10-23,Meal,1,10,20,cash,0\na,2026-10-23,Meal,99999999,10,20,cash,0\n",
    )
    assert response.json()["rows_inserted"] == 0


async def test_valid_sale_boundary_and_storage_overflow(api, db_session):
    client, item, _ = api
    response = await client.post(
        "/api/v1/sales",
        json={"items": [{"menu_item_id": item.id, "quantity": 1000}], "tax_rate": 1},
    )
    assert response.status_code == 201
    assert Decimal(str(response.json()["tax_amount"])) == Decimal("10000")
    item.price = Decimal("99999999.99")
    await db_session.commit()
    response = await client.post(
        "/api/v1/sales", json={"items": [{"menu_item_id": item.id, "quantity": 1000}]}
    )
    assert response.status_code == 422


async def test_csv_item_count_boundary(api):
    for count in (100, 101):
        rows = f"order-{count},2026-10-23,Meal,1,10,{count * 10},cash,0\n" * count
        response = await upload(api[0], rows)
        assert response.status_code == 201
        assert response.json()["rows_inserted"] == (1 if count == 100 else 0)


async def test_failed_commit_rolls_back_import_receipts_and_sales(api, db_session):
    from app.models.imported_order import ImportedOrder

    with patch.object(db_session, "commit", side_effect=RuntimeError("commit failed")):
        response = await upload(api[0], "a,2026-10-23,Meal,1,10,10,cash,0\n")
    assert response.status_code == 500
    assert not (await db_session.execute(select(Sale))).scalars().all()
    assert not (await db_session.execute(select(ImportedOrder))).scalars().all()


async def test_concurrent_imports_create_only_one_sale(api, db_session):
    if db_session.bind.dialect.name != "postgresql":
        pytest.skip("Concurrent worker check runs against PostgreSQL")
    client, _, app = api
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def database():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = database
    row = "same-order,2026-10-23,Meal,1,10,10,upi,0.50\n"
    responses = await asyncio.gather(upload(client, row), upload(client, row))
    assert all(r.status_code == 201 for r in responses)
    assert sum(r.json()["rows_inserted"] for r in responses) == 1
    assert sum(r.json()["orders_skipped"] for r in responses) == 1
    assert len((await db_session.execute(select(Sale))).scalars().all()) == 1


async def test_oversized_customer_id_is_rejected_without_database_error(api):
    response = await api[0].post(
        "/api/v1/data/upload-sales",
        files={
            "file": (
                "sales.csv",
                HEADER.rstrip()
                + ",customer_id\n"
                + "a,2026-10-23,Meal,1,10,10,cash,0,9999999999999999999999999\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    assert response.json()["rows_inserted"] == 0
    assert response.json()["validation_errors"][0]["errors"] == [
        "Customer ID is invalid or unavailable"
    ]


async def test_safe_error_handler_even_when_debug_requested(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "debug", True)
    app = create_app()

    @app.get("/failure")
    async def failure():
        raise RuntimeError("private-debug-trace")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/failure")
    assert response.status_code == 500
    assert "private-debug-trace" not in response.text
    assert response.json()["correlation_id"]


@pytest.mark.parametrize(
    "payload,status",
    [
        (b"x" * (5 * 1024 * 1024 + 1), 413),
        ((HEADER + "a,2026-10-23,Meal,1,10,10,cash,0\n" * 10001).encode(), 413),
        (b"\xff\xfe", 400),
        (b"\x00binary", 400),
        (HEADER.encode(), 400),
        (b"date,item_name\n2026-10-23,Meal", 400),
    ],
    ids=["oversize", "too-many-rows", "encoding", "binary", "empty", "headers"],
)
async def test_import_file_limits_and_content(api, payload, status):
    response = await api[0].post(
        "/api/v1/data/upload-sales", files={"file": ("sales.csv", payload, "text/csv")}
    )
    assert response.status_code == status


async def test_unhandled_error_is_safe_and_correlated(api, caplog):
    client, _, app = api

    @app.get("/test-unexpected")
    async def unexpected():
        raise RuntimeError("private-gateway-url")

    response = await client.get("/test-unexpected")
    assert response.status_code == 500
    assert "private-gateway-url" not in response.text
    assert response.json()["correlation_id"] == response.headers["X-Correlation-ID"]
    assert response.json()["correlation_id"] in caplog.text


async def test_forwarded_service_error_is_safe_and_correlated(api, caplog):
    from fastapi import HTTPException

    client, _, app = api

    @app.get("/test-service-failure")
    async def failure():
        raise HTTPException(503, "private-gateway-error")

    response = await client.get("/test-service-failure")
    assert response.status_code == 503
    assert "private-gateway-error" not in response.text
    assert response.json()["correlation_id"] == response.headers["X-Correlation-ID"]
    assert response.json()["correlation_id"] in caplog.text
    assert "private-gateway-error" in caplog.text


async def test_caught_error_is_safe_and_logged(api, caplog):
    with patch(
        "app.services.sales_reporting.period_totals", new_callable=AsyncMock
    ) as calculate:
        calculate.side_effect = RuntimeError("private-gateway-url")
        response = await api[0].get("/api/v1/analytics/summary")
    assert response.status_code == 500
    assert "private-gateway-url" not in response.text
    assert response.json()["correlation_id"] == response.headers["X-Correlation-ID"]
    assert "private-gateway-url" in caplog.text


async def test_sales_relationship_loading_uses_two_queries(api, db_session):
    client, item, _ = api
    for _ in range(3):
        assert (
            await client.post(
                "/api/v1/sales",
                json={"items": [{"menu_item_id": item.id, "quantity": 1}]},
            )
        ).status_code == 201
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = db_session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        response = await client.get("/api/v1/sales")
        assert response.status_code == 200 and len(response.json()) == 3
        assert (
            len([s for s in statements if s.lstrip().upper().startswith("SELECT")]) == 2
        )
    finally:
        event.remove(engine, "before_cursor_execute", record)
