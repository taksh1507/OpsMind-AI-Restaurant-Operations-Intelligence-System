"""Unit tests for the forecasting endpoint routing and fallbacks.

Verifies that the forecast service correctly loads and predicts using the XGBoost
model when present, and falls back gracefully to the linear regression baseline
when absent.
"""

import os
import pytest
import asyncio
import pandas as pd
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.services.forecast_service import generate_forecast_report
from app.ml.train_forecast import train_model


def test_forecast_service_both_paths():
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
            # Seed Tenant 1 (will train model) and Tenant 999 (fallback)
            tenant_1 = Tenant(
                id=1,
                tenant_id="restaurant-1",
                name="Restaurant 1",
                subscription_status=SubscriptionStatus.ACTIVE
            )
            tenant_999 = Tenant(
                id=999,
                tenant_id="restaurant-999",
                name="Restaurant 999",
                subscription_status=SubscriptionStatus.ACTIVE
            )
            session.add(tenant_1)
            session.add(tenant_999)
            await session.commit()
            
            # Load Kaggle dataset
            csv_path = os.path.join("tests", "data", "kaggle_restaurant_sales.csv")
            assert os.path.exists(csv_path), f"CSV not found at {csv_path}"
            csv_df = pd.read_csv(csv_path)
            
            # Seed sales history for both tenants
            for _, row in csv_df.iterrows():
                dt = datetime.strptime(row["date"], "%Y-%m-%d")
                
                # Tenant 1
                sale_1 = Sale(
                    tenant_id=1,
                    total_amount=Decimal(str(row["quantity"] * row["unit_price"])),
                    tax_amount=Decimal("0.00"),
                    payment_method=PaymentMethod.CASH,
                    timestamp=dt
                )
                session.add(sale_1)
                await session.flush()
                
                sale_item_1 = SaleItem(
                    tenant_id=1,
                    sale_id=sale_1.id,
                    menu_item_id=int(row["item_id"]),
                    quantity=int(row["quantity"]),
                    unit_price_at_sale=Decimal(str(row["unit_price"]))
                )
                session.add(sale_item_1)
                
                # Tenant 999
                sale_999 = Sale(
                    tenant_id=999,
                    total_amount=Decimal(str(row["quantity"] * row["unit_price"])),
                    tax_amount=Decimal("0.00"),
                    payment_method=PaymentMethod.CASH,
                    timestamp=dt
                )
                session.add(sale_999)
                await session.flush()
                
                sale_item_999 = SaleItem(
                    tenant_id=999,
                    sale_id=sale_999.id,
                    menu_item_id=int(row["item_id"]),
                    quantity=int(row["quantity"]),
                    unit_price_at_sale=Decimal(str(row["unit_price"]))
                )
                session.add(sale_item_999)
                
            await session.commit()
            
            # --- 1. Test Model Absent Path (Tenant 999) ---
            # No model exists for tenant 999, so it should run the linear regression fallback
            report_999 = await generate_forecast_report(tenant_id=999, db=session)
            
            assert report_999["status"] == "success"
            assert report_999["model_used"] == "lr_fallback"
            
            forecast_999 = report_999["forecast"]
            assert forecast_999["next_day_1_revenue"] >= 0.0
            assert forecast_999["next_day_2_revenue"] >= 0.0
            assert forecast_999["next_day_3_revenue"] >= 0.0
            
            # --- 2. Test Model Present Path (Tenant 1) ---
            # Programmatically train XGBoost model for Tenant 1
            await train_model(csv_path, tenant_id=1)
            
            model_path = os.path.join("models", "1", "forecast_v1.pkl")
            assert os.path.exists(model_path), "Model must exist before calling service"
            
            # Generate forecast report - should route to ml_xgb
            report_1 = await generate_forecast_report(tenant_id=1, db=session)
            
            assert report_1["status"] == "success"
            assert report_1["model_used"] == "ml_xgb"
            
            forecast_1 = report_1["forecast"]
            assert forecast_1["next_day_1_revenue"] >= 0.0
            assert forecast_1["next_day_2_revenue"] >= 0.0
            assert forecast_1["next_day_3_revenue"] >= 0.0
            
        await engine.dispose()

    asyncio.run(run())
