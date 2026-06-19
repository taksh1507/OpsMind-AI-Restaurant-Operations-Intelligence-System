"""Forecaster Evaluation and Baseline Establishment.

Provides standalone evaluation of forecasting methods against date-based holdout
splits. Defines score_model, compute_naive_baseline, and an evaluation runner.
"""

import os
import asyncio
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.ml.features import build_training_frame
from app.core.math_utils import forecast_next_values


def score_model(y_true: list[float], y_pred: list[float]) -> tuple[float, float]:
    """Calculate Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).
    
    Args:
        y_true: True revenue values
        y_pred: Predicted revenue values
        
    Returns:
        tuple of (mae, rmse)
    """
    y_t = np.array(y_true, dtype=float)
    y_p = np.array(y_pred, dtype=float)
    
    if len(y_t) == 0:
        return 0.0, 0.0
        
    mae = np.mean(np.abs(y_t - y_p))
    rmse = np.sqrt(np.mean((y_t - y_p) ** 2))
    
    return float(mae), float(rmse)


def compute_naive_baseline(df: pd.DataFrame) -> list[float]:
    """Compute naive baseline (same-day-last-week) predictions.
    
    Args:
        df: Test dataset DataFrame containing 'lag_7' column
        
    Returns:
        List of naive baseline predictions
    """
    return df["lag_7"].tolist()


async def evaluate_baselines(csv_path: str):
    """Seed DB, build features, split data, run baselines and evaluate performance.
    
    Args:
        csv_path: Path to the Kaggle sales CSV dataset
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at: {csv_path}")
        return

    print("Initializing in-memory database...")
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
        print("Seeding database with restaurant sales history...")
        # 1. Create Tenant
        tenant = Tenant(
            id=1,
            tenant_id="test-restaurant",
            name="Test Restaurant",
            subscription_status=SubscriptionStatus.ACTIVE
        )
        session.add(tenant)
        await session.commit()
        
        # 2. Parse CSV and seed sales tables
        csv_df = pd.read_csv(csv_path)
        grouped_sales = csv_df.groupby("date")
        
        for date_str, group in grouped_sales:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            total_amount = sum(row["quantity"] * row["unit_price"] for _, row in group.iterrows())
            
            sale = Sale(
                tenant_id=1,
                total_amount=Decimal(str(round(total_amount, 2))),
                tax_amount=Decimal("0.00"),
                payment_method=PaymentMethod.CASH,
                timestamp=dt
            )
            session.add(sale)
            await session.flush()
            
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
        
        print("Running feature engineering pipeline...")
        df = await build_training_frame(tenant_id=1, session=session)
        
    await engine.dispose()
    
    if df.empty:
        print("Error: Feature engineering pipeline returned no data.")
        return

    # Perform evaluation grouping by menu item
    all_y_true = []
    all_naive_preds = []
    all_lr_preds = []
    
    items = sorted(df["item_id"].unique())
    print(f"Evaluating across {len(items)} menu items over the last 14 days...")
    
    for item_id in items:
        item_df = df[df["item_id"] == item_id].sort_values("date").reset_index(drop=True)
        
        if len(item_df) <= 14:
            print(f"Warning: Item {item_id} has only {len(item_df)} rows. Skipping.")
            continue
            
        train_size = len(item_df) - 14
        train_part = item_df.iloc[:train_size]
        test_part = item_df.iloc[train_size:]
        
        # True revenues and Naive (same-day-last-week / lag_7) predictions
        y_true = test_part["revenue"].tolist()
        naive_preds = compute_naive_baseline(test_part)
        
        # Linear Regression: rolling 1-day-ahead predictions
        lr_preds = []
        history = train_part["revenue"].tolist()
        for i in range(14):
            pred = forecast_next_values(history, periods_ahead=1)[0]
            lr_preds.append(pred)
            history.append(test_part.iloc[i]["revenue"])
            
        all_y_true.extend(y_true)
        all_naive_preds.extend(naive_preds)
        all_lr_preds.extend(lr_preds)
        
    # Calculate global scores
    naive_mae, naive_rmse = score_model(all_y_true, all_naive_preds)
    lr_mae, lr_rmse = score_model(all_y_true, all_lr_preds)
    
    # Print comparison table
    print("\n" + "=" * 55)
    print("              FORECASTER BASELINE EVALUATION")
    print("=" * 55)
    print(f"Dataset Source:     {csv_path}")
    print(f"Holdout Split:      Last 14 days per item")
    print(f"Total Test Samples: {len(all_y_true)} rows")
    print("-" * 55)
    print(f"{'Evaluation Method':<25} | {'MAE':<12} | {'RMSE':<12}")
    print("-" * 55)
    print(f"{'Naive (Lag 7)':<25} | {naive_mae:<12.2f} | {naive_rmse:<12.2f}")
    print(f"{'Linear Regression':<25} | {lr_mae:<12.2f} | {lr_rmse:<12.2f}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate forecasting baselines.")
    parser.add_argument(
        "--csv",
        type=str,
        default="tests/data/kaggle_restaurant_sales.csv",
        help="Path to the sales dataset CSV (default: tests/data/kaggle_restaurant_sales.csv)"
    )
    args = parser.parse_args()
    asyncio.run(evaluate_baselines(args.csv))
