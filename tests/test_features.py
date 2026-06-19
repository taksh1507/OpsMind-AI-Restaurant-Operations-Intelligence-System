"""Unit and integration tests for the feature engineering pipeline.

Verifies that build_training_frame handles empty inputs, imports and groups
Kaggle-style sales datasets, computes correctly aligned lag and rolling mean
features, joins weather context, and drops initial NaN boundary rows.
"""

import os
import asyncio
import pytest
import pandas as pd
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.ml.features import build_training_frame


def test_build_training_frame_empty():
    async def run():
        # Setup in-memory SQLite database
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            future=True,
        )
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # Test that empty database returns empty dataframe with correct columns
            df = await build_training_frame(tenant_id=1, session=session)
            assert isinstance(df, pd.DataFrame)
            assert df.empty
            expected_cols = [
                "date", "item_id", "revenue", "lag_1", "lag_7", "lag_14",
                "rolling_mean_7", "rolling_mean_14", "day_of_week", "month",
                "temp_c", "weather_condition"
            ]
            assert list(df.columns) == expected_cols
            
        await engine.dispose()

    asyncio.run(run())


def test_build_training_frame_success():
    async def run():
        # Setup in-memory SQLite database
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            future=True,
        )
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            # 1. Insert Tenant
            tenant = Tenant(
                id=1,
                tenant_id="test-restaurant",
                name="Test Restaurant",
                subscription_status=SubscriptionStatus.ACTIVE
            )
            session.add(tenant)
            await session.commit()
            
            # 2. Load generated sales CSV
            csv_path = os.path.join(os.path.dirname(__file__), "data", "kaggle_restaurant_sales.csv")
            assert os.path.exists(csv_path), f"CSV not found at {csv_path}"
            
            csv_df = pd.read_csv(csv_path)
            
            # Seed sales and sale_items by grouping CSV rows by date
            grouped = csv_df.groupby("date")
            
            for date_str, group in grouped:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Calculate total amount for this day's sales
                total_amount = sum(row["quantity"] * row["unit_price"] for _, row in group.iterrows())
                
                # Create a single daily sale record
                sale = Sale(
                    tenant_id=1,
                    total_amount=Decimal(str(round(total_amount, 2))),
                    tax_amount=Decimal("0.00"),
                    payment_method=PaymentMethod.CASH,
                    timestamp=dt
                )
                session.add(sale)
                await session.flush()  # flush to populate sale.id
                
                # Create SaleItem for each row in the group
                for _, row in group.iterrows():
                    sale_item = SaleItem(
                        tenant_id=1,
                        sale_id=sale.id,
                        menu_item_id=int(row["item_id"]),
                        quantity=int(row["quantity"]),
                        unit_price_at_sale=Decimal(str(row["unit_price"]))
                    )
                    session.add(sale_item)
                    
            await session.commit()
            
            # 3. Build training frame
            df = await build_training_frame(tenant_id=1, session=session)
            
            # 4. Verify columns
            expected_cols = [
                "date", "item_id", "revenue", "lag_1", "lag_7", "lag_14",
                "rolling_mean_7", "rolling_mean_14", "day_of_week", "month",
                "temp_c", "weather_condition"
            ]
            assert list(df.columns) == expected_cols
            
            # 5. Verify no NaN values
            assert df.isna().sum().sum() == 0
            
            # 6. Verify row counts and time-series history
            # The generated dataset covers 180 days for 5 distinct menu items.
            # The first 14 days of history for each item should be dropped because of lag_14 and rolling_mean_14,
            # leaving 180 - 14 = 166 rows per item.
            # For 5 items, this should yield exactly 5 * 166 = 830 rows.
            assert len(df) == 830
            
            # Verify the items are present
            assert set(df["item_id"].unique()) == {1, 2, 3, 4, 5}
            
            # Check that day_of_week and month are correct
            first_row = df.iloc[0]
            date_val = first_row["date"]
            assert first_row["day_of_week"] == date_val.weekday()
            assert first_row["month"] == date_val.month
            
            # Check weather properties
            assert "temp_c" in df.columns
            assert "weather_condition" in df.columns
            assert not df["weather_condition"].isna().any()

        await engine.dispose()

    asyncio.run(run())

