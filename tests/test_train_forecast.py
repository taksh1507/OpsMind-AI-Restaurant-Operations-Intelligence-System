"""Unit tests for ML model loading and inference.

Verifies that the serialized XGBoost model file can be correctly loaded and
produces predictions of the correct dimensions and shapes.
"""

import os
import joblib
import pandas as pd
import numpy as np
import pytest
import asyncio
from app.ml.train_forecast import train_model


@pytest.fixture(scope="module")
def trained_model_path():
    model_path = os.path.join("models", "1", "forecast_v1.pkl")
    csv_path = os.path.join("tests", "data", "kaggle_restaurant_sales.csv")
    
    # Run the training script programmatically to guarantee model file exists
    asyncio.run(train_model(csv_path, tenant_id=1))
    
    assert os.path.exists(model_path), f"Model path {model_path} should exist after training"
    return model_path


def test_saved_model_load_and_predict(trained_model_path):
    # 1. Load the serialized model using joblib
    model = joblib.load(trained_model_path)
    
    # 2. Construct mock input features representing 2 samples with 10 features
    sample_data = pd.DataFrame({
        "item_id": [1, 2],
        "lag_1": [350.0, 290.0],
        "lag_7": [380.0, 310.0],
        "lag_14": [400.0, 320.0],
        "rolling_mean_7": [360.0, 300.0],
        "rolling_mean_14": [370.0, 305.0],
        "day_of_week": [4, 5],
        "month": [12, 12],
        "temp_c": [22.5, 21.0],
        "weather_condition_encoded": [0, 1]
    })
    
    # 3. Generate predictions
    predictions = model.predict(sample_data)
    
    # 4. Verify predictions shape and datatype
    assert isinstance(predictions, np.ndarray), "Predictions should be a numpy array"
    assert predictions.shape == (2,), f"Expected shape (2,), got {predictions.shape}"
    assert np.all(predictions >= 0), "All predictions should be non-negative"
