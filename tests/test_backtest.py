"""Unit tests for the rolling backtest engine.

Runs a minimal 3-week synthetic backtest using the generated sales dataset
to confirm report structure, column sequence, and stability outputs.
"""

import os
import asyncio
import pandas as pd
from app.ml.backtest import run_backtest


def test_rolling_backtest_3_weeks():
    async def run():
        csv_path = os.path.join("tests", "data", "kaggle_restaurant_sales.csv")
        assert os.path.exists(csv_path), f"CSV path {csv_path} does not exist"
        
        results_df, mean_mae, std_mae, passed_stability = await run_backtest(
            csv_path, tenant_id=1, num_weeks=3
        )
        
        # 1. Assertions on results dataframe structure
        assert isinstance(results_df, pd.DataFrame), "Results should be a pandas DataFrame"
        assert len(results_df) == 3, f"Expected 3 rows in report, got {len(results_df)}"
        
        expected_cols = [
            "week_idx", "start_date", "end_date", 
            "naive_mae", "naive_rmse", "lr_mae", "lr_rmse", "xgb_mae", "xgb_rmse"
        ]
        for col in expected_cols:
            assert col in results_df.columns, f"Expected column {col} missing in report"
            
        # 2. Check metrics properties
        assert isinstance(mean_mae, float)
        assert isinstance(std_mae, float)
        assert isinstance(passed_stability, bool)
        
        # Verify indexes are sequential
        assert results_df["week_idx"].tolist() == [1, 2, 3]

    asyncio.run(run())
