"""Unit tests for the sentiment training data preparation pipeline.

Verifies raw data generation, upsampling class balance logic, and end-to-end CSV output.
"""

import os
import pytest
import asyncio
import pandas as pd

from app.ml.sentiment_data import build_raw_dataset, balance_and_export, get_heuristic_sentiment


def test_heuristic_sentiment():
    """Verify that the keyword heuristic scores reviews properly on boundary cases."""
    p_label, p_score = get_heuristic_sentiment("The food was delicious and amazing!")
    assert p_label == "positive"
    assert p_score > 0.0
    
    n_label, n_score = get_heuristic_sentiment("The service was slow and cold.")
    assert n_label == "negative"
    assert n_score < 0.0
    
    neu_label, neu_score = get_heuristic_sentiment("The table was wooden and square.")
    assert neu_label == "neutral"
    assert neu_score == 0.0


def test_build_raw_dataset_columns():
    """Verify that build_raw_dataset outputs a DataFrame with the correct columns."""
    async def run():
        df = await build_raw_dataset()
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "review_text" in df.columns
        assert "sentiment_label" in df.columns
        assert "sentiment_score" in df.columns
        
    asyncio.run(run())


def test_balance_and_export_upsampling():
    """Test that balance_and_export upsamples minority classes in a highly skewed DataFrame."""
    # Create a deliberately skewed DataFrame: 100 positive, 2 negative, 2 neutral
    skewed_records = []
    for _ in range(100):
        skewed_records.append({
            "review_text": "Delicious pizza!",
            "sentiment_label": "positive",
            "sentiment_score": 0.8
        })
    for _ in range(2):
        skewed_records.append({
            "review_text": "Cold pizza.",
            "sentiment_label": "negative",
            "sentiment_score": -0.8
        })
    for _ in range(2):
        skewed_records.append({
            "review_text": "It is pizza.",
            "sentiment_label": "neutral",
            "sentiment_score": 0.0
        })
        
    df_skewed = pd.DataFrame(skewed_records)
    
    temp_output = "data/test_sentiment_skewed.csv"
    if os.path.exists(temp_output):
        os.remove(temp_output)
        
    try:
        # Run balance and export
        df_balanced = balance_and_export(df_skewed, output_path=temp_output)
        
        # Verify temporary file was written
        assert os.path.exists(temp_output)
        
        # Verify minimum size constraint (>=300)
        assert len(df_balanced) >= 300
        
        # Verify class balance: no single label exceeds 60%
        counts = df_balanced["sentiment_label"].value_counts().to_dict()
        total = len(df_balanced)
        for label, count in counts.items():
            ratio = count / total
            assert ratio <= 0.60, f"Class {label} exceeds 60% limit at {ratio:.2%}"
            
        # Verify that positive count remains 100, but negatives and neutrals have been upsampled
        assert counts["positive"] == 100
        assert counts["negative"] >= 67
        assert counts["neutral"] >= 67
        
    finally:
        if os.path.exists(temp_output):
            os.remove(temp_output)


def test_end_to_end_sentiment_data():
    """Run build_raw_dataset and balance_and_export to verify final CSV properties."""
    async def run():
        output_csv = "data/sentiment_train.csv"
        
        # Ensure we delete prior files if any
        if os.path.exists(output_csv):
            os.remove(output_csv)
            
        raw_df = await build_raw_dataset()
        balanced_df = balance_and_export(raw_df, output_path=output_csv)
        
        # Verify final file exists
        assert os.path.exists(output_csv)
        
        # Load from disk to verify it's written and readable
        disk_df = pd.read_csv(output_csv)
        assert len(disk_df) >= 300
        
        # Verify columns
        assert list(disk_df.columns) == ["review_text", "sentiment_label", "sentiment_score"]
        
        # Verify class balance
        counts = disk_df["sentiment_label"].value_counts().to_dict()
        total = len(disk_df)
        for label, count in counts.items():
            ratio = count / total
            assert ratio <= 0.60, f"Class {label} exceeds 60% limit at {ratio:.2%}"
            
    asyncio.run(run())
