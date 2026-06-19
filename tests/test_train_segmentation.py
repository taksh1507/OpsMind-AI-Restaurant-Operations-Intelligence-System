"""Unit tests for the customer segmentation training pipeline.

Verifies preprocessing, K-Means hyperparameter tuning, persona assignment,
and model serialization/deserialization.
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


def test_train_customer_segmentation_success():
    """Verify that train_customer_segmentation tunes, profiles, and saves a valid PKL."""
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
            
            # 4. Seed 5 Customers (to allow k-means clustering tests up to k=4)
            customers = []
            for i in range(1, 6):
                cust = Customer(id=100 + i, name=f"Customer {i}", email=f"cust{i}@test.com", total_spent_inr=0.0, visit_count=0)
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
            assert len(df_features) == 5
            
            # Train model
            temp_model_dir = "temp_test_models"
            if os.path.exists(temp_model_dir):
                shutil.rmtree(temp_model_dir)
                
            try:
                res = train_customer_segmentation(df_features, tenant_id=1, model_dir=temp_model_dir)
                
                assert res["status"] == "success"
                assert "best_k" in res
                assert "silhouette_score" in res
                assert os.path.exists(res["model_path"])
                
                # Verify we can load the model
                model_data = joblib.load(res["model_path"])
                assert "preprocessor" in model_data
                assert "model" in model_data
                assert "cluster_to_persona" in model_data
                assert "features_cols" in model_data
                
                # Check mapping covers all clusters
                mapping = model_data["cluster_to_persona"]
                assert len(mapping) == res["best_k"]
                assert "At-Risk" in mapping.values()
                
            finally:
                if os.path.exists(temp_model_dir):
                    shutil.rmtree(temp_model_dir)
                    
        await engine.dispose()

    asyncio.run(run())


def test_train_customer_segmentation_insufficient_samples():
    """Verify train_customer_segmentation raises ValueError if there are <3 samples."""
    # Create a DataFrame with only 2 samples
    df_small = pd.DataFrame([
        {
            "customer_id": 101,
            "order_frequency": 3,
            "avg_spend": 25.0,
            "recency_days": 5.0,
            "top_category": "Pizza",
            "total_items": 4,
            "avg_items_per_order": 1.33
        },
        {
            "customer_id": 102,
            "order_frequency": 2,
            "avg_spend": 40.0,
            "recency_days": 1.0,
            "top_category": "Burgers",
            "total_items": 3,
            "avg_items_per_order": 1.5
        }
    ])
    
    with pytest.raises(ValueError, match="Not enough customers"):
        train_customer_segmentation(df_small, tenant_id=1)
