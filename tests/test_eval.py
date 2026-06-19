"""Unit tests for the evaluation metrics and baseline estimators.

Validates score_model with perfect, exact-offset, and empty inputs, and checks
compute_naive_baseline extracts features correctly.
"""

import pytest
import pandas as pd
import math
from app.ml.eval import score_model, compute_naive_baseline


def test_score_model_perfect():
    # Perfect prediction should return MAE = 0 and RMSE = 0
    y_true = [100.0, 150.0, 200.0]
    y_pred = [100.0, 150.0, 200.0]
    mae, rmse = score_model(y_true, y_pred)
    assert mae == 0.0
    assert rmse == 0.0


def test_score_model_known_offset():
    # Simple known offset test case
    y_true = [10.0, 20.0, 30.0]
    y_pred = [12.0, 18.0, 33.0]
    
    # Absolute errors: [2.0, 2.0, 3.0] -> Mean = 7/3 = 2.333...
    # Squared errors: [4.0, 4.0, 9.0] -> Mean = 17/3 = 5.666... -> RMSE = sqrt(5.666...) = 2.380...
    mae, rmse = score_model(y_true, y_pred)
    
    assert math.isclose(mae, 7.0 / 3.0, rel_tol=1e-5)
    assert math.isclose(rmse, math.sqrt(17.0 / 3.0), rel_tol=1e-5)


def test_score_model_empty():
    # Empty lists should safely return 0.0, 0.0
    mae, rmse = score_model([], [])
    assert mae == 0.0
    assert rmse == 0.0


def test_compute_naive_baseline():
    # DataFrame mock with lag_7 column
    df = pd.DataFrame({
        "lag_7": [150.0, 220.0, 190.5]
    })
    preds = compute_naive_baseline(df)
    assert preds == [150.0, 220.0, 190.5]
