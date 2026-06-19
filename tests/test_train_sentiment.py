"""Unit tests for the sentiment classifier training pipeline.

Verifies that the serialized model can be successfully loaded and produces correct sentiment predictions.
"""

import os
import pytest
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from app.ml.train_sentiment import train_sentiment_model


def test_sentiment_model_training_and_inference():
    """Verify that training outputs correct holdout performance and serializes inference-ready pipeline."""
    csv_path = "data/sentiment_train.csv"
    model_dir = "models"
    model_path = os.path.join(model_dir, "sentiment_v1.pkl")
    
    assert os.path.exists(csv_path), "Training dataset must exist before running tests"
    
    # Run the training script programmatically
    acc, prec, rec, f1 = train_sentiment_model(csv_path=csv_path, model_dir=model_dir)
    
    # Assert F1 constraint is met
    assert f1 >= 0.75, f"Holdout F1 score {f1:.4f} did not meet target of 0.75"
    
    # Verify model file exists
    assert os.path.exists(model_path)
    
    # Load model and verify structure
    pipeline = joblib.load(model_path)
    assert isinstance(pipeline, Pipeline)
    
    # Verify predictions on known inputs
    test_phrases = [
        "The food was absolutely delicious and the service was amazing!",
        "The pasta was cold and the waiter was very rude.",
        "Best cheeseburger I've had in years!"
    ]
    
    preds = pipeline.predict(test_phrases)
    
    # Expected predictions: positive (1), negative (0), positive (1)
    assert len(preds) == 3
    assert preds[0] == 1, f"Expected positive, got {preds[0]}"
    assert preds[1] == 0, f"Expected negative, got {preds[1]}"
    assert preds[2] == 1, f"Expected positive, got {preds[2]}"
    
    # Check shape
    import numpy as np
    assert isinstance(preds, np.ndarray)
