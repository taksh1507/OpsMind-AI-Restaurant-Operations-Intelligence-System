"""Unit tests for the sentiment service routing and fallbacks.

Verifies that the sentiment service loads the local Logistic Regression model when present
and falls back to Gemini or heuristic methods when the model file is missing.
"""

import os
import pytest
import asyncio
import shutil

import app.services.sentiment_service as sentiment_service


def test_sentiment_service_both_paths():
    """Verify that predictions route to local classifier when present, and fall back when absent."""
    async def run():
        model_path = os.path.join("models", "sentiment_v1.pkl")
        backup_path = os.path.join("models", "sentiment_v1.pkl.backup")
        
        # Ensure the model exists first
        assert os.path.exists(model_path), "Pre-trained sentiment model must exist for testing"
        
        # Clear global caches to force fresh load
        sentiment_service._sentiment_model = None
        sentiment_service._model_loaded_at = None
        
        # --- 1. Test Model Present Path ---
        # The model is present, so it should run the local Logistic Regression pipeline
        res_present = await sentiment_service.predict_sentiment("The food was absolutely delicious and the service was top-notch.")
        assert res_present["model_used"] == "local_lr"
        assert res_present["label"] == "positive"
        assert res_present["score"] > 0.0
        assert res_present["confidence"] >= 50.0
        
        res_present_neg = await sentiment_service.predict_sentiment("The pasta was cold and the waiter was very rude.")
        assert res_present_neg["model_used"] == "local_lr"
        assert res_present_neg["label"] == "negative"
        assert res_present_neg["score"] < 0.0
        assert res_present_neg["confidence"] >= 50.0
        
        # --- 2. Test Model Absent Path ---
        # Move model to temporary backup location
        shutil.move(model_path, backup_path)
        
        # Clear cache again
        sentiment_service._sentiment_model = None
        sentiment_service._model_loaded_at = None
        
        try:
            # Predict with model file absent - should fallback
            res_absent = await sentiment_service.predict_sentiment("The food was absolutely delicious and the service was top-notch.")
            assert res_absent["model_used"] in ["gemini_fallback", "heuristic_fallback"]
            assert res_absent["label"] == "positive"
            assert res_absent["score"] > 0.0
            
            res_absent_neg = await sentiment_service.predict_sentiment("The pasta was cold and the waiter was very rude.")
            assert res_absent_neg["model_used"] in ["gemini_fallback", "heuristic_fallback"]
            assert res_absent_neg["label"] == "negative"
            assert res_absent_neg["score"] < 0.0
            
        finally:
            # Restore model file from backup
            shutil.move(backup_path, model_path)
            
            # Reset cache
            sentiment_service._sentiment_model = None
            sentiment_service._model_loaded_at = None

    asyncio.run(run())
