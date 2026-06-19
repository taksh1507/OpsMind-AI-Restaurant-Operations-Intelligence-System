"""ML Forecast Training Pipeline.

Trains an XGBRegressor model on daily restaurant sales features,
evaluates on a 14-day holdout split, prints performance and feature
importances, and serializes the model using joblib.
"""

import os
import asyncio
import argparse
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from xgboost import XGBRegressor

from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.ml.features import build_training_frame
from app.ml.eval import score_model


def encode_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Encode categorical weather conditions to integer categories.
    
    Args:
        df: Input DataFrame containing 'weather_condition' column
        
    Returns:
        DataFrame with an additional 'weather_condition_encoded' column
    """
    df_copy = df.copy()
    conditions = ["Clear", "Clouds", "Rain", "Unknown"]
    cond_map = {cond: idx for idx, cond in enumerate(conditions)}
    df_copy["weather_condition_encoded"] = df_copy["weather_condition"].map(
        lambda x: cond_map.get(x, cond_map["Unknown"])
    )
    return df_copy


async def train_model(
    csv_path: str = "tests/data/kaggle_restaurant_sales.csv",
    tenant_id: int = 1,
    session: AsyncSession = None,
    version: int = None
) -> dict:
    """Seed DB (if session not provided), build training frame, train XGBoost model, evaluate, and save.
    
    Args:
        csv_path: Path to the sales CSV dataset (only used if session is None)
        tenant_id: Restaurant tenant ID
        session: Active database session (if None, an in-memory SQLite is used and seeded)
        version: Version number to save the model under (auto-calculated if None)
    """
    if session is not None:
        print("Running feature engineering pipeline on active DB session...")
        df = await build_training_frame(tenant_id=tenant_id, session=session)
    else:
        if not os.path.exists(csv_path):
            print(f"Error: CSV file not found at: {csv_path}")
            return {}

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
        
        async with async_session() as temp_session:
            print("Seeding database with restaurant sales history...")
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
            
            print("Running feature engineering pipeline...")
            df = await build_training_frame(tenant_id=tenant_id, session=temp_session)
            
        await engine.dispose()
    
    if df.empty:
        print("Error: Feature engineering pipeline returned no data.")
        return {}

    # Apply encoding
    df = encode_weather(df)
    
    # Define features and target
    feature_cols = [
        "item_id", "lag_1", "lag_7", "lag_14", 
        "rolling_mean_7", "rolling_mean_14", 
        "day_of_week", "month", "temp_c", "weather_condition_encoded"
    ]
    
    # Holdout Split: Last 14 days per item
    train_dfs = []
    test_dfs = []
    
    items = sorted(df["item_id"].unique())
    for item_id in items:
        item_df = df[df["item_id"] == item_id].sort_values("date").reset_index(drop=True)
        train_size = len(item_df) - 14
        train_dfs.append(item_df.iloc[:train_size])
        test_dfs.append(item_df.iloc[train_size:])
        
    train_df = pd.concat(train_dfs).reset_index(drop=True)
    test_df = pd.concat(test_dfs).reset_index(drop=True)
    
    X_train = train_df[feature_cols]
    y_train = train_df["revenue"]
    X_test = test_df[feature_cols]
    y_test = test_df["revenue"]
    
    print(f"Training XGBRegressor on {len(X_train)} samples...")
    # Controlling depth and estimators for regularization on a small dataset
    model = XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.08,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Predict and evaluate
    y_pred = model.predict(X_test)
    mae, rmse = score_model(y_test.tolist(), y_pred.tolist())
    
    print("\n" + "=" * 55)
    print("              XGBOOST FORECASTER PERFORMANCE")
    print("=" * 55)
    print(f"Model MAE:          {mae:.2f} (Naive baseline ~976.71)")
    print(f"Model RMSE:         {rmse:.2f} (Naive baseline ~1347.68)")
    print("-" * 55)
    
    print("Feature Importances:")
    importances = model.feature_importances_
    for col, imp in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
        print(f"  {col:<28}: {imp:.4f}")
        
    # Serialize model using manifest_helper
    from app.ml.manifest_helper import get_next_version, update_manifest

    if version is None:
        version = get_next_version(tenant_id, "forecast")
        
    model_dir = os.path.join("models", str(tenant_id))
    os.makedirs(model_dir, exist_ok=True)
    filename = f"forecast_v{version}.pkl"
    model_path = os.path.join(model_dir, filename)
    
    # Save the model
    joblib.dump(model, model_path)
    
    # Update manifest
    update_manifest(tenant_id, "forecast", filename)
    
    print("-" * 55)
    print(f"Successfully saved trained model to: {model_path}")
    print("=" * 55 + "\n")
    
    return {
        "status": "success",
        "version": version,
        "mae": float(mae),
        "rmse": float(rmse),
        "model_path": model_path
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train forecasting model.")
    parser.add_argument(
        "--csv",
        type=str,
        default="tests/data/kaggle_restaurant_sales.csv",
        help="Path to the sales dataset CSV (default: tests/data/kaggle_restaurant_sales.csv)"
    )
    parser.add_argument(
        "--tenant",
        type=int,
        default=1,
        help="Tenant ID to save model under (default: 1)"
    )
    args = parser.parse_args()
    asyncio.run(train_model(args.csv, args.tenant))
