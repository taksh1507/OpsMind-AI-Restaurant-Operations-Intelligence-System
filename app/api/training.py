"""Training Router.

Provides on-demand model retraining endpoints for forecasting and customer segmentation.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models import User
from app.ml.train_forecast import train_model
from app.ml.train_segmentation import train_customer_segmentation
from app.ml.segmentation_features import build_segmentation_features
from app.services.forecast_service import clear_forecast_model_cache

router = APIRouter(prefix="/ml", tags=["🏋️ Model Training"])


@router.post("/retrain", status_code=status.HTTP_200_OK)
async def retrain_models(
    model_type: Optional[str] = "all",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger on-demand retraining of forecasting and/or customer segmentation models.
    
    Accepts model_type: "forecast", "segmentation", or "all".
    Saves incremented version files and updates manifest.json.
    """
    model_type = model_type.lower().strip()
    if model_type not in ("forecast", "segmentation", "all"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model_type. Must be 'forecast', 'segmentation', or 'all'."
        )

    tenant_id = current_user.tenant_id
    response_data: Dict[str, Any] = {
        "status": "success",
        "tenant_id": tenant_id
    }

    # 1. Retrain Forecast
    if model_type in ("forecast", "all"):
        try:
            forecast_res = await train_model(tenant_id=tenant_id, session=db)
            if not forecast_res:
                raise ValueError("Feature engineering pipeline returned no sales data for training.")
                
            # Invalidate forecast cache immediately
            clear_forecast_model_cache(tenant_id)
            
            # Generate and save backtest report for model performance tracking
            from app.ml.backtest import run_backtest
            import os
            try:
                results_df, _, _, _ = await run_backtest(tenant_id=tenant_id, session=db, num_weeks=8)
                report_dir = os.path.join("reports", str(tenant_id))
                os.makedirs(report_dir, exist_ok=True)
                results_df.to_csv(os.path.join(report_dir, "backtest.csv"), index=False)
            except Exception as e_bt:
                print(f"Failed to generate backtest report during retraining: {e_bt}")
            
            response_data["forecast"] = {
                "version": forecast_res["version"],
                "mae": forecast_res["mae"],
                "rmse": forecast_res["rmse"]
            }
        except Exception as e:
            if model_type == "forecast":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Forecasting retraining failed: {str(e)}"
                )
            else:
                # In 'all' mode, we raise the first failure to be safe
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Forecasting retraining failed: {str(e)}"
                )

    # 2. Retrain Customer Segmentation
    if model_type in ("segmentation", "all"):
        try:
            df_features = await build_segmentation_features(db, tenant_id)
            segmentation_res = train_customer_segmentation(df_features, tenant_id)
            
            response_data["segmentation"] = {
                "version": segmentation_res["version"],
                "best_k": segmentation_res["best_k"],
                "silhouette_score": segmentation_res["silhouette_score"]
            }
        except ValueError as e:
            # Expected error when not enough customers exist
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Segmentation retraining failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Segmentation retraining failed: {str(e)}"
            )

    return response_data
