"""Scheduled Background Model Retraining Task.

Automates checking and retraining per-tenant machine learning models
(forecast and customer segmentation) when new data is uploaded.
"""

import os
import json
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, func

from app.core import settings
import app.database
from app.models.tenant import Tenant
from app.models.sales import Sale
from app.ml.train_forecast import train_model
from app.ml.train_segmentation import train_customer_segmentation
from app.ml.segmentation_features import build_segmentation_features
from app.services.forecast_service import clear_forecast_model_cache

logger = logging.getLogger("opsmind.scheduler")

# Global reference to scheduler
scheduler = AsyncIOScheduler()


async def check_and_retrain_tenants() -> None:
    """Iterate over all tenants and trigger retraining for those with new sales data.
    
    Triggered periodically via Cron schedule.
    """
    logger.info("Executing scheduled model retraining checks...")
    
    if app.database.AsyncSessionLocal is None:
        logger.error("Database session factory (AsyncSessionLocal) not initialized. Skipping retraining.")
        return
        
    async with app.database.AsyncSessionLocal() as session:
        try:
            # 1. Fetch all tenants
            tenant_stmt = select(Tenant)
            res = await session.execute(tenant_stmt)
            tenants = res.scalars().all()
        except Exception as e:
            logger.error(f"Failed to query tenants during scheduled retraining: {e}")
            return
            
        for tenant in tenants:
            tenant_id = tenant.id
            
            # 2. Look up manifest.json for last_trained timestamp
            model_dir = os.path.join("models", str(tenant_id))
            manifest_path = os.path.join(model_dir, "manifest.json")
            last_trained = None
            
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r") as f:
                        manifest_data = json.load(f)
                    last_trained_str = manifest_data.get("last_trained")
                    if last_trained_str:
                        # Parse ISO format timestamp
                        last_trained = datetime.fromisoformat(last_trained_str)
                except Exception as e:
                    logger.error(f"Failed to load manifest.json for tenant {tenant_id}: {e}")
                    
            # 3. Check for new sales data since last_trained
            sales_stmt = select(func.count(Sale.id)).where(Sale.tenant_id == tenant_id)
            if last_trained:
                # If database stores naive UTC timestamps, convert last_trained to naive UTC comparison
                last_trained_naive = last_trained.replace(tzinfo=None)
                sales_stmt = sales_stmt.where(Sale.timestamp > last_trained_naive)
                
            try:
                count_res = await session.execute(sales_stmt)
                new_sales_count = count_res.scalar() or 0
            except Exception as e:
                logger.error(f"Failed to count new sales for tenant {tenant_id}: {e}")
                new_sales_count = 0
                
            # 4. Trigger retraining if new sales are present, or if never trained
            if new_sales_count > 0 or last_trained is None:
                logger.info(
                    f"Retraining models for tenant {tenant_id}: "
                    f"Found {new_sales_count} new sales since {last_trained or 'never'}."
                )
                try:
                    # Retrain Forecast (uses scheduled reason)
                    forecast_res = await train_model(tenant_id=tenant_id, session=session, reason="scheduled")
                    if forecast_res:
                        clear_forecast_model_cache(tenant_id)
                        logger.info(f"Forecast model retrained successfully for tenant {tenant_id}.")
                        
                        # Generate backtest report
                        try:
                            from app.ml.backtest import run_backtest
                            results_df, _, _, _ = await run_backtest(tenant_id=tenant_id, session=session, num_weeks=8)
                            report_dir = os.path.join("reports", str(tenant_id))
                            os.makedirs(report_dir, exist_ok=True)
                            results_df.to_csv(os.path.join(report_dir, "backtest.csv"), index=False)
                            logger.info(f"Generated backtest report for tenant {tenant_id}.")
                        except Exception as e_bt:
                            logger.error(f"Failed to generate scheduled backtest report for tenant {tenant_id}: {e_bt}")
                    else:
                        logger.warning(f"Forecast model training skipped or returned no data for tenant {tenant_id}.")
                        
                    # Retrain Customer Segmentation (if enough customers)
                    df_features = await build_segmentation_features(session, tenant_id)
                    if not df_features.empty and len(df_features) >= 3:
                        train_customer_segmentation(df_features, tenant_id, reason="scheduled")
                        logger.info(f"Customer segmentation model retrained successfully for tenant {tenant_id}.")
                    else:
                        logger.warning(
                            f"Customer segmentation training skipped for tenant {tenant_id} "
                            f"(insufficient segmentation customers: {len(df_features)})."
                        )
                except Exception as ex:
                    logger.error(f"Scheduled retraining failed for tenant {tenant_id}: {ex}")
            else:
                logger.info(f"Skipped retraining for tenant {tenant_id} (no new sales data since last_trained).")


def start_scheduler() -> None:
    """Start the background task scheduler."""
    if not scheduler.running:
        cron_expr = settings.retrain_cron
        logger.info(f"Initializing automated model retraining scheduler with Cron schedule: '{cron_expr}'")
        
        try:
            trigger = CronTrigger.from_crontab(cron_expr)
            scheduler.add_job(
                check_and_retrain_tenants,
                trigger=trigger,
                id="per_tenant_retrain_job",
                replace_existing=True
            )
            scheduler.start()
            logger.info("Retraining scheduler started successfully.")
        except Exception as e:
            logger.error(f"Failed to start retraining scheduler: {e}")


async def shutdown_scheduler() -> None:
    """Cleanly shutdown the scheduler."""
    if scheduler.running:
        logger.info("Stopping automated retraining scheduler...")
        try:
            scheduler.shutdown(wait=False)
            logger.info("Retraining scheduler shut down successfully.")
        except Exception as e:
            logger.error(f"Error shutting down retraining scheduler: {e}")
            # Raise so it can be seen in tests
            raise e
        # Yield control to the event loop to process the scheduled shutdown
        import asyncio
        await asyncio.sleep(0.1)
