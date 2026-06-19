"""Unit and integration tests for the sales CSV upload API.

Verifies headers checks, row-level validation, transactional grouping,
error logging, and multi-tenant database isolation.
"""

import os
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from decimal import Decimal
import asyncio

from app.main import create_app
from app.database import get_db
from app.api.deps import get_current_user
from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.models.menu import Category, MenuItem
from app.models.customer import Customer
from app.models.sales import Sale, SaleItem


@pytest.mark.anyio
async def test_data_import_endpoints():
    """Run all tests for sales CSV upload using an overridden ASGI Test Client."""
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
    
    # Seed common test data
    async with async_session() as session:
        # Tenants
        t1 = Tenant(id=1, tenant_id="tenant-1", name="Tenant One", subscription_status=SubscriptionStatus.ACTIVE)
        t2 = Tenant(id=2, tenant_id="tenant-2", name="Tenant Two", subscription_status=SubscriptionStatus.ACTIVE)
        session.add_all([t1, t2])
        
        # Users
        u1 = User(id=1, tenant_id=1, email="user1@test.com", hashed_password="pw", role=UserRole.OWNER)
        u2 = User(id=2, tenant_id=2, email="user2@test.com", hashed_password="pw", role=UserRole.OWNER)
        session.add_all([u1, u2])
        
        # Categories
        cat1 = Category(id=1, tenant_id=1, name="Burgers")
        cat2 = Category(id=2, tenant_id=2, name="Tacos")
        session.add_all([cat1, cat2])
        
        # Menu Items
        mi1 = MenuItem(id=10, tenant_id=1, category_id=1, name="Burger", price=Decimal("15.00"), cost_price=Decimal("4.00"))
        mi2 = MenuItem(id=11, tenant_id=2, category_id=2, name="Taco", price=Decimal("8.00"), cost_price=Decimal("2.00"))
        session.add_all([mi1, mi2])
        
        # Customer
        cust = Customer(id=101, name="Test Customer", email="test@cust.com", total_spent_inr=0.0, visit_count=0)
        session.add(cust)
        
        await session.commit()

    # Define mock dependencies
    active_user = u1

    async def override_get_db():
        async with async_session() as s:
            yield s

    async def override_get_current_user():
        return active_user

    # Setup FastAPI app with overrides
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Use AsyncClient to execute requests
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        
        # --- 1. Test Valid CSV Upload (Tenant 1) ---
        csv_valid = (
            "date,item_name,quantity,unit_price,total_amount,customer_id\n"
            "2026-06-20,Burger,2,15.00,30.00,101\n"
            "2026-06-20,Burger,1,15.00,30.00,101\n"
        )
        files = {"file": ("sales_valid.csv", csv_valid, "text/csv")}
        res = await client.post("/api/v1/data/upload-sales", files=files)
        
        assert res.status_code == status.HTTP_201_CREATED
        json_res = res.json()
        assert json_res["status"] == "success"
        assert json_res["rows_inserted"] == 1  # 1 grouped Sale record
        assert json_res["items_matched"] == 2  # 2 SaleItem records
        assert len(json_res["validation_errors"]) == 0
        
        # Verify DB records
        async with async_session() as session:
            sales_db = (await session.execute(select(Sale).where(Sale.tenant_id == 1))).scalars().all()
            assert len(sales_db) == 1
            sale = sales_db[0]
            assert sale.total_amount == Decimal("30.00")
            assert sale.customer_id == 101
            
            items_db = (await session.execute(select(SaleItem).where(SaleItem.sale_id == sale.id))).scalars().all()
            assert len(items_db) == 2
            assert items_db[0].quantity == 2
            assert items_db[1].quantity == 1

        # --- 2. Test Missing Required Headers ---
        csv_missing_headers = (
            "item_name,quantity,unit_price,total_amount\n"
            "Burger,2,15.00,30.00\n"
        )
        files = {"file": ("sales_bad_headers.csv", csv_missing_headers, "text/csv")}
        res = await client.post("/api/v1/data/upload-sales", files=files)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "date" in res.json()["detail"]

        # --- 3. Test Row-Level Validation Errors ---
        csv_validation_errors = (
            "date,item_name,quantity,unit_price,total_amount,customer_id\n"
            "invalid-date,Burger,2,15.00,30.00,101\n"      # Bad Date
            "2026-06-20,UnknownItem,2,15.00,30.00,101\n"   # Unknown Item
            "2026-06-20,Burger,-3,15.00,30.00,101\n"       # Negative Qty
            "2026-06-20,Burger,2,15.00,30.00,999\n"        # Non-existent customer
        )
        files = {"file": ("sales_validation_errs.csv", csv_validation_errors, "text/csv")}
        res = await client.post("/api/v1/data/upload-sales", files=files)
        
        assert res.status_code == status.HTTP_201_CREATED
        json_res = res.json()
        assert json_res["rows_inserted"] == 0
        assert json_res["items_matched"] == 0
        errors = json_res["validation_errors"]
        assert len(errors) == 4
        
        # Verify row indices and error flags
        assert errors[0]["row"] == 1
        assert any("date" in e for e in errors[0]["errors"])
        
        assert errors[1]["row"] == 2
        assert any("Unknown menu item" in e for e in errors[1]["errors"])
        
        assert errors[2]["row"] == 3
        assert any("Quantity" in e for e in errors[2]["errors"])
        
        assert errors[3]["row"] == 4
        assert any("Customer ID" in e for e in errors[3]["errors"])

        # --- 4. Test Tenant Isolation ---
        # Switch current user to Admin Two (Tenant 2)
        active_user = u2
        
        # Admin Two tries to upload "Burger" which belongs only to Tenant 1
        csv_t1_items = (
            "date,item_name,quantity,unit_price,total_amount,customer_id\n"
            "2026-06-20,Burger,2,15.00,30.00,\n"
        )
        files = {"file": ("sales_t1_items.csv", csv_t1_items, "text/csv")}
        res = await client.post("/api/v1/data/upload-sales", files=files)
        assert res.status_code == status.HTTP_201_CREATED
        json_res = res.json()
        assert len(json_res["validation_errors"]) == 1
        assert "Unknown menu item: 'Burger'" in json_res["validation_errors"][0]["errors"][0]
        
        # Admin Two uploads valid items for Tenant 2 ("Taco")
        csv_t2_valid = (
            "date,item_name,quantity,unit_price,total_amount,customer_id\n"
            "2026-06-20,Taco,3,8.00,24.00,\n"
        )
        files = {"file": ("sales_t2_items.csv", csv_t2_valid, "text/csv")}
        res = await client.post("/api/v1/data/upload-sales", files=files)
        assert res.status_code == status.HTTP_201_CREATED
        json_res = res.json()
        assert json_res["rows_inserted"] == 1
        assert len(json_res["validation_errors"]) == 0
        
        # Verify in DB that it is scoped to Tenant 2
        async with async_session() as session:
            sales_t2 = (await session.execute(select(Sale).where(Sale.tenant_id == 2))).scalars().all()
            assert len(sales_t2) == 1
            assert sales_t2[0].total_amount == Decimal("24.00")
            
            # Ensure no Tenant 1 sales were mutated/interfered
            sales_t1 = (await session.execute(select(Sale).where(Sale.tenant_id == 1))).scalars().all()
            assert len(sales_t1) == 1

    await engine.dispose()
