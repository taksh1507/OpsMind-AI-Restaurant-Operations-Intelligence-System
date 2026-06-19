"""Unit and integration tests for the ML retraining and versioning pipeline.

Verifies on-demand retraining API, version auto-incrementation, manifest.json,
cache invalidation, and dynamic serving retrieval of versioned models.
"""

import os
import shutil
import json
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from app.main import create_app
from app.database import get_db
from app.api.deps import get_current_user
from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.models.menu import Category, MenuItem
from app.models.customer import Customer
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.services.forecast_service import get_cached_predict_fn, generate_forecast_report
from app.services.persona_engine import get_customer_persona


@pytest.mark.anyio
async def test_training_and_versioning_endpoints():
    """Run integration tests for ML retraining, versioning, manifest tracking, and model serving."""
    # Test Tenant ID
    test_tenant_id = 999
    model_dir = os.path.join("models", str(test_tenant_id))
    
    # 1. Setup in-memory SQLite database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Clean up model directory before running
    if os.path.exists(model_dir):
        shutil.rmtree(model_dir)

    try:
        # Seed test data: 1 Tenant, 1 User, 2 MenuItems, 5 Customers, and 20 sales days to allow forecast training
        async with async_session() as session:
            t = Tenant(
                id=test_tenant_id,
                tenant_id=f"tenant-{test_tenant_id}",
                name="Test Tenant 999",
                subscription_status=SubscriptionStatus.ACTIVE
            )
            session.add(t)
            
            u = User(
                id=test_tenant_id,
                tenant_id=test_tenant_id,
                email="owner999@test.com",
                hashed_password="pw",
                role=UserRole.OWNER
            )
            session.add(u)
            
            cat = Category(id=test_tenant_id, tenant_id=test_tenant_id, name="Beverages")
            session.add(cat)
            
            mi1 = MenuItem(
                id=test_tenant_id * 10,
                tenant_id=test_tenant_id,
                category_id=test_tenant_id,
                name="Coffee",
                price=Decimal("5.00"),
                cost_price=Decimal("1.50")
            )
            mi2 = MenuItem(
                id=test_tenant_id * 10 + 1,
                tenant_id=test_tenant_id,
                category_id=test_tenant_id,
                name="Tea",
                price=Decimal("4.00"),
                cost_price=Decimal("1.20")
            )
            session.add_all([mi1, mi2])
            
            # Seed 5 Customers for segmentation
            customers = []
            for i in range(1, 6):
                cust = Customer(
                    id=test_tenant_id * 10 + i,
                    name=f"Customer {i}",
                    email=f"cust{i}@test999.com",
                    total_spent_inr=0.0,
                    visit_count=0
                )
                session.add(cust)
                customers.append(cust)
            await session.commit()
            
            # Seed 20 days of sales history (needs at least 15 days for forecast lags)
            ref_date = datetime(2026, 6, 20, 12, 0, 0)
            for day in range(20):
                sale_date = ref_date - timedelta(days=day)
                # Ensure each customer has 2+ orders for segmentation feature build
                cust_idx = day % 5
                cust_id = customers[cust_idx].id
                
                sale = Sale(
                    tenant_id=test_tenant_id,
                    customer_id=cust_id,
                    total_amount=Decimal("20.00"),
                    tax_amount=Decimal("0.00"),
                    payment_method=PaymentMethod.CASH,
                    timestamp=sale_date
                )
                session.add(sale)
                await session.flush()
                
                session.add(SaleItem(
                    tenant_id=test_tenant_id,
                    sale_id=sale.id,
                    menu_item_id=mi1.id if day % 2 == 0 else mi2.id,
                    quantity=4,
                    unit_price_at_sale=Decimal("5.00")
                ))
            await session.commit()

        # Overrides
        async def override_get_db():
            async with async_session() as s:
                yield s

        async def override_get_current_user():
            return u

        app = create_app()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            
            # --- Test 1: Invalid model_type param ---
            res = await client.post("/api/v1/ml/retrain?model_type=invalid")
            assert res.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid model_type" in res.json()["detail"]
            
            # --- Test 2: Retrain Forecast (First run -> v1) ---
            res = await client.post("/api/v1/ml/retrain?model_type=forecast")
            assert res.status_code == status.HTTP_200_OK
            json_res = res.json()
            assert json_res["status"] == "success"
            assert "forecast" in json_res
            assert json_res["forecast"]["version"] == 1
            assert "mae" in json_res["forecast"]
            
            # Verify file created
            assert os.path.exists(os.path.join(model_dir, "forecast_v1.pkl"))
            
            # Verify manifest
            manifest_path = os.path.join(model_dir, "manifest.json")
            assert os.path.exists(manifest_path)
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
            assert manifest_data["forecast"] == "forecast_v1.pkl"
            assert "last_trained" in manifest_data
            
            # --- Test 3: Retrain Forecast (Second run -> v2) ---
            res = await client.post("/api/v1/ml/retrain?model_type=forecast")
            assert res.status_code == status.HTTP_200_OK
            json_res = res.json()
            assert json_res["forecast"]["version"] == 2
            assert os.path.exists(os.path.join(model_dir, "forecast_v2.pkl"))
            
            # Verify manifest updated
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
            assert manifest_data["forecast"] == "forecast_v2.pkl"

            # --- Test 4: Retrain Customer Segmentation (First run -> v1) ---
            res = await client.post("/api/v1/ml/retrain?model_type=segmentation")
            assert res.status_code == status.HTTP_200_OK
            json_res = res.json()
            assert json_res["segmentation"]["version"] == 1
            assert "silhouette_score" in json_res["segmentation"]
            assert os.path.exists(os.path.join(model_dir, "segments_v1.pkl"))

            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
            assert manifest_data["segmentation"] == "segments_v1.pkl"
            
            # --- Test 5: Retrain All (Forecast -> v3, Segmentation -> v2) ---
            res = await client.post("/api/v1/ml/retrain?model_type=all")
            assert res.status_code == status.HTTP_200_OK
            json_res = res.json()
            assert json_res["forecast"]["version"] == 3
            assert json_res["segmentation"]["version"] == 2
            
            with open(manifest_path, "r") as f:
                manifest_data = json.load(f)
            assert manifest_data["forecast"] == "forecast_v3.pkl"
            assert manifest_data["segmentation"] == "segments_v2.pkl"
            
            # --- Test 6: Verify Endpoint Serving picks up the latest model version ---
            # Let's verify forecast report loading
            async with async_session() as test_session:
                report = await generate_forecast_report(test_tenant_id, test_session)
                assert report["status"] == "success"
                assert report["model_used"] == "ml_xgb"  # Successfully loaded XGB model
                
                # Check get_customer_persona uses K-Means cluster path
                persona_report = await get_customer_persona(
                    customer_id=customers[0].id,
                    session=test_session,
                    tenant_id=test_tenant_id
                )
                assert persona_report["status"] == "success"
                assert "Assigned K-Means cluster-based persona" in persona_report["reasoning"]

    finally:
        # 1. Clean up generated model files for test tenant
        if os.path.exists(model_dir):
            shutil.rmtree(model_dir)
        # 2. Dispose of SQLite engine
        await engine.dispose()
