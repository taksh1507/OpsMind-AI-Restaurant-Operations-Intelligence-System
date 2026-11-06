from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import pytest

from app.main import create_app
from app.api.deps import get_current_user
from app.api.customers import get_customer_order_history
from app.database import get_db
from app.models import Tenant, User, UserRole, Customer, Category, MenuItem, Sale, SaleItem, Review, Ingredient, Recipe
from app.ml.segmentation_features import build_segmentation_features
from app.ml.sentiment_data import build_raw_dataset
from app.services.persona_engine import get_customer_persona
from app.services.margin_analysis import calculate_menu_item_cost, get_all_menu_items_with_costs


@pytest.fixture
async def tenants(db_session):
    owners = []
    for tenant_id in (1, 2):
        db_session.add(Tenant(id=tenant_id, tenant_id=f"restaurant-{tenant_id}", name=f"Restaurant {tenant_id}"))
        await db_session.flush()
        user = User(tenant_id=tenant_id, email=f"owner{tenant_id}@example.com", hashed_password="unused", role=UserRole.OWNER)
        db_session.add(user)
        owners.append(user)
        db_session.add(Customer(id=tenant_id, tenant_id=tenant_id, name=f"Private customer {tenant_id}",
                                email="same@example.com", total_spent_inr=20, visit_count=2,
                                preferences={"private_note": f"tenant-{tenant_id}"}))
        db_session.add(Category(id=tenant_id, tenant_id=tenant_id, name=f"Private category {tenant_id}"))
        await db_session.flush()
        db_session.add(MenuItem(id=tenant_id, tenant_id=tenant_id, category_id=tenant_id,
                                name=f"Private meal {tenant_id}", price=Decimal("10"), cost_price=Decimal("2")))
        db_session.add(Ingredient(id=tenant_id, tenant_id=tenant_id, name=f"Private ingredient {tenant_id}",
                                  unit="kg", unit_cost=Decimal("2") if tenant_id == 1 else Decimal("100")))
        db_session.add(Review(tenant_id=tenant_id, customer_name=f"Private reviewer {tenant_id}",
                              rating=5, comment=f"private-review-for-tenant-{tenant_id}", source="internal"))
        for days in (60, 61):
            sale = Sale(tenant_id=tenant_id, customer_id=tenant_id, total_amount=Decimal("10"),
                        timestamp=datetime.now() - timedelta(days=days))
            db_session.add(sale)
            await db_session.flush()
            db_session.add(SaleItem(tenant_id=tenant_id, sale_id=sale.id, menu_item_id=tenant_id,
                                    quantity=1, unit_price_at_sale=Decimal("10")))
    await db_session.flush()
    # Existing malformed historical references must not bypass owner checks.
    leaked_sale = Sale(tenant_id=2, customer_id=1, total_amount=Decimal("9000"), timestamp=datetime.now())
    db_session.add(leaked_sale)
    await db_session.flush()
    db_session.add(SaleItem(tenant_id=2, sale_id=leaked_sale.id, menu_item_id=2, quantity=90,
                            unit_price_at_sale=Decimal("100")))
    db_session.add_all([
        Recipe(menu_item_id=1, ingredient_id=1, quantity_used=1),
        Recipe(menu_item_id=1, ingredient_id=2, quantity_used=100),
        Recipe(menu_item_id=2, ingredient_id=2, quantity_used=1),
    ])
    await db_session.commit()
    return owners


@pytest.fixture
async def client(db_session, tenants):
    application = create_app()
    active = [tenants[0]]
    async def database():
        yield db_session
    async def user():
        return active[0]
    application.dependency_overrides[get_db] = database
    application.dependency_overrides[get_current_user] = user
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as http:
        yield http, active


