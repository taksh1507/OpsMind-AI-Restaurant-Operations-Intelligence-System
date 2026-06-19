"""Unit tests for customer behavioral segmentation features extraction.

Verifies correct calculation of order frequency, recency, average spend,
top categories with tie-breaks, and correct filtering of low-frequency customers.
"""

import os
import asyncio
import pytest
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.customer import Customer
from app.models.menu import Category, MenuItem
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.ml.segmentation_features import build_segmentation_features


def test_segmentation_features_empty():
    """Verify that an empty database returns an empty DataFrame with the correct columns."""
    async def run():
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
        
        async with async_session() as session:
            df = await build_segmentation_features(session, tenant_id=1)
            assert isinstance(df, pd.DataFrame)
            assert df.empty
            expected_cols = [
                "customer_id", "order_frequency", "avg_spend", "recency_days",
                "top_category", "total_items", "avg_items_per_order"
            ]
            assert list(df.columns) == expected_cols
            
        await engine.dispose()

    asyncio.run(run())


def test_segmentation_features_filtering_and_calculation():
    """Verify customer filtering (<2 orders excluded) and exact feature math."""
    async def run():
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
        
        async with async_session() as session:
            # 1. Seed Tenant
            tenant = Tenant(
                id=1,
                tenant_id="aurora-test",
                name="Aurora Test Restaurant",
                subscription_status=SubscriptionStatus.ACTIVE
            )
            session.add(tenant)
            
            # 2. Seed Categories
            cat_burgers = Category(id=1, tenant_id=1, name="Burgers")
            cat_pizza = Category(id=2, tenant_id=1, name="Pizza")
            cat_drinks = Category(id=3, tenant_id=1, name="Beverages")
            session.add_all([cat_burgers, cat_pizza, cat_drinks])
            
            # 3. Seed Menu Items
            item_burger = MenuItem(id=10, tenant_id=1, category_id=1, name="Cheeseburger", price=Decimal("15.00"), cost_price=Decimal("4.00"))
            item_pizza = MenuItem(id=11, tenant_id=1, category_id=2, name="Pepperoni Pizza", price=Decimal("20.00"), cost_price=Decimal("5.00"))
            item_coke = MenuItem(id=12, tenant_id=1, category_id=3, name="Coke", price=Decimal("3.00"), cost_price=Decimal("0.50"))
            session.add_all([item_burger, item_pizza, item_coke])
            
            # 4. Seed Customers
            # Customer A: 2 orders (included)
            cust_a = Customer(id=101, name="Customer A", email="a@test.com", total_spent_inr=0.0, visit_count=0)
            # Customer B: 3 orders (included)
            cust_b = Customer(id=102, name="Customer B", email="b@test.com", total_spent_inr=0.0, visit_count=0)
            # Customer C: 1 order (should be filtered out)
            cust_c = Customer(id=103, name="Customer C", email="c@test.com", total_spent_inr=0.0, visit_count=0)
            session.add_all([cust_a, cust_b, cust_c])
            
            await session.commit()
            
            # Use a fixed reference date for deterministic testing
            ref_date = datetime(2026, 6, 20, 12, 0, 0)
            
            # 5. Seed Sales & SaleItems
            
            # Customer A:
            # Order 1: 1 day ago. total_amount = 30.00 (2 Burgers)
            sale_a1 = Sale(
                tenant_id=1, customer_id=101, total_amount=Decimal("30.00"),
                payment_method=PaymentMethod.CASH, timestamp=ref_date - timedelta(days=1)
            )
            session.add(sale_a1)
            await session.flush()
            item_a1 = SaleItem(tenant_id=1, sale_id=sale_a1.id, menu_item_id=10, quantity=2, unit_price_at_sale=Decimal("15.00"))
            session.add(item_a1)
            
            # Order 2: 10 days ago. total_amount = 23.00 (1 Pizza, 1 Coke)
            sale_a2 = Sale(
                tenant_id=1, customer_id=101, total_amount=Decimal("23.00"),
                payment_method=PaymentMethod.CARD, timestamp=ref_date - timedelta(days=10)
            )
            session.add(sale_a2)
            await session.flush()
            item_a2_1 = SaleItem(tenant_id=1, sale_id=sale_a2.id, menu_item_id=11, quantity=1, unit_price_at_sale=Decimal("20.00"))
            item_a2_2 = SaleItem(tenant_id=1, sale_id=sale_a2.id, menu_item_id=12, quantity=1, unit_price_at_sale=Decimal("3.00"))
            session.add_all([item_a2_1, item_a2_2])
            
            # Customer B:
            # Order 1: 5 days ago. total_amount = 60.00 (3 Pizzas)
            sale_b1 = Sale(
                tenant_id=1, customer_id=102, total_amount=Decimal("60.00"),
                payment_method=PaymentMethod.CARD, timestamp=ref_date - timedelta(days=5)
            )
            session.add(sale_b1)
            await session.flush()
            item_b1 = SaleItem(tenant_id=1, sale_id=sale_b1.id, menu_item_id=11, quantity=3, unit_price_at_sale=Decimal("20.00"))
            session.add(item_b1)
            
            # Order 2: 95 days ago (outside 90-day frequency window). total_amount = 40.00 (2 Pizzas)
            sale_b2 = Sale(
                tenant_id=1, customer_id=102, total_amount=Decimal("40.00"),
                payment_method=PaymentMethod.CASH, timestamp=ref_date - timedelta(days=95)
            )
            session.add(sale_b2)
            await session.flush()
            item_b2 = SaleItem(tenant_id=1, sale_id=sale_b2.id, menu_item_id=11, quantity=2, unit_price_at_sale=Decimal("20.00"))
            session.add(item_b2)
            
            # Order 3: 100 days ago. total_amount = 20.00 (1 Pizza)
            sale_b3 = Sale(
                tenant_id=1, customer_id=102, total_amount=Decimal("20.00"),
                payment_method=PaymentMethod.CASH, timestamp=ref_date - timedelta(days=100)
            )
            session.add(sale_b3)
            await session.flush()
            item_b3 = SaleItem(tenant_id=1, sale_id=sale_b3.id, menu_item_id=11, quantity=1, unit_price_at_sale=Decimal("20.00"))
            session.add(item_b3)
            
            # Customer C:
            # Order 1: 2 days ago. total_amount = 15.00 (1 Burger)
            sale_c1 = Sale(
                tenant_id=1, customer_id=103, total_amount=Decimal("15.00"),
                payment_method=PaymentMethod.CASH, timestamp=ref_date - timedelta(days=2)
            )
            session.add(sale_c1)
            await session.flush()
            item_c1 = SaleItem(tenant_id=1, sale_id=sale_c1.id, menu_item_id=10, quantity=1, unit_price_at_sale=Decimal("15.00"))
            session.add(item_c1)
            
            await session.commit()
            
            # 6. Execute features extraction
            df = await build_segmentation_features(session, tenant_id=1, reference_date=ref_date)
            
            # 7. Assertions
            assert isinstance(df, pd.DataFrame)
            # Customer C should be excluded because they only have 1 order
            assert len(df) == 2
            assert set(df["customer_id"].unique()) == {101, 102}
            
            # Verify Customer A (ID 101) features:
            # order_frequency (last 90 days) = 2 (1 day ago, 10 days ago)
            # avg_spend = (30 + 23) / 2 = 26.5
            # recency_days = 1.0 (last order was 1 day ago)
            # total_items = 2 (burgers) + 1 (pizza) + 1 (coke) = 4
            # avg_items_per_order = 4 / 2 = 2.0
            # top_category = "Burgers" (qty: Burgers=2, Pizza=1, Beverages=1)
            row_a = df[df["customer_id"] == 101].iloc[0]
            assert row_a["order_frequency"] == 2
            assert row_a["avg_spend"] == 26.50
            assert row_a["recency_days"] == 1.0
            assert row_a["total_items"] == 4
            assert row_a["avg_items_per_order"] == 2.0
            assert row_a["top_category"] == "Burgers"
            
            # Verify Customer B (ID 102) features:
            # order_frequency (last 90 days) = 1 (only the one 5 days ago; 95 & 100 days ago are excluded)
            # avg_spend = (60 + 40 + 20) / 3 = 40.0
            # recency_days = 5.0 (last order was 5 days ago)
            # total_items = 3 + 2 + 1 = 6 (all pizzas)
            # avg_items_per_order = 6 / 3 = 2.0
            # top_category = "Pizza"
            row_b = df[df["customer_id"] == 102].iloc[0]
            assert row_b["order_frequency"] == 1
            assert row_b["avg_spend"] == 40.00
            assert row_b["recency_days"] == 5.0
            assert row_b["total_items"] == 6
            assert row_b["avg_items_per_order"] == 2.0
            assert row_b["top_category"] == "Pizza"
            
            # Verify no missing values exist
            assert df.isna().sum().sum() == 0

        await engine.dispose()

    asyncio.run(run())


