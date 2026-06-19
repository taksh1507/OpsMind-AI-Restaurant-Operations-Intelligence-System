"""Rolling-Window Backtesting Engine.

Simulates forecaster training and evaluation over multiple weekly windows
to ensure stability and prevent performance degradation over time.
Writes final report to reports/backtest.csv.
"""

import os
import asyncio
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from xgboost import XGBRegressor

from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.ml.features import build_training_frame
from app.ml.eval import score_model, compute_naive_baseline
from app.ml.train_forecast import encode_weather
from app.core.math_utils import forecast_next_values


async def run_backtest(
    csv_path: str = "tests/data/kaggle_restaurant_sales.csv",
    tenant_id: int = 1,
    num_weeks: int = 8,
    session: AsyncSession = None
) -> tuple[pd.DataFrame, float, float, bool]:
    """Perform rolling-window backtesting over the specified number of weeks.
    
    Args:
        csv_path: Path to the sales CSV dataset (only used if session is None)
        tenant_id: Target tenant ID
        num_weeks: Number of weeks to backtest (default: 8)
        session: Active database session (if None, memory SQLite is created and seeded)
        
    Returns:
        tuple of (results_df, mean_mae, std_mae, passed_stability)
    """
    if session is not None:
        print("Extracting full feature set from active DB session...")
        df = await build_training_frame(tenant_id=tenant_id, session=session)
    else:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at: {csv_path}")

        print("Initializing backtest database...")
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
        
        async with async_session() as temp_session:
            print("Seeding database...")
            tenant = Tenant(
                id=tenant_id,
                tenant_id=f"restaurant-{tenant_id}",
                name=f"Restaurant {tenant_id}",
                subscription_status=SubscriptionStatus.ACTIVE
            )
            temp_session.add(tenant)
            await temp_session.commit()
            
            csv_df = pd.read_csv(csv_path)
            grouped_sales = csv_df.groupby("date")
            
            for date_str, group in grouped_sales:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                total_amount = sum(row["quantity"] * row["unit_price"] for _, row in group.iterrows())
                
                sale = Sale(
                    tenant_id=tenant_id,
                    total_amount=Decimal(str(round(total_amount, 2))),
                    tax_amount=Decimal("0.00"),
                    payment_method=PaymentMethod.CASH,
                    timestamp=dt
                )
                temp_session.add(sale)
                await temp_session.flush()
                
                for _, row in group.iterrows():
                    sale_item = SaleItem(
                        tenant_id=tenant_id,
                        sale_id=sale.id,
                        menu_item_id=int(row["item_id"]),
                        quantity=int(row["quantity"]),
                        unit_price_at_sale=Decimal(str(row["unit_price"]))
                    )
                    temp_session.add(sale_item)
                    
            await temp_session.commit()
            
            print("Extracting full feature set...")
            df = await build_training_frame(tenant_id=tenant_id, session=temp_session)
            
        await engine.dispose()
        
    if df.empty:
        raise ValueError("Feature engineering pipeline returned no data.")

    # Encode weather conditions
    df = encode_weather(df)
    
    # Feature columns for XGBRegressor
    feature_cols = [
        "item_id", "lag_1", "lag_7", "lag_14", 
        "rolling_mean_7", "rolling_mean_14", 
        "day_of_week", "month", "temp_c", "weather_condition_encoded"
    ]
    
    # Identify unique items and chronological sorting
    df = df.sort_values(by=["item_id", "date"]).reset_index(drop=True)
    max_date = df["date"].max()
    
    backtest_records = []
    
    print(f"Starting rolling-window backtest for the last {num_weeks} weeks...")
    # Loop over each week (counting backwards: 1 is the most recent week, up to num_weeks)
    for i in range(num_weeks, 0, -1):
        # Define train/test split boundary
        start_test_date = max_date - timedelta(days=i * 7)
        end_test_date = max_date - timedelta(days=(i - 1) * 7)
        
        train_df = df[df["date"] <= start_test_date]
        test_df = df[(df["date"] > start_test_date) & (df["date"] <= end_test_date)]
        
        if train_df.empty or test_df.empty:
            print(f"Warning: Week {i} has empty train or test split. Skipping.")
            continue
            
        # Target variables
        y_test = test_df["revenue"].tolist()
        
        # 1. Naive Baseline (Lag 7)
        naive_preds = compute_naive_baseline(test_df)
        naive_mae, naive_rmse = score_model(y_test, naive_preds)
        
        # 2. Linear Regression (1-day-ahead rolling per item)
        lr_preds = []
        lr_true = []
        
        for item_id in test_df["item_id"].unique():
            item_train = train_df[train_df["item_id"] == item_id].sort_values("date")
            item_test = test_df[test_df["item_id"] == item_id].sort_values("date")
            
            history = item_train["revenue"].tolist()
            for _, row in item_test.iterrows():
                pred = forecast_next_values(history, periods_ahead=1)[0]
                lr_preds.append(pred)
                lr_true.append(row["revenue"])
                history.append(row["revenue"])
                
        lr_mae, lr_rmse = score_model(lr_true, lr_preds)
        
        # 3. XGBoost Forecaster
        X_train = train_df[feature_cols]
        y_train = train_df["revenue"]
        X_test = test_df[feature_cols]
        
        model = XGBRegressor(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.08,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        xgb_preds = model.predict(X_test).tolist()
        xgb_mae, xgb_rmse = score_model(y_test, xgb_preds)
        
        # Record results
        backtest_records.append({
            "week_idx": num_weeks - i + 1,
            "start_date": start_test_date.strftime("%Y-%m-%d"),
            "end_date": end_test_date.strftime("%Y-%m-%d"),
            "naive_mae": round(naive_mae, 2),
            "naive_rmse": round(naive_rmse, 2),
            "lr_mae": round(lr_mae, 2),
            "lr_rmse": round(lr_rmse, 2),
            "xgb_mae": round(xgb_mae, 2),
            "xgb_rmse": round(xgb_rmse, 2)
        })
        
    results_df = pd.DataFrame(backtest_records)
    
    # Calculate stability check (using standard deviation to compare scale directly with mean MAE)
    xgb_maes = results_df["xgb_mae"].values
    mean_mae = float(np.mean(xgb_maes))
    std_mae = float(np.std(xgb_maes))
    
    passed_stability = std_mae < (0.20 * mean_mae)
    
    return results_df, mean_mae, std_mae, passed_stability


def main():
    parser = argparse.ArgumentParser(description="Evaluate forecasting models using rolling-window backtesting.")
    parser.add_argument(
        "--csv",
        type=str,
        default="tests/data/kaggle_restaurant_sales.csv",
        help="Path to the sales dataset CSV (default: tests/data/kaggle_restaurant_sales.csv)"
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=8,
        help="Number of weeks to backtest (default: 8)"
    )
    args = parser.parse_args()
    
    results_df, mean_mae, std_mae, passed_stability = asyncio.run(
        run_backtest(args.csv, num_weeks=args.weeks)
    )
    
    # Print week-by-week comparison table
    print("\n" + "=" * 90)
    print("                     ROLLING-WINDOW BACKTEST REPORT")
    print("=" * 90)
    print(f"{'Week':<4} | {'Start Date':<10} | {'End Date':<10} | "
          f"{'Naive MAE':<10} | {'LR MAE':<10} | {'XGB MAE':<10} | "
          f"{'XGB RMSE':<10}")
    print("-" * 90)
    for _, row in results_df.iterrows():
        print(f"{int(row['week_idx']):<4} | {row['start_date']:<10} | {row['end_date']:<10} | "
              f"{row['naive_mae']:<10.2f} | {row['lr_mae']:<10.2f} | {row['xgb_mae']:<10.2f} | "
              f"{row['xgb_rmse']:<10.2f}")
    print("-" * 90)
    print(f"XGB MAE Mean:     {mean_mae:.2f}")
    print(f"XGB MAE Std Dev:  {std_mae:.2f}")
    ratio = std_mae / mean_mae
    print(f"Stability Ratio:  {ratio:.4f} (Threshold < 0.2000)")
    status = "PASSED" if passed_stability else "FAILED"
    print(f"Stability Check:  {status}")
    print("=" * 90)
    
    # Save output to reports/backtest.csv
    os.makedirs("reports", exist_ok=True)
    report_path = os.path.join("reports", "backtest.csv")
    results_df.to_csv(report_path, index=False)
    print(f"Saved rolling-window backtest report to: {report_path}\n")


if __name__ == "__main__":
    main()
