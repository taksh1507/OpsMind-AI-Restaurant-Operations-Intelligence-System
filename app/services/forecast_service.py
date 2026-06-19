"""Forecast Service - Model loading, Caching, and Inference.

Provides serving endpoints for the ML forecasting model (XGBoost) with 1-hour
caching and fallback to simple linear regression if no model has been trained yet.
"""

import os
import joblib
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import build_training_frame
from app.ml.train_forecast import encode_weather
from app.services.weather import get_current_weather
from app.services.analytics import get_daily_sales_trend
from app.core.math_utils import forecast_next_values, calculate_confidence_score

# In-memory model cache to prevent repeated disk reads
# Key: tenant_id (int), Value: (predict_fn, loaded_at datetime)
_model_cache = {}
_cache_ttl = timedelta(hours=1)


def load_forecast_model(tenant_id: int):
    """Load the trained forecast model for the tenant if present.
    
    Args:
        tenant_id: Restaurant ID
        
    Returns:
        Callable predict function, or None if model doesn't exist
    """
    model_path = os.path.join("models", str(tenant_id), "forecast_v1.pkl")
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            
            def predict_fn(features_df: pd.DataFrame) -> np.ndarray:
                return model.predict(features_df)
                
            return predict_fn
        except Exception as e:
            print(f"Error loading model for tenant {tenant_id}: {e}")
            return None
    return None


def get_cached_predict_fn(tenant_id: int):
    """Retrieve model predict function from cache, or load fresh if expired.
    
    Args:
        tenant_id: Restaurant ID
        
    Returns:
        Callable predict function, or None if no model is found
    """
    now = datetime.utcnow()
    if tenant_id in _model_cache:
        predict_fn, loaded_at = _model_cache[tenant_id]
        if now - loaded_at < _cache_ttl:
            return predict_fn
            
    # Load fresh
    predict_fn = load_forecast_model(tenant_id)
    if predict_fn:
        _model_cache[tenant_id] = (predict_fn, now)
    return predict_fn


async def get_forecast_weather(city: str, date_obj) -> tuple[float, int]:
    """Helper to simulate temperature and weather conditions for a future date.
    
    Reuses simulated weather logic from features.py to align features.
    """
    try:
        weather_data = await get_current_weather(city)
        current_temp = weather_data.get("temperature", 22.0)
        current_condition = weather_data.get("condition", "Clear")
    except Exception:
        current_temp = 22.0
        current_condition = "Clear"
        
    # Simulate seasonal and daily factors
    month_factor = math.sin(2 * math.pi * (date_obj.month - 2) / 12)
    day_factor = math.cos(2 * math.pi * date_obj.day / 31) * 2.0
    temp = current_temp + (month_factor * 8.0) + day_factor
    
    # Deterministic conditions
    if (date_obj.day % 7) == 0:
        cond = "Rain"
    elif (date_obj.day % 3) == 0:
        cond = "Clouds"
    else:
        cond = current_condition
        
    conditions = ["Clear", "Clouds", "Rain", "Unknown"]
    cond_map = {c: idx for idx, c in enumerate(conditions)}
    cond_encoded = cond_map.get(cond, cond_map["Unknown"])
    
    return round(temp, 1), cond_encoded


