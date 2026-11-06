"""Data-entry workflows, ownership, permissions and real downstream metrics."""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_current_user
from app.database import get_db
from app.main import create_app
from app.models import Tenant, User, UserRole


@pytest.fixture
async def operations(db_session):
    db_session.add_all(
        [
            Tenant(id=1, tenant_id="ops-one", name="One"),
            Tenant(id=2, tenant_id="ops-two", name="Two"),
        ]
    )
    await db_session.flush()
    users = [
        User(
            tenant_id=i,
            email=f"ops{i}@example.com",
            hashed_password="unused",
            role=UserRole.OWNER,
        )
        for i in (1, 2)
    ]
    db_session.add_all(users)
    await db_session.commit()
    for authenticated_user in users:
        db_session.expunge(authenticated_user)
    app = create_app()
    current = [users[0]]

    async def database():
        yield db_session

    async def user():
        return current[0]

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = user
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client, current, users, app


async def post(client, resource, payload):
    response = await client.post("/api/v1/" + resource, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def enter_data(client):
    day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    category = await post(client, "categories", {"name": "Meals"})
    menu = await post(
        client,
        "menu-items",
        {
            "name": "Meal",
            "category_id": category["id"],
            "price": "100",
            "cost_price": "20",
        },
    )
    payloads = {
        "customers": {
            "name": "Customer",
            "email": "customer@example.com",
            "preferences": {"taste": "spicy"},
        },
        "ingredients": {"name": "Rice", "unit": "kg", "unit_cost": "40"},
        "staff": {"name": "Chef", "role": "chef", "hourly_rate": "120"},
    }
    rows = {key: await post(client, key, value) for key, value in payloads.items()}
    payloads.update(
        {
            "recipes": {
                "menu_item_id": menu["id"],
                "ingredient_id": rows["ingredients"]["id"],
                "quantity_used": 0.5,
            },
            "shifts": {
                "staff_id": rows["staff"]["id"],
                "start_time": day.isoformat(),
                "end_time": (day + timedelta(hours=24)).isoformat(),
            },
            "waste-logs": {
                "ingredient_id": rows["ingredients"]["id"],
                "quantity_wasted": 2,
                "reason": "Spoiled",
                "cost_lost_inr": "80",
                "timestamp": day.isoformat(),
            },
        }
    )
    for key in ("recipes", "shifts", "waste-logs"):
        rows[key] = await post(client, key, payloads[key])
    return rows, payloads, menu


@pytest.mark.parametrize(
    "resource", ["customers", "ingredients", "recipes", "staff", "shifts", "waste-logs"]
)
async def test_crud_and_cross_tenant_isolation(operations, resource):
    client, current, users, _ = operations
    rows, payloads, _ = await enter_data(client)
    row = rows[resource]
    path = f"/api/v1/{resource}/{row['id']}"
    assert (await client.get(path)).status_code == 200
    assert (await client.get("/api/v1/" + resource)).json()[0]["id"] == row["id"]
    current[0] = users[1]
    assert (await client.get("/api/v1/" + resource)).json() == []
    for method, kwargs in [
        ("get", {}),
        ("put", {"json": payloads[resource]}),
        ("delete", {}),
    ]:
        assert (await getattr(client, method)(path, **kwargs)).status_code == 404
    current[0] = users[0]
    changed = {**payloads[resource]}
    key, value = {
        "customers": ("name", "Updated"),
        "ingredients": ("unit_cost", "50"),
        "recipes": ("quantity_used", 0.25),
        "staff": ("hourly_rate", "140"),
        "shifts": ("notes", "Updated"),
        "waste-logs": ("quantity_wasted", 1),
    }[resource]
    changed[key] = value
    response = await client.put(path, json=changed)
    assert response.status_code == 200, response.text
    if key in {"unit_cost", "hourly_rate", "quantity_used", "quantity_wasted"}:
        assert Decimal(str(response.json()[key])) == Decimal(str(value))
    else:
        assert response.json()[key] == value


@pytest.mark.parametrize("resource", ["recipes", "shifts", "waste-logs"])
async def test_foreign_and_missing_parent_ids_are_indistinguishable(
    operations, resource
):
    client, current, users, _ = operations
    rows, payloads, _ = await enter_data(client)
    current[0] = users[1]
    first = await client.post("/api/v1/" + resource, json=payloads[resource])
    assert first.status_code == 404
    missing = {
        key: (999999 if key.endswith("_id") else value)
        for key, value in payloads[resource].items()
    }
    second = await client.post("/api/v1/" + resource, json=missing)
    assert second.status_code == first.status_code and second.json() == first.json()


async def test_delete_preserves_sales_and_requires_explicit_dependency_removal(
    operations,
):
    client, _, _, _ = operations
    rows, _, menu = await enter_data(client)
    sale = await post(
        client,
        "sales",
        {
            "customer_id": rows["customers"]["id"],
            "items": [{"menu_item_id": menu["id"], "quantity": 1}],
            "tax_rate": "0.05",
        },
    )
    assert (
        await client.delete(f"/api/v1/ingredients/{rows['ingredients']['id']}")
    ).status_code == 409
    assert (
        await client.delete(f"/api/v1/staff/{rows['staff']['id']}")
    ).status_code == 409
    for resource in (
        "recipes",
        "waste-logs",
        "shifts",
        "ingredients",
        "staff",
        "customers",
    ):
        path = f"/api/v1/{resource}/{rows[resource]['id']}"
        assert (await client.delete(path)).status_code == 204
        assert (await client.get(path)).status_code == 404
    stored = (await client.get(f"/api/v1/sales/{sale['id']}")).json()
    assert stored["customer_id"] is None
    assert Decimal(stored["total_amount"]) == 100


@pytest.mark.parametrize("role", [UserRole.STAFF, UserRole.MANAGER])
async def test_operational_permissions(operations, role):
    client, current, _, _ = operations
    rows, payloads, _ = await enter_data(client)
    current[0].role = role
    expected = 403 if role == UserRole.STAFF else 200
    for resource, row in rows.items():
        path = f"/api/v1/{resource}/{row['id']}"
        response = await client.put(path, json=payloads[resource])
        assert response.status_code == expected, response.text
        if role == UserRole.STAFF:
            assert (
                await client.post("/api/v1/" + resource, json=payloads[resource])
            ).status_code == 403
            assert (await client.delete(path)).status_code == 403
            if resource != "customers":
                assert (await client.get(path)).status_code == 403
                assert (await client.get("/api/v1/" + resource)).status_code == 403
    review = {"rating": 5, "comment": "Great food"}
    assert (await client.post("/api/v1/reviews", json=review)).status_code == (
        403 if role == UserRole.STAFF else 201
    )
    assert (await client.get("/api/v1/reviews")).status_code == expected


async def test_customer_sale_totals_history_conflicts_and_foreign_ids(operations):
    client, current, users, _ = operations
    rows, _, menu = await enter_data(client)
    customer_id = rows["customers"]["id"]
    payload = {
        "customer_id": customer_id,
        "items": [{"menu_item_id": menu["id"], "quantity": 2}],
        "tax_rate": "0.05",
    }
    sale = await post(client, "sales", payload)
    assert sale["customer_id"] == customer_id
    customer = (await client.get(f"/api/v1/customers/{customer_id}")).json()
    assert customer["visit_count"] == 1
    assert Decimal(customer["total_spent_inr"]) == 210
    briefing = await client.get(f"/api/v1/customers/{customer_id}/briefing")
    assert briefing.status_code == 200, briefing.text
    history = briefing.json()["order_history_sample"]
    assert history[0]["item"] == "Meal" and history[0]["quantity"] == 2
    duplicate = await client.post(
        "/api/v1/customers", json={"name": "Duplicate", "email": "CUSTOMER@example.com"}
    )
    assert duplicate.status_code == 409
    invalid = await client.post(
        "/api/v1/sales",
        json={**payload, "items": [{"menu_item_id": 99999, "quantity": 1}]},
    )
    assert invalid.status_code == 404
    assert (await client.get(f"/api/v1/customers/{customer_id}")).json()[
        "visit_count"
    ] == 1
    current[0] = users[1]
    assert (await client.post("/api/v1/sales", json=payload)).status_code == 404
    assert (
        await client.post(
            "/api/v1/customers", json={"name": "Other", "email": "customer@example.com"}
        )
    ).status_code == 201


async def test_concurrent_sales_increment_customer_atomically(operations, db_session):
    client, _, _, app = operations
    rows, _, menu = await enter_data(client)
    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def database():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = database
    payload = {
        "customer_id": rows["customers"]["id"],
        "items": [{"menu_item_id": menu["id"], "quantity": 1}],
    }
    responses = await asyncio.gather(
        *(client.post("/api/v1/sales", json=payload) for _ in range(4))
    )
    assert [r.status_code for r in responses] == [201] * 4, [r.text for r in responses]
    customer = (await client.get(f"/api/v1/customers/{rows['customers']['id']}")).json()
    assert customer["visit_count"] == 4 and Decimal(customer["total_spent_inr"]) == 400


async def test_fresh_tenant_api_data_feeds_real_analytics(operations):
    client, _, _, _ = operations
    rows, _, menu = await enter_data(client)
    await post(
        client,
        "sales",
        {
            "customer_id": rows["customers"]["id"],
            "items": [{"menu_item_id": menu["id"], "quantity": 3}],
        },
    )
    review = await post(
        client,
        "reviews",
        {"rating": 5, "comment": "Excellent delicious food", "source": "internal"},
    )
    assert review["is_processed"] and Decimal(review["sentiment_score"]) > 0
    assert len((await client.get("/api/v1/reviews")).json()) == 1
    summary = (await client.get("/api/v1/analytics/summary")).json()
    assert summary["metrics"]["total_revenue_inr"] == 300
    with patch(
        "app.api.analytics.analyze_profit_margins",
        AsyncMock(return_value={"status": "success", "analysis": {}}),
    ), patch(
        "app.api.analytics.calculate_labor_efficiency",
        AsyncMock(return_value={"status": "success", "efficiency_analysis": {}}),
    ):
        margin = await client.get("/api/v1/analytics/margin-report")
        assert margin.status_code == 200, margin.text
        assert margin.json()["menu_items"][0]["cost_of_goods"] == 20
        staffing = await client.get(
            "/api/v1/analytics/staffing-plan",
            params={"analysis_date": datetime.now(timezone.utc).date().isoformat()},
        )
        assert staffing.status_code == 200, staffing.text
        assert staffing.json()["metrics"]["total_daily_sales"] == 300
        assert staffing.json()["metrics"]["total_daily_labor"] == 2880
    reputation = await client.get("/api/v1/analytics/reputation")
    assert reputation.status_code == 200, reputation.text
    assert reputation.json()["metrics"]["total_reviews"] == 1
    assert reputation.json()["metrics"]["average_rating"] == 5
    sustainability = await client.get("/api/v1/analytics/sustainability")
    assert sustainability.status_code == 200, sustainability.text
    assert sustainability.json()["details"]["current_month_waste_logs"] == 1


@pytest.mark.parametrize(
    "resource,payload",
    [
        ("customers", {"name": " ", "email": "bad"}),
        ("ingredients", {"name": "Rice", "unit": "kg", "unit_cost": "-1"}),
        ("recipes", {"menu_item_id": 1, "ingredient_id": 1, "quantity_used": 0}),
        ("staff", {"name": "Chef", "hourly_rate": -1}),
        (
            "shifts",
            {
                "staff_id": 1,
                "start_time": "2026-10-20T10:00:00Z",
                "end_time": "2026-10-20T09:00:00Z",
            },
        ),
        (
            "shifts",
            {
                "staff_id": 1,
                "start_time": "2026-10-20T09:00:00",
                "end_time": "2026-10-20T10:00:00",
            },
        ),
        (
            "waste-logs",
            {
                "ingredient_id": 1,
                "quantity_wasted": 1,
                "reason": "Unknown",
                "cost_lost_inr": 1,
                "timestamp": "2026-10-20T00:00:00Z",
            },
        ),
        ("reviews", {"rating": 6, "comment": "Good"}),
        ("reviews", {"rating": 5, "comment": "x" * 10001}),
        ("customers", {"name": "Customer", "email": "a@example.com", "tenant_id": 2}),
    ],
)
async def test_validation_and_tenant_assignment_cannot_be_overridden(
    operations, resource, payload
):
    assert (
        await operations[0].post("/api/v1/" + resource, json=payload)
    ).status_code == 422


async def test_bounded_lists_and_review_isolation(operations):
    client, current, users, _ = operations
    await post(
        client, "reviews", {"rating": 1, "comment": "Cold food and rude service"}
    )
    current[0] = users[1]
    assert (await client.get("/api/v1/reviews")).json() == []
    for resource in (
        "customers",
        "ingredients",
        "recipes",
        "staff",
        "shifts",
        "waste-logs",
        "reviews",
    ):
        for query in ("limit=201", "offset=-1"):
            assert (
                await client.get("/api/v1/" + resource + "?" + query)
            ).status_code == 422


async def test_local_review_processing_never_calls_paid_fallback(monkeypatch):
    from app.services import sentiment_service

    monkeypatch.setattr(sentiment_service, "get_cached_sentiment_model", lambda: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("app.services.ai_agent.process_review", AsyncMock()) as paid:
        result = await sentiment_service.predict_sentiment(
            "Excellent food", allow_external=False
        )
    paid.assert_not_awaited()
    assert result["model_used"] == "heuristic_fallback" and result["score"] > 0


async def test_import_updates_customer_once_even_when_retried(operations):
    client, _, _, _ = operations
    rows, _, _ = await enter_data(client)
    customer_id = rows["customers"]["id"]
    csv = (
        "order_id,date,item_name,quantity,unit_price,total_amount,payment_method,tax_amount,customer_id\n"
        f"order-one,2026-10-20,Meal,2,100,200,upi,10,{customer_id}\n"
    )
    for _ in range(2):
        response = await client.post(
            "/api/v1/data/upload-sales", files={"file": ("sales.csv", csv, "text/csv")}
        )
        assert response.status_code == 201, response.text
    customer = (await client.get(f"/api/v1/customers/{customer_id}")).json()
    assert customer["visit_count"] == 1
    assert Decimal(customer["total_spent_inr"]) == 210


async def test_foreign_parent_reassignment_and_mixed_recipe_ownership(operations):
    client, current, users, _ = operations
    foreign, foreign_payloads, foreign_menu = await enter_data(client)
    current[0] = users[1]
    own, payloads, menu = await enter_data(client)
    for resource, field, foreign_id in (
        ("recipes", "menu_item_id", foreign_menu["id"]),
        ("recipes", "ingredient_id", foreign["ingredients"]["id"]),
        ("shifts", "staff_id", foreign["staff"]["id"]),
        ("waste-logs", "ingredient_id", foreign["ingredients"]["id"]),
    ):
        payload = {**payloads[resource], field: foreign_id}
        assert (
            await client.post("/api/v1/" + resource, json=payload)
        ).status_code == 404
        response = await client.put(
            f"/api/v1/{resource}/{own[resource]['id']}", json=payload
        )
        assert response.status_code == 404
        unchanged = (
            await client.get(f"/api/v1/{resource}/{own[resource]['id']}")
        ).json()
        assert unchanged[field] == payloads[resource][field]


async def test_customer_update_conflict_preserves_totals_and_preferences(operations):
    client, _, _, _ = operations
    rows, _, menu = await enter_data(client)
    customer_id = rows["customers"]["id"]
    await post(
        client,
        "sales",
        {
            "customer_id": customer_id,
            "items": [{"menu_item_id": menu["id"], "quantity": 1}],
        },
    )
    other = await post(
        client, "customers", {"name": "Other", "email": "other@example.com"}
    )
    assert (
        await client.put(
            f"/api/v1/customers/{other['id']}",
            json={"name": "Other", "email": "customer@example.com"},
        )
    ).status_code == 409
    updated = await client.put(
        f"/api/v1/customers/{customer_id}",
        json={
            "name": "Updated",
            "email": "new@example.com",
            "preferences": {"allergies": ["nuts"], "spice": {"level": 3}},
        },
    )
    assert updated.status_code == 200, updated.text
    assert (
        updated.json()["visit_count"] == 1
        and Decimal(updated.json()["total_spent_inr"]) == 100
    )
    assert updated.json()["preferences"]["allergies"] == ["nuts"]


async def test_registration_to_data_entry_with_real_authentication(db_session):
    app = create_app()

    async def database():
        yield db_session

    app.dependency_overrides[get_db] = database
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        assert (await client.get("/api/v1/ingredients")).status_code == 401
        registration = await client.post(
            "/api/v1/auth/register",
            json={
                "restaurant_name": "Fresh API tenant",
                "email": "fresh@example.com",
                "password": "StrongPassword123!",
            },
        )
        assert registration.status_code == 201, registration.text
        client.headers["Authorization"] = (
            "Bearer " + registration.json()["access_token"]
        )
        rows, _, menu = await enter_data(client)
        sale = await post(
            client,
            "sales",
            {
                "customer_id": rows["customers"]["id"],
                "items": [{"menu_item_id": menu["id"], "quantity": 1}],
            },
        )
        assert sale["customer_id"] == rows["customers"]["id"]
        assert (await client.get("/api/v1/analytics/summary")).json()["metrics"][
            "total_revenue_inr"
        ] == 100


def test_openapi_has_concrete_operational_request_schemas():
    schema = create_app().openapi()
    assert schema["paths"]["/api/v1/ingredients"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/IngredientInput")
    assert schema["paths"]["/api/v1/shifts/{record_id}"]["put"]["requestBody"][
        "content"
    ]["application/json"]["schema"]["$ref"].endswith("/ShiftInput")


async def test_historical_totals_rebuild_is_scoped_and_repeatable(
    operations, db_session
):
    from app.models import Customer, Sale
    from app.services.customer_totals import rebuild_customer_totals

    client, current, users, _ = operations
    customer = await post(
        client, "customers", {"name": "Legacy", "email": "legacy@example.com"}
    )
    current[0] = users[1]
    foreign = await post(
        client, "customers", {"name": "Foreign", "email": "foreign@example.com"}
    )
    db_session.add_all(
        [
            Sale(
                tenant_id=1, customer_id=customer["id"], total_amount=100, tax_amount=5
            ),
            Sale(
                tenant_id=1, customer_id=customer["id"], total_amount=200, tax_amount=10
            ),
            Sale(
                tenant_id=2, customer_id=foreign["id"], total_amount=999, tax_amount=0
            ),
        ]
    )
    await db_session.commit()
    for _ in range(2):
        assert await rebuild_customer_totals(db_session, 1) == 1
        await db_session.commit()
    own = await db_session.get(Customer, customer["id"])
    other = await db_session.get(Customer, foreign["id"])
    assert own.visit_count == 2 and own.total_spent_inr == Decimal("315")
    assert other.visit_count == 0 and other.total_spent_inr == 0


async def test_waste_metrics_normalize_weight_and_exclude_other_units(operations):
    client, _, _, _ = operations
    rows, payloads, _ = await enter_data(client)
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    previous = now.replace(day=1) - timedelta(days=1)
    grams = await post(
        client, "ingredients", {"name": "Spice", "unit": "g", "unit_cost": "0.04"}
    )
    pieces = await post(
        client, "ingredients", {"name": "Pieces", "unit": "pc", "unit_cost": "0.5"}
    )
    for ingredient_id, quantity, cost, timestamp in (
        (rows["ingredients"]["id"], 4, "160", previous),
        (grams["id"], 1000, "40", previous),
        (grams["id"], 500, "20", now),
        (pieces["id"], 100, "50", now),
    ):
        await post(
            client,
            "waste-logs",
            {
                "ingredient_id": ingredient_id,
                "quantity_wasted": quantity,
                "reason": "Spoiled",
                "cost_lost_inr": cost,
                "timestamp": timestamp.isoformat(),
            },
        )
    response = await client.get("/api/v1/analytics/sustainability")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["current_weight_wasted_kg"] == 2.5
    assert data["previous_weight_wasted_kg"] == 5
    assert data["waste_reduction_pct"] == 50
    assert data["co2_impact_kg"] == 6.25
    assert data["excluded_non_weight_logs"] == 1
    assert data["current_cost_lost_inr"] == 150
    assert data["money_saved_inr"] == 50
    changed = {**payloads["ingredients"], "unit": "pc"}
    assert (
        await client.put(
            f"/api/v1/ingredients/{rows['ingredients']['id']}", json=changed
        )
    ).status_code == 409
    assert (
        await client.get("/api/v1/analytics/sustainability?month=13")
    ).status_code == 422
