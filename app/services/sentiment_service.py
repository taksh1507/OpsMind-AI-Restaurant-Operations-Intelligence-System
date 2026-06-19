"""Sentiment Service - Model Loading, Caching, and Inference.

Provides local sentiment prediction using the trained TF-IDF + Logistic
Regression classifier, caching loaded models in-memory with a 1-hour TTL,
and falling back gracefully to Gemini or keyword heuristics if model is absent.
"""

import os
import joblib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from app.core.config import settings

# Global in-memory cache for loaded model pipeline
_sentiment_model = None
_model_loaded_at = None
_cache_ttl = timedelta(hours=1)


def load_sentiment_model():
    """Load the trained sentiment pipeline model if present.
    
    Returns:
        Pipeline or None if model doesn't exist
    """
    model_path = os.path.join("models", "sentiment_v1.pkl")
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            return model
        except Exception as e:
            print(f"Error loading sentiment model pipeline: {e}")
    return None


def get_cached_sentiment_model():
    """Retrieve the sentiment pipeline from cache, or load fresh if expired."""
    global _sentiment_model, _model_loaded_at
    now = datetime.utcnow()
    
    if _sentiment_model is not None and _model_loaded_at is not None:
        if now - _model_loaded_at < _cache_ttl:
            return _sentiment_model
            
    # Load fresh
    model = load_sentiment_model()
    if model is not None:
        _sentiment_model = model
        _model_loaded_at = now
    return _sentiment_model


def get_heuristic_sentiment(text: str) -> tuple[str, float]:
    """Analyze review comment using a local keyword rule-based system."""
    text_lower = text.lower()
    
    positive_words = {
        "delicious", "amazing", "best", "perfect", "outstanding", "great", 
        "excellent", "love", "wonderful", "friendly", "good", "fresh", 
        "incredible", "recommend", "top-notch", "nice", "fantastic", "tasty",
        "delightful", "superb", "awesome", "liked", "pleasant", "yummy"
    }
    
    negative_words = {
        "slow", "cold", "disappointed", "wrong", "bland", "worst", "unhappy", 
        "bad", "mediocre", "noise", "unbearable", "rude", "poor", "disappointing",
        "terrible", "avoid", "sick", "overcooked", "wait", "dry", "tasteless", 
        "awful", "horrible", "dirty", "salty", "stale", "slowest"
    }
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count == 0 and neg_count == 0:
        score = 0.0
    else:
        score = (pos_count - neg_count) / max(1, pos_count + neg_count)
        
    score = max(-1.0, min(1.0, round(score * 0.8, 2)))
    
    if score >= 0.3:
        label = "positive"
    elif score <= -0.3:
        label = "negative"
    else:
        label = "neutral"
        
    return label, score


async def predict_sentiment(text: str) -> Dict[str, Any]:
    """Predict review sentiment using the local classifier, with Gemini and heuristic fallbacks.
    
    Args:
        text: Review comment text
        
    Returns:
        Dict containing label ("positive"|"negative"), confidence (float), and score (float).
    """
    model = get_cached_sentiment_model()
    if model is not None:
        try:
            # Predict probability of positive (class 1)
            proba = model.predict_proba([text])[0]
            p_pos = float(proba[1])
            
            label = "positive" if p_pos >= 0.5 else "negative"
            # Scale probability P in [0, 1] to score in [-1.0, 1.0]
            score = round(2.0 * p_pos - 1.0, 2)
            confidence = round(max(p_pos, 1.0 - p_pos) * 100.0, 2)
            
            return {
                "label": label,
                "confidence": confidence,
                "score": score,
                "model_used": "local_lr"
            }
        except Exception as e:
            print(f"Prediction failed with local model, falling back: {e}")
            
    # Fallback 1: Gemini API
    api_key = os.getenv("GEMINI_API_KEY") or (settings.gemini_api_key if hasattr(settings, "gemini_api_key") else None)
    if api_key:
        try:
            from app.services.ai_agent import process_review
            res = await process_review(text)
            if res.get("status") == "success":
                score = float(res.get("sentiment_score", 0.0))
                # Map score to label
                if score >= 0.3:
                    label = "positive"
                elif score <= -0.3:
                    label = "negative"
                else:
                    label = "neutral"
                return {
                    "label": label,
                    "confidence": 100.0,
                    "score": score,
                    "model_used": "gemini_fallback"
                }
        except Exception as e:
            print(f"Gemini fallback failed: {e}")
            
    # Fallback 2: Local keyword heuristic
    label, score = get_heuristic_sentiment(text)
    return {
        "label": label,
        "confidence": 100.0,
        "score": score,
        "model_used": "heuristic_fallback"
    }