async def generate_forecast_report(tenant_id: int, db: AsyncSession, days: int = 14) -> dict:
    """Generate 3-day revenue forecast.
    
    Loads ML model (XGBoost) if present, else falls back to linear regression.
    
    Args:
        tenant_id: Restaurant ID
        db: Database session
        days: Number of historical days to analyze
        
    Returns:
        Dict structured to match analytics.py response fields
    """
    predict_fn = get_cached_predict_fn(tenant_id)
    
    # Fetch historical daily revenues totals for baseline metrics and fallback
    trend_data = await get_daily_sales_trend(db, tenant_id, days=days)
    revenue_values = list(trend_data.values()) if trend_data else []
    
    if predict_fn:
        try:
            # 1. Fetch feature training frame to extract recent values
            df = await build_training_frame(tenant_id=tenant_id, session=db)
            if not df.empty:
                df = df.sort_values(by=["item_id", "date"]).reset_index(drop=True)
                max_date = df["date"].max()
                
                # Retrieve last 14 days of revenues per item
                item_histories = {}
                for item_id in df["item_id"].unique():
                    item_df = df[df["item_id"] == item_id].sort_values("date")
                    revenues = item_df["revenue"].tolist()
                    if len(revenues) < 14:
                        revenues = [0.0] * (14 - len(revenues)) + revenues
                    else:
                        revenues = revenues[-14:]
                    item_histories[item_id] = revenues
                
                # Forecast 3 days forward recursively
                day_preds = {1: 0.0, 2: 0.0, 3: 0.0}
                for d in [1, 2, 3]:
                    future_date = max_date + timedelta(days=d)
                    temp, cond_encoded = await get_forecast_weather("Mumbai", future_date)
                    
                    for item_id, history in item_histories.items():
                        features = pd.DataFrame([{
                            "item_id": item_id,
                            "lag_1": history[-1],
                            "lag_7": history[-7],
                            "lag_14": history[-14],
                            "rolling_mean_7": sum(history[-7:]) / 7.0,
                            "rolling_mean_14": sum(history[-14:]) / 14.0,
                            "day_of_week": future_date.weekday(),
                            "month": future_date.month,
                            "temp_c": temp,
                            "weather_condition_encoded": cond_encoded
                        }])
                        
                        pred = predict_fn(features)[0]
                        pred = max(0.0, float(pred))
                        
                        # Store prediction in history for future recursive steps
                        history.append(pred)
                        day_preds[d] += pred
                
                # Compute growth metrics
                day1 = day_preds[1]
                day3 = day_preds[3]
                growth_rate = ((day3 - day1) / day1 * 100.0) if day1 > 0 else 0.0
                
                # Return ML forecast dict matching expected keys
                return {
                    "status": "success",
                    "forecast": {
                        "next_day_1_revenue": round(day_preds[1], 2),
                        "next_day_2_revenue": round(day_preds[2], 2),
                        "next_day_3_revenue": round(day_preds[3], 2),
                        "confidence_score": 85,
                        "confidence_reasoning": "The XGBoost model forecasts stable growth based on the last 14 days of item sales history.",
                        "growth_rate_percent": round(growth_rate, 2),
                        "growth_direction": "Growing" if growth_rate > 2.0 else "Declining" if growth_rate < -2.0 else "Stable",
                        "pattern_detected": "XGBoost item-level time-series patterns",
                        "risk_factors": [],
                        "business_impact": "Optimizing inventory and staffing based on XGBoost item demand forecasting.",
                        "mathematical_reasoning": "XGBoost regression using lag and rolling averages across menu items."
                    },
                    "model_used": "ml_xgb"
                }
        except Exception as e:
            print(f"XGBoost prediction failed, falling back: {e}")
            
    # Fallback to math_utils linear regression
    lr_predictions = forecast_next_values(revenue_values, periods_ahead=3)
    if len(lr_predictions) < 3:
        lr_predictions = lr_predictions + [0.0] * (3 - len(lr_predictions))
        
    day1 = lr_predictions[0]
    day3 = lr_predictions[2]
    growth_rate = ((day3 - day1) / day1 * 100.0) if day1 > 0 else 0.0
    
    return {
        "status": "success",
        "forecast": {
            "next_day_1_revenue": round(lr_predictions[0], 2),
            "next_day_2_revenue": round(lr_predictions[1], 2),
            "next_day_3_revenue": round(lr_predictions[2], 2),
            "confidence_score": 50,
            "confidence_reasoning": "Linear regression projection of recent total restaurant revenues.",
            "growth_rate_percent": round(growth_rate, 2),
            "growth_direction": "Growing" if growth_rate > 2.0 else "Declining" if growth_rate < -2.0 else "Stable",
            "pattern_detected": "Recent daily baseline totals",
            "risk_factors": [],
            "business_impact": "Plan operations according to the mathematically projected trend.",
            "mathematical_reasoning": "Simple linear regression forecast on overall daily revenues."
        },
        "model_used": "lr_fallback"
    }
