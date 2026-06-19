"""Unit and integration tests for the background retraining scheduler.

Verifies startup, shutdown, conditional retraining checks, manifest timestamp
comparisons, and skipped/executed run logging.
"""

import os
import shutil
import json
import logging
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import app.database
from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.menu import Category, MenuItem
from app.models.customer import Customer
from app.models.sales import Sale, SaleItem, PaymentMethod
from app.core.scheduler import (
    scheduler,
    start_scheduler,
    shutdown_scheduler,
    check_and_retrain_tenants
)


class LogCaptureHandler(logging.Handler):
    """Simple logging handler to capture log records for assertions."""
    def __init__(self):
        super().__init__()
        self.records = []
        
    def emit(self, record):
        self.records.append(self.format(record))


@pytest.mark.anyio
async def test_scheduler_lifecycle_and_retraining():
    """Verify background scheduler lifecycle management and conditional retraining triggers."""
    
    # 1. Test Scheduler Startup & Clean Shutdown
    assert not scheduler.running
    start_scheduler()
    assert scheduler.running
    await shutdown_scheduler()
    assert not scheduler.running
    
    # 2. Setup database and override database session factory
    test_tenant_id = 888
    model_dir = os.path.join("models", str(test_tenant_id))
    manifest_path = os.path.join(model_dir, "manifest.json")
    
    # Clean up model directory before running
    if os.path.exists(model_dir):
        shutil.rmtree(model_dir)
        
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Override global session local
    original_session_local = app.database.AsyncSessionLocal
    app.database.AsyncSessionLocal = async_session
    
    # Setup logger capture
    logger = logging.getLogger("opsmind.scheduler")
    capture_handler = LogCaptureHandler()
    logger.addHandler(capture_handler)
    logger.setLevel(logging.INFO)
    
    try:
        # Seed initial data (15+ days of sales for forecast to work)
        async with async_session() as session:
            t = Tenant(
                id=test_tenant_id,
                tenant_id=f"tenant-{test_tenant_id}",
                name="Test Tenant 888",
                subscription_status=SubscriptionStatus.ACTIVE
            )
            session.add(t)
            
            cat = Category(id=test_tenant_id, tenant_id=test_tenant_id, name="Breads")
            session.add(cat)
            
            mi1 = MenuItem(
                id=test_tenant_id * 10,
                tenant_id=test_tenant_id,
                category_id=test_tenant_id,
                name="Sourdough",
                price=Decimal("6.00"),
                cost_price=Decimal("2.00")
            )
            session.add(mi1)
            
            # Seed 3 Customers for segmentation
            customers = []
            for i in range(1, 4):
                cust = Customer(
                    id=test_tenant_id * 10 + i,
                    name=f"Cust {i}",
                    email=f"cust{i}@test888.com",
                    total_spent_inr=0.0,
                    visit_count=0
                )
                session.add(cust)
                customers.append(cust)
            await session.commit()
            
            # Seed 16 days of sales history (2 orders per customer for segmentation)
            ref_date = datetime.now(timezone.utc) - timedelta(days=2)
            ref_date = ref_date.replace(tzinfo=None)
            for day in range(16):
                sale_date = ref_date - timedelta(days=day)
                cust_idx = day % 3
                cust_id = customers[cust_idx].id
                
                sale = Sale(
                    tenant_id=test_tenant_id,
                    customer_id=cust_id,
                    total_amount=Decimal("12.00"),
                    tax_amount=Decimal("0.00"),
                    payment_method=PaymentMethod.CASH,
                    timestamp=sale_date
                )
                session.add(sale)
                await session.flush()
                
                session.add(SaleItem(
                    tenant_id=test_tenant_id,
                    sale_id=sale.id,
                    menu_item_id=mi1.id,
                    quantity=2,
                    unit_price_at_sale=Decimal("6.00")
                ))
            await session.commit()
            
        # --- PHASE 1: Run retraining when no models exist yet ---
        capture_handler.records.clear()
        await check_and_retrain_tenants()
        
        # Verify it trained and created models
        assert os.path.exists(os.path.join(model_dir, "forecast_v1.pkl"))
        assert os.path.exists(os.path.join(model_dir, "segments_v1.pkl"))
        assert os.path.exists(manifest_path)
        
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)
            
        assert manifest_data["forecast"] == "forecast_v1.pkl"
        assert manifest_data["segmentation"] == "segments_v1.pkl"
        assert manifest_data["retrain_reason"] == "scheduled"
        
        # Check logs
        log_output = "\n".join(capture_handler.records)
        assert f"Retraining models for tenant {test_tenant_id}" in log_output
        assert "Forecast model retrained successfully" in log_output
        
        # --- PHASE 2: Run retraining again with NO new sales data ---
        capture_handler.records.clear()
        
        # Capture timestamp before running
        manifest_time_before = manifest_data["last_trained"]
        
        await check_and_retrain_tenants()
        
        # Check version numbers didn't increment
        with open(manifest_path, "r") as f:
            manifest_data2 = json.load(f)
        assert manifest_data2["forecast"] == "forecast_v1.pkl"
        assert manifest_data2["last_trained"] == manifest_time_before  # Unchanged
        
        # Verify skipped logs
        log_output = "\n".join(capture_handler.records)
        assert f"Skipped retraining for tenant {test_tenant_id}" in log_output
        
        # --- PHASE 3: Run retraining after adding a new sale row ---
        capture_handler.records.clear()
        
        # Seed one new sale row
        async with async_session() as session:
            # Timestamp must be after the last trained time
            # last_trained is UTC, let's use datetime.now(timezone.utc) + 1 hour or simple future datetime
            future_sale_date = datetime.now(timezone.utc) + timedelta(minutes=5)
            # Make it naive for SQLite compatibility
            future_sale_date = future_sale_date.replace(tzinfo=None)
            
            new_sale = Sale(
                tenant_id=test_tenant_id,
                customer_id=customers[0].id,
                total_amount=Decimal("12.00"),
                tax_amount=Decimal("0.00"),
                payment_method=PaymentMethod.CASH,
                timestamp=future_sale_date
            )
            session.add(new_sale)
            await session.flush()
            
            session.add(SaleItem(
                tenant_id=test_tenant_id,
                sale_id=new_sale.id,
                menu_item_id=mi1.id,
                quantity=2,
                unit_price_at_sale=Decimal("6.00")
            ))
            await session.commit()
            
        await check_and_retrain_tenants()
        
        # Check that forecast model version incremented to v2
        assert os.path.exists(os.path.join(model_dir, "forecast_v2.pkl"))
        assert os.path.exists(os.path.join(model_dir, "segments_v2.pkl"))
        
        with open(manifest_path, "r") as f:
            manifest_data3 = json.load(f)
            
        assert manifest_data3["forecast"] == "forecast_v2.pkl"
        assert manifest_data3["segmentation"] == "segments_v2.pkl"
        assert manifest_data3["retrain_reason"] == "scheduled"
        assert manifest_data3["last_trained"] != manifest_time_before  # Changed
        
        # Verify training logs
        log_output = "\n".join(capture_handler.records)
        assert f"Retraining models for tenant {test_tenant_id}: Found 1 new sales" in log_output

    finally:
        # Restore session factory
        app.database.AsyncSessionLocal = original_session_local
        # Remove logs handler
        logger.removeHandler(capture_handler)
        # Clean up models
        if os.path.exists(model_dir):
            shutil.rmtree(model_dir)
        await engine.dispose()