@pytest.mark.parametrize("tenant_id", [1, 2])
async def test_briefing_rejects_foreign_and_missing_customers_identically(client, tenants, tenant_id):
    http, active = client
    active[0] = tenants[tenant_id - 1]
    foreign = await http.get(f"/api/v1/customers/{3 - tenant_id}/briefing")
    missing = await http.get("/api/v1/customers/9999/briefing")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
    own = await http.get(f"/api/v1/customers/{tenant_id}/briefing")
    assert own.status_code == 200
    assert own.json()["favorite_item"] == f"Private meal {tenant_id}"
    assert all(order["quantity"] == 1 for order in own.json()["order_history_sample"])


@pytest.mark.parametrize("tenant_id", [1, 2])
async def test_import_does_not_reveal_foreign_customer_existence(client, tenants, db_session, tenant_id):
    http, active = client
    active[0] = tenants[tenant_id - 1]
    async def upload(customer_id):
        csv = ("order_id,payment_method,tax_amount,date,item_name,quantity,unit_price,total_amount,customer_id\n"
               f"order-1,cash,0,2026-10-23,Private meal {tenant_id},1,10,10,{customer_id}\n")
        return await http.post("/api/v1/data/upload-sales", files={"file": ("sales.csv", csv, "text/csv")})
    foreign, missing = await upload(3 - tenant_id), await upload(9999)
    assert foreign.status_code == missing.status_code == 201
    assert foreign.json()["rows_inserted"] == missing.json()["rows_inserted"] == 0
    assert foreign.json()["validation_errors"][0]["errors"] == missing.json()["validation_errors"][0]["errors"]
    own = await upload(tenant_id)
    assert own.json()["rows_inserted"] == 1
    latest = await db_session.scalar(select(Sale).where(Sale.tenant_id == tenant_id).order_by(Sale.id.desc()))
    assert latest.customer_id == tenant_id


async def test_new_owned_customer_without_sales_has_an_empty_briefing(client, db_session):
    db_session.add(Customer(id=3, tenant_id=1, name="New", email="new@example.com"))
    await db_session.commit()
    http, _ = client
    response = await http.get("/api/v1/customers/3/briefing")
    assert response.status_code == 200
    assert response.json()["order_history_sample"] == []
    assert response.json()["ltv"] == 0


async def test_personas_and_history_ignore_other_tenant_sales(db_session, tenants):
    persona = await get_customer_persona(1, db_session, 1)
    assert persona["persona"] == "At-Risk"  # Other tenant's recent sale cannot affect recency.
    assert (await get_customer_persona(1, db_session, 2))["status"] == "error"
    assert await get_customer_order_history(1, db_session, 2) == []
    history = await get_customer_order_history(1, db_session, 1)
    assert len(history) == 2
    assert {row["item"] for row in history} == {"Private meal 1"}


@pytest.mark.parametrize("tenant_id", [1, 2])
async def test_segmentation_training_receives_only_owned_customers(db_session, tenants, client, tenant_id):
    frame = await build_segmentation_features(db_session, tenant_id)
    assert frame["customer_id"].tolist() == [tenant_id]
    assert frame.iloc[0]["avg_spend"] == 10
    assert frame.iloc[0]["total_items"] == 2
    http, active = client
    active[0] = tenants[tenant_id - 1]
    with patch("app.api.training.train_customer_segmentation", return_value={
        "version": 1, "best_k": 1, "silhouette_score": None,
    }) as train:
        response = await http.post("/api/v1/ml/retrain?model_type=segmentation")
    assert response.status_code == 200
    assert train.call_args.args[0]["customer_id"].tolist() == [tenant_id]
    assert train.call_args.args[1] == tenant_id


async def test_cross_tenant_menu_links_cannot_contribute_features(db_session, tenants):
    items = (await db_session.execute(select(SaleItem).where(SaleItem.tenant_id == 1))).scalars().all()
    for item in items:
        item.menu_item_id = 2
    await db_session.commit()
    frame = await build_segmentation_features(db_session, 1)
    assert frame.iloc[0]["total_items"] == 0
    assert frame.iloc[0]["top_category"] == "Unknown"


