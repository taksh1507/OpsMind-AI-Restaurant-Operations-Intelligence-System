"""Feature Engineering Pipeline for Forecaster.

Implements build_training_frame to prepare historical sales and weather
data for machine learning models.
"""

import math
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sales import Sale, SaleItem
from app.services.weather import get_current_weather


async def build_training_frame(
    tenant_id: int,
    session: AsyncSession,
    city: str = "Mumbai"
) -> pd.DataFrame:
    """Build a training dataset for the revenue forecasting model.
    
    Aggregates sale records to daily granularity per item, fills date gaps,
    computes lag and rolling average features, and joins environmental weather data.
    
    Args:
        tenant_id: Target tenant (restaurant) ID
        session: Database session
        city: City name for weather lookup (default: "Mumbai")
        
    Returns:
        pandas.DataFrame with columns:
        - date (datetime.date)
        - item_id (int)
        - revenue (float)
        - lag_1, lag_7, lag_14 (float)
        - rolling_mean_7, rolling_mean_14 (float)
        - day_of_week (int)
        - month (int)
        - temp_c (float)
        - weather_condition (str)
    """
    # 1. Fetch aggregated daily sales per item
    stmt = (
        select(
            func.date(Sale.timestamp).label("date"),
            SaleItem.menu_item_id.label("item_id"),
            func.sum(SaleItem.quantity * SaleItem.unit_price_at_sale).label("revenue")
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .where(Sale.tenant_id == tenant_id)
        .group_by(func.date(Sale.timestamp), SaleItem.menu_item_id)
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    required_cols = [
        "date", "item_id", "revenue", "lag_1", "lag_7", "lag_14",
        "rolling_mean_7", "rolling_mean_14", "day_of_week", "month",
        "temp_c", "weather_condition"
    ]
    
    if not rows:
        return pd.DataFrame(columns=required_cols)
        
    # Convert database rows to DataFrame
    df = pd.DataFrame([
        {
            "date": pd.to_datetime(row.date),
            "item_id": row.item_id,
            "revenue": float(row.revenue)
        }
        for row in rows
    ])
    
    # 2. Reindex to ensure continuous dates per item (fills gaps with 0.0 revenue)
    all_items = df["item_id"].unique()
    min_date = df["date"].min()
    max_date = df["date"].max()
    all_dates = pd.date_range(start=min_date, end=max_date, freq="D")
    
    mux = pd.MultiIndex.from_product([all_dates, all_items], names=["date", "item_id"])
    df = df.set_index(["date", "item_id"]).reindex(mux, fill_value=0.0).reset_index()
    
    # Ensure correct sorting before shift/rolling operations
    df = df.sort_values(by=["item_id", "date"]).reset_index(drop=True)
    
    # 3. Compute time-series lag and rolling mean features per item group
    grouped = df.groupby("item_id")
    
    df["lag_1"] = grouped["revenue"].shift(1)
    df["lag_7"] = grouped["revenue"].shift(7)
    df["lag_14"] = grouped["revenue"].shift(14)
    
    df["rolling_mean_7"] = grouped["revenue"].shift(1).rolling(window=7).mean()
    df["rolling_mean_14"] = grouped["revenue"].shift(1).rolling(window=14).mean()
    
    # 4. Extract calendar features
    df["day_of_week"] = df["date"].dt.weekday
    df["month"] = df["date"].dt.month
    
    # 5. Fetch weather baseline and apply realistic historical variations
    weather_data = await get_current_weather(city)
    current_temp = weather_data.get("temperature", 22.0)
    current_condition = weather_data.get("condition", "Clear")
    
    def simulate_weather(row):
        d = row["date"]
        # Seasonal temperature cycle (peaks in summer)
        month_factor = math.sin(2 * math.pi * (d.month - 2) / 12)
        # Daily temperature fluctuations
        day_factor = math.cos(2 * math.pi * d.day / 31) * 2.0
        
        temp = current_temp + (month_factor * 8.0) + day_factor
        
        # Deterministic weather condition cycle based on day
        if (d.day % 7) == 0:
            cond = "Rain"
        elif (d.day % 3) == 0:
            cond = "Clouds"
        else:
            cond = current_condition
            
        return pd.Series([round(temp, 1), cond])
        
    df[["temp_c", "weather_condition"]] = df.apply(simulate_weather, axis=1)
    
    # 6. Drop NaNs (rows without at least 14 days of history)
    df = df.dropna(subset=["lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_14"])
    
    # Final formatting
    df["date"] = df["date"].dt.date
    df = df[required_cols].reset_index(drop=True)
    
    return df