def test_segmentation_features_tie_breaking():
    """Verify alphabetical tie-breaking on top_category when quantities are equal."""
    async def run():
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
        
        async with async_session() as session:
            # Seed tenant
            tenant = Tenant(id=1, tenant_id="aurora-test", name="Aurora Test", subscription_status=SubscriptionStatus.ACTIVE)
            session.add(tenant)
            
            # Seed Categories: Pizza and Burgers
            cat_burgers = Category(id=1, tenant_id=1, name="Burgers")
            cat_pizza = Category(id=2, tenant_id=1, name="Pizza")
            session.add_all([cat_burgers, cat_pizza])
            
            # Seed Menu Items
            item_burger = MenuItem(id=10, tenant_id=1, category_id=1, name="Cheeseburger", price=Decimal("15.00"), cost_price=Decimal("4.00"))
            item_pizza = MenuItem(id=11, tenant_id=1, category_id=2, name="Pepperoni Pizza", price=Decimal("20.00"), cost_price=Decimal("5.00"))
            session.add_all([item_burger, item_pizza])
            
            # Seed Customer
            cust = Customer(id=200, name="Customer Tie", email="tie@test.com", total_spent_inr=0.0, visit_count=0)
            session.add(cust)
            await session.commit()
            
            ref_date = datetime(2026, 6, 20, 12, 0, 0)
            
            # Create 2 sales with equal quantities of Burgers and Pizzas
            # Sale 1: 1 Burger
            sale1 = Sale(tenant_id=1, customer_id=200, total_amount=Decimal("15.00"), timestamp=ref_date - timedelta(days=5))
            session.add(sale1)
            await session.flush()
            session.add(SaleItem(tenant_id=1, sale_id=sale1.id, menu_item_id=10, quantity=1, unit_price_at_sale=Decimal("15.00")))
            
            # Sale 2: 1 Pizza
            sale2 = Sale(tenant_id=1, customer_id=200, total_amount=Decimal("20.00"), timestamp=ref_date - timedelta(days=2))
            session.add(sale2)
            await session.flush()
            session.add(SaleItem(tenant_id=1, sale_id=sale2.id, menu_item_id=11, quantity=1, unit_price_at_sale=Decimal("20.00")))
            
            await session.commit()
            
            # Run extraction
            df = await build_segmentation_features(session, tenant_id=1, reference_date=ref_date)
            
            # Assert Burgers comes before Pizza alphabetically
            assert len(df) == 1
            row = df.iloc[0]
            assert row["top_category"] == "Burgers"

        await engine.dispose()

    asyncio.run(run())
