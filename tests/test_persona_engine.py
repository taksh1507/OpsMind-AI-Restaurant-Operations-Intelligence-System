"""Unit tests for the customer persona engine.

Verifies rule-based classification fallback paths, model-based predictions path,
and dynamic profile inferences.
"""

import os
import shutil
import asyncio
import pytest
import pandas as pd
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
import joblib

from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.customer import Customer
from app.models.menu import Category, MenuItem
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.ml.segmentation_features import build_segmentation_features
from app.ml.train_segmentation import train_customer_segmentation
from app.services.persona_engine import get_customer_persona, get_suggested_action_for_persona


def test_persona_engine_fallback_rules():
    """Verify that when no model is present, the engine defaults to correct rule-based classification."""
    async def run():
        # Setup in-memory SQLite database
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
            tenant = Tenant(id=1, tenant_id="aurora-test", name="Aurora Test", subscription_status=SubscriptionStatus.ACTIVE)
            session.add(tenant)
            
            # 2. Seed Customers for various rule triggers
            # VIP Regular: visit_count >= 10, total_spent >= 5000
            vip_cust = Customer(id=201, name="VIP", email="vip@test.com", total_spent_inr=5500.0, visit_count=12)
            # Big Spender: avg_spend >= 1500 or total_spent >= 8000
            spender_cust = Customer(id=202, name="Spender", email="spender@test.com", total_spent_inr=1600.0, visit_count=1)
            # New Customer: visit_count <= 1
            new_cust = Customer(id=203, name="New", email="new@test.com", total_spent_inr=100.0, visit_count=1)
            # Occasional Visitor: fallback
            occasional_cust = Customer(id=204, name="Occasional", email="occ@test.com", total_spent_inr=400.0, visit_count=2)
            
            session.add_all([vip_cust, spender_cust, new_cust, occasional_cust])
            await session.commit()
            
            # Since no model file exists, all should default to rule-based fallback
            res_vip = await get_customer_persona(201, session, tenant_id=1)
            assert res_vip["persona"] == "VIP Regular"
            assert "complimentary chef's special dessert" in res_vip["suggested_action"]
            assert "fallback" in res_vip["reasoning"]
            
            res_spender = await get_customer_persona(202, session, tenant_id=1)
            assert res_spender["persona"] == "Big Spender"
            assert "premium wine pairing" in res_spender["suggested_action"]
            
            res_new = await get_customer_persona(203, session, tenant_id=1)
            assert res_new["persona"] == "New Customer"
            assert "free appetizer" in res_new["suggested_action"]
            
            res_occ = await get_customer_persona(204, session, tenant_id=1)
            assert res_occ["persona"] == "Occasional Visitor"
            assert "loyalty program" in res_occ["suggested_action"]
            
        await engine.dispose()

    asyncio.run(run())


def test_persona_engine_model_present_path():
    """Verify that when segments_v1.pkl is present, predictions are retrieved from KMeans model."""
    async def run():
        # Setup in-memory SQLite database
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
            tenant = Tenant(id=1, tenant_id="aurora-test", name="Aurora Test", subscription_status=SubscriptionStatus.ACTIVE)
            session.add(tenant)
            
            # 2. Seed Categories
            cat_burgers = Category(id=1, tenant_id=1, name="Burgers")
            cat_pizza = Category(id=2, tenant_id=1, name="Pizza")
            session.add_all([cat_burgers, cat_pizza])
            
            # 3. Seed Menu Items
            item_burger = MenuItem(id=10, tenant_id=1, category_id=1, name="Burger", price=Decimal("15.00"), cost_price=Decimal("4.00"))
            item_pizza = MenuItem(id=11, tenant_id=1, category_id=2, name="Pizza", price=Decimal("20.00"), cost_price=Decimal("5.00"))
            session.add_all([item_burger, item_pizza])
            
            # 4. Seed 5 Customers (to allow model training)
            customers = []
            for i in range(1, 6):
                cust = Customer(id=100 + i, name=f"Customer {i}", email=f"cust{i}@test.com", total_spent_inr=2000.0, visit_count=5)
                session.add(cust)
                customers.append(cust)
            await session.commit()
            
            ref_date = datetime(2026, 6, 20, 12, 0, 0)
            
            # 5. Add 2 sales per customer to satisfy build_segmentation_features requirement
            # We vary visit counts and values to form clusters:
            # - Customer 1 & 2: Low recency, high frequency, high spend (VIP Candidates)
            # - Customer 3: High recency (At-Risk Candidate)
            # - Customer 4 & 5: Occasional patterns
            for i, cust in enumerate(customers):
                c_id = cust.id
                if i in [0, 1]:  # VIP candidates
                    recency_1 = timedelta(days=2)
                    recency_2 = timedelta(days=4)
                    amount_1 = Decimal("100.00")
                    amount_2 = Decimal("150.00")
                    qty = 5
                elif i == 2:     # At-risk candidate
                    recency_1 = timedelta(days=80)
                    recency_2 = timedelta(days=85)
                    amount_1 = Decimal("20.00")
                    amount_2 = Decimal("30.00")
                    qty = 1
                else:            # Occasionals
                    recency_1 = timedelta(days=10)
                    recency_2 = timedelta(days=15)
                    amount_1 = Decimal("30.00")
                    amount_2 = Decimal("40.00")
                    qty = 2
                
                sale1 = Sale(tenant_id=1, customer_id=c_id, total_amount=amount_1, timestamp=ref_date - recency_1)
                sale2 = Sale(tenant_id=1, customer_id=c_id, total_amount=amount_2, timestamp=ref_date - recency_2)
                session.add_all([sale1, sale2])
                await session.flush()
                
                # Add items
                session.add(SaleItem(tenant_id=1, sale_id=sale1.id, menu_item_id=10 if i % 2 == 0 else 11, quantity=qty, unit_price_at_sale=Decimal("15.00")))
                session.add(SaleItem(tenant_id=1, sale_id=sale2.id, menu_item_id=11, quantity=qty, unit_price_at_sale=Decimal("20.00")))
            
            await session.commit()
            
            # Build features
            df_features = await build_segmentation_features(session, tenant_id=1, reference_date=ref_date)
            
            # Train model in custom dir and copy segments_v1.pkl to models/1/segments_v1.pkl
            temp_model_dir = "models"
            model_subpath = os.path.join(temp_model_dir, "1", "segments_v1.pkl")
            if os.path.exists(model_subpath):
                os.remove(model_subpath)
                
            try:
                res = train_customer_segmentation(df_features, tenant_id=1, model_dir=temp_model_dir)
                assert os.path.exists(model_subpath)
                
                # Run persona prediction - should run through the K-Means path
                res_vip = await get_customer_persona(101, session, tenant_id=1)
                
                assert res_vip["status"] == "success"
                assert "cluster-based persona" in res_vip["reasoning"]
                assert res_vip["persona"] in ["VIP Regular", "At-Risk", "Occasional Visitor", "Big Spender"]
                
                # Predict for Customer 3 (At-Risk candidate, recency of 80+ days)
                res_risk = await get_customer_persona(103, session, tenant_id=1)
                assert res_risk["persona"] == "At-Risk"
                assert "15% discount coupon" in res_risk["suggested_action"]
                
            finally:
                if os.path.exists(model_subpath):
                    os.remove(model_subpath)
                    
        await engine.dispose()

    asyncio.run(run())
