"""Unit and integration tests for the Model Performance API.

Verifies 404 responses for missing reports, correct calculation of summary metrics,
and multi-tenant directory scoping.
"""

import os
import shutil
import json
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, status
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from decimal import Decimal

from app.main import create_app
from app.database import get_db
from app.api.deps import get_current_user
from app.models.base import Base
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole


@pytest.mark.anyio
async def test_model_performance_endpoints():
    """Verify endpoint routing, validation formats, and tenant file path isolation."""
    test_tenant_id = 777
    report_dir = os.path.join("reports", str(test_tenant_id))
    report_path = os.path.join(report_dir, "backtest.csv")
    
    # 1. Setup in-memory SQLite database
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
    
    # Seeding
    async with async_session() as session:
        t = Tenant(id=test_tenant_id, tenant_id="tenant-777", name="Tenant 777", subscription_status=SubscriptionStatus.ACTIVE)
        u = User(id=test_tenant_id, tenant_id=test_tenant_id, email="owner777@test.com", hashed_password="pw", role=UserRole.OWNER)
        session.add_all([t, u])
        await session.commit()
        
    async def override_get_db():
        async with async_session() as s:
            yield s
            
    async def override_get_current_user():
        return u
        
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # Clear folder before test
    if os.path.exists(report_dir):
        shutil.rmtree(report_dir)
        
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            
            # --- 1. Test 404 No Report Available ---
            res = await client.get("/api/v1/analytics/model-performance")
            assert res.status_code == status.HTTP_404_NOT_FOUND
            assert "No backtest data available" in res.json()["detail"]
            
            # --- 2. Test 200 OK with mock CSV report ---
            os.makedirs(report_dir, exist_ok=True)
            mock_csv_content = (
                "week_idx,start_date,end_date,naive_mae,naive_rmse,lr_mae,lr_rmse,xgb_mae,xgb_rmse\n"
                "1,2026-04-23,2026-04-30,646.86,865.6,1035.74,1200.0,600.0,800.0\n"
                "2,2026-04-30,2026-05-07,712.57,755.58,952.38,1100.0,500.0,700.0\n"
            )
            with open(report_path, "w") as f:
                f.write(mock_csv_content)
                
            res = await client.get("/api/v1/analytics/model-performance")
            assert res.status_code == status.HTTP_200_OK
            
            json_res = res.json()
            assert json_res["status"] == "success"
            
            # Expected calculations:
            # naive_mae: (646.86 + 712.57) / 2 = 679.715 -> 679.72
            # xgboost_mae: (600 + 500) / 2 = 550.0
            # xgboost_rmse: (800 + 700) / 2 = 750.0
            # xgb_maes: [600, 500], mean = 550, std = 50
            # stability_ratio: 50 / 550 = 0.0909
            assert json_res["naive_mae"] == 679.72
            assert json_res["xgboost_mae"] == 550.0
            assert json_res["xgboost_rmse"] == 750.0
            assert json_res["stability_ratio"] == 0.0909
            assert len(json_res["weeks"]) == 2
            assert json_res["weeks"][0]["week_idx"] == 1
            
    finally:
        # Cleanup reports dir
        if os.path.exists(report_dir):
            shutil.rmtree(report_dir)
        await engine.dispose()