@pytest.mark.parametrize("tenant_id", [1, 2])
async def test_sentiment_data_reads_only_explicit_tenant_reviews(db_session, tenants, tenant_id):
    from app.ml import sentiment_data
    label = AsyncMock(return_value=("positive", 0.8))
    with patch.object(sentiment_data, "weak_label_review", label), patch.object(
        sentiment_data, "get_external_reviews", return_value=pd.DataFrame([{
            "review_text": "public review", "sentiment_label": "positive", "sentiment_score": 0.8,
        }])
    ):
        frame = await build_raw_dataset(db_session, tenant_id)
    assert set(frame["review_text"]) == {f"private-review-for-tenant-{tenant_id}", "public review"}
    label.assert_awaited_once_with(f"private-review-for-tenant-{tenant_id}")


async def test_sentiment_requires_scope_and_shared_dataset_never_opens_database(db_session):
    with pytest.raises(ValueError, match="tenant_id is required"):
        await build_raw_dataset(db_session)
    with patch("app.ml.sentiment_data.create_async_engine", side_effect=AssertionError("DB must not be opened")), patch(
        "app.ml.sentiment_data.get_external_reviews", return_value=pd.DataFrame()
    ):
        frame = await build_raw_dataset()
    assert not frame.empty
    assert not frame["review_text"].str.contains("private-review-for-tenant").any()


async def test_recipe_costs_filter_menu_and_ingredient_ownership(db_session, tenants):
    assert await calculate_menu_item_cost(db_session, 1, 1) == Decimal("2")
    assert await calculate_menu_item_cost(db_session, 2, 1) == 0
    assert await calculate_menu_item_cost(db_session, 9999, 1) == 0
    assert (await get_all_menu_items_with_costs(db_session, 1))[0]["cost_of_goods"] == 2


async def test_customer_email_unique_only_within_a_tenant(db_session, tenants):
    # Fixture already created the same email in both restaurants successfully.
    db_session.add(Customer(tenant_id=1, name="Duplicate", email="same@example.com"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


def test_private_datasets_cannot_overwrite_shared_or_other_tenant_training_data():
    from app.ml.sentiment_data import balance_and_export
    frame = pd.DataFrame([{
        "review_text": "private review", "sentiment_label": "positive", "sentiment_score": 0.8,
    }])
    frame.attrs["tenant_id"] = 1
    for destination in ("data/sentiment_train.csv", "data/2/sentiment_train.csv"):
        with pytest.raises(ValueError, match="must be exported"):
            balance_and_export(frame, destination)


def test_tenant_training_csv_cannot_be_used_for_a_shared_or_other_tenant_model():
    from app.ml.train_sentiment import train_sentiment_model
    for tenant_id in (None, 2):
        with pytest.raises(ValueError, match="matching tenant_id"):
            train_sentiment_model(csv_path="data/1/sentiment_train.csv", tenant_id=tenant_id)


def test_tenant_sentiment_models_are_written_only_to_tenant_directory():
    from pathlib import Path
    from app.ml.sentiment_data import balance_and_export
    from app.ml.train_sentiment import train_sentiment_model
    frame = pd.read_csv("data/sentiment_train.csv")
    frame.attrs["tenant_id"] = 1
    exported = balance_and_export(frame, "data/1/sentiment_train.csv")
    assert exported.attrs["tenant_id"] == 1
    shared = Path("models/sentiment_v1.pkl")
    shared.write_bytes(b"shared-model-sentinel")
    other = Path("models/2/sentiment_v1.pkl")
    other.parent.mkdir()
    other.write_bytes(b"other-tenant-sentinel")
    train_sentiment_model(csv_path="data/1/sentiment_train.csv", tenant_id=1)
    assert Path("models/1/sentiment_v1.pkl").exists()
    assert shared.read_bytes() == b"shared-model-sentinel"
    assert other.read_bytes() == b"other-tenant-sentinel"
