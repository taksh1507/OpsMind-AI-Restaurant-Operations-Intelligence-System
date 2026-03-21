"""
Day 14 Test Suite: Agentic Feedback & Learning Loop

Tests for:
1. Recommendation model creation and relationships
2. Recommendations API endpoints (CRUD)
3. Impact verification logic
4. Status transitions and validation
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Tenant, User, Recommendation, RecommendationCategory, RecommendationStatus
from app.core.security import hash_password, create_access_token
from app.core.config import settings
from app.database import get_db
from app.main import create_app
from app.services.ai_agent import verify_recommendation_impact


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async def override_get_db():
        async with async_session() as session:
            yield session
    
    yield async_session
    
    await engine.dispose()


@pytest.fixture
async def app(test_db):
    """Create FastAPI app with test database."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: test_db()
    return app


@pytest.fixture
async def client(app):
    """Create async HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_tenant(test_db):
    """Create a test tenant."""
    async with test_db() as session:
        tenant = Tenant(
            tenant_id="test_restaurant",
            name="Test Restaurant"
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        return tenant


@pytest.fixture
async def test_user(test_db, test_tenant):
    """Create a test user."""
    async with test_db() as session:
        user = User(
            tenant_id=test_tenant.id,
            email="owner@test.com",
            hashed_password=hash_password("password123"),
            is_active=True,
            is_admin=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def test_token(test_user):
    """Create a test JWT token."""
    return create_access_token(
        data={"sub": test_user.email, "tenant_id": test_user.tenant_id}
    )


@pytest.fixture
async def auth_client(client, test_token):
    """Create authenticated HTTP client."""
    client.headers["Authorization"] = f"Bearer {test_token}"
    return client


# ============================================================================
# Model Tests
# ============================================================================

class TestRecommendationModel:
    """Test Recommendation model creation and relationships."""
    
    @pytest.mark.asyncio
    async def test_recommendation_creation(self, test_db, test_tenant):
        """Test creating a recommendation."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_tenant.id,
                category=RecommendationCategory.PRICING.value,
                content="Increase burger price from $12 to $13.50",
                impact_score=400.00,
                status=RecommendationStatus.PENDING.value
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            
            assert rec.id is not None
            assert rec.tenant_id == test_tenant.id
            assert rec.category == RecommendationCategory.PRICING.value
            assert rec.status == RecommendationStatus.PENDING.value
            assert rec.created_at is not None
    
    @pytest.mark.asyncio
    async def test_recommendation_status_transition(self, test_db, test_tenant):
        """Test status transitions: Pending -> Accepted -> Verified."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_tenant.id,
                category=RecommendationCategory.STAFFING.value,
                content="Reduce staff on Tuesday mornings",
                impact_score=150.00,
                status=RecommendationStatus.PENDING.value
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            
            # Transition to Accepted
            rec.status = RecommendationStatus.ACCEPTED.value
            rec.applied_date = datetime.now(timezone.utc)
            await session.commit()
            
            # Verify transitions
            assert rec.status == RecommendationStatus.ACCEPTED.value
            assert rec.applied_date is not None
    
    @pytest.mark.asyncio
    async def test_recommendation_verified_impact(self, test_db, test_tenant):
        """Test recording verified impact and summary."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_tenant.id,
                category=RecommendationCategory.WASTE.value,
                content="Reduce portion sizes to save costs",
                impact_score=250.00,
                status=RecommendationStatus.ACCEPTED.value,
                applied_date=datetime.now(timezone.utc)
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            
            # Add verification results
            rec.verified_impact = 180.00
            rec.verification_summary = "Waste reduced by 3%, saving $180/week. Annual value: $9,360."
            await session.commit()
            
            assert rec.verified_impact == 180.00
            assert "Annual value" in rec.verification_summary


# ============================================================================
# API Endpoint Tests
# ============================================================================

class TestRecommendationsAPI:
    """Test Recommendations API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_recommendation(self, auth_client, test_user):
        """Test POST /recommendations endpoint."""
        payload = {
            "category": RecommendationCategory.PRICING.value,
            "content": "Push Iced Lattes - high margin item",
            "impact_score": 400.00
        }
        
        response = await auth_client.post(
            "/recommendations",
            json=payload
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == RecommendationCategory.PRICING.value
        assert data["status"] == RecommendationStatus.PENDING.value
        assert data["impact_score"] == 400.00
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_list_recommendations(self, auth_client, test_db, test_user):
        """Test GET /recommendations endpoint."""
        # Create multiple recommendations
        async with test_db() as session:
            for i in range(3):
                rec = Recommendation(
                    tenant_id=test_user.tenant_id,
                    category=RecommendationCategory.STAFFING.value if i % 2 == 0 else RecommendationCategory.PRICING.value,
                    content=f"Recommendation {i+1}",
                    impact_score=100.00 * (i + 1),
                    status=RecommendationStatus.PENDING.value
                )
                session.add(rec)
            await session.commit()
        
        response = await auth_client.get("/recommendations")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["impact_score"] == 300.00  # Most recent first
    
    @pytest.mark.asyncio
    async def test_list_recommendations_with_filter(self, auth_client, test_db, test_user):
        """Test GET /recommendations with status_filter."""
        async with test_db() as session:
            # Create 2 pending and 1 accepted
            for status in [RecommendationStatus.PENDING.value, RecommendationStatus.PENDING.value, RecommendationStatus.ACCEPTED.value]:
                rec = Recommendation(
                    tenant_id=test_user.tenant_id,
                    category=RecommendationCategory.STAFFING.value,
                    content="Test recommendation",
                    impact_score=100.00,
                    status=status,
                    applied_date=datetime.now(timezone.utc) if status == RecommendationStatus.ACCEPTED.value else None
                )
                session.add(rec)
            await session.commit()
        
        response = await auth_client.get("/recommendations?status_filter=Pending")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(rec["status"] == RecommendationStatus.PENDING.value for rec in data)
    
    @pytest.mark.asyncio
    async def test_get_single_recommendation(self, auth_client, test_db, test_user):
        """Test GET /recommendations/{id} endpoint."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_user.tenant_id,
                category=RecommendationCategory.INVENTORY.value,
                content="Stock more ice",
                impact_score=200.00,
                status=RecommendationStatus.PENDING.value
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            rec_id = rec.id
        
        response = await auth_client.get(f"/recommendations/{rec_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == rec_id
        assert data["content"] == "Stock more ice"
    
    @pytest.mark.asyncio
    async def test_update_recommendation_accept(self, auth_client, test_db, test_user):
        """Test PATCH /recommendations/{id} to accept recommendation."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_user.tenant_id,
                category=RecommendationCategory.PRICING.value,
                content="Raise prices",
                impact_score=300.00,
                status=RecommendationStatus.PENDING.value
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            rec_id = rec.id
        
        payload = {
            "status": RecommendationStatus.ACCEPTED.value
        }
        
        response = await auth_client.patch(
            f"/recommendations/{rec_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == RecommendationStatus.ACCEPTED.value
        assert data["applied_date"] is not None
    
    @pytest.mark.asyncio
    async def test_update_recommendation_reject(self, auth_client, test_db, test_user):
        """Test PATCH /recommendations/{id} to reject recommendation."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_user.tenant_id,
                category=RecommendationCategory.STAFFING.value,
                content="Cut staff",
                impact_score=150.00,
                status=RecommendationStatus.PENDING.value
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            rec_id = rec.id
        
        payload = {
            "status": RecommendationStatus.REJECTED.value
        }
        
        response = await auth_client.patch(
            f"/recommendations/{rec_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == RecommendationStatus.REJECTED.value
    
    @pytest.mark.asyncio
    async def test_cannot_change_accepted_to_rejected(self, auth_client, test_db, test_user):
        """Test that accepted recommendation cannot be changed to rejected."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_user.tenant_id,
                category=RecommendationCategory.MENU.value,
                content="Add new item",
                impact_score=250.00,
                status=RecommendationStatus.ACCEPTED.value,
                applied_date=datetime.now(timezone.utc)
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            rec_id = rec.id
        
        payload = {
            "status": RecommendationStatus.REJECTED.value
        }
        
        response = await auth_client.patch(
            f"/recommendations/{rec_id}",
            json=payload
        )
        
        assert response.status_code == 409  # Conflict
        assert "Cannot change status" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_pending_recommendation(self, auth_client, test_db, test_user):
        """Test DELETE /recommendations/{id} for pending recommendation."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_user.tenant_id,
                category=RecommendationCategory.WASTE.value,
                content="Reduce waste",
                impact_score=200.00,
                status=RecommendationStatus.PENDING.value
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            rec_id = rec.id
        
        response = await auth_client.delete(f"/recommendations/{rec_id}")
        
        assert response.status_code == 204
        
        # Verify deletion
        response = await auth_client.get(f"/recommendations/{rec_id}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_cannot_delete_accepted_recommendation(self, auth_client, test_db, test_user):
        """Test that accepted recommendation cannot be deleted."""
        async with test_db() as session:
            rec = Recommendation(
                tenant_id=test_user.tenant_id,
                category=RecommendationCategory.PROMOTION.value,
                content="Promote item",
                impact_score=180.00,
                status=RecommendationStatus.ACCEPTED.value,
                applied_date=datetime.now(timezone.utc)
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            rec_id = rec.id
        
        response = await auth_client.delete(f"/recommendations/{rec_id}")
        
        assert response.status_code == 409  # Conflict
        assert "Can only delete recommendations in Pending status" in response.json()["detail"]


# ============================================================================
# Impact Verification Tests
# ============================================================================

class TestImpactVerification:
    """Test impact verification and ROI calculation."""
    
    @pytest.mark.asyncio
    async def test_verify_impact_success(self):
        """Test verify_impact with positive result."""
        recommendation = {
            "id": 1,
            "category": "Pricing",
            "content": "Increase burger price to $14",
            "impact_score": 400.00
        }
        
        before_metrics = {
            "revenue": 5000,
            "profit": 800,
            "profit_margin": 16,
            "specific_item_sales": 120,
            "item_profit": 360,
            "days_elapsed": 7
        }
        
        after_metrics = {
            "revenue": 5200,
            "profit": 1000,
            "profit_margin": 19.2,
            "specific_item_sales": 128,
            "item_profit": 430,
            "days_elapsed": 7
        }
        
        result = await verify_recommendation_impact(recommendation, before_metrics, after_metrics)
        
        assert result["status"] == "success"
        assert result["actual_impact"] == 200.00
        assert result["original_prediction"] == 400.00
        assert result["changes"]["profit_change"] == 200.00
        assert result["annual_projection"] > 0
        assert "success_report" in result
    
    @pytest.mark.asyncio
    async def test_verify_impact_partial_success(self):
        """Test verify_impact with partial success."""
        recommendation = {
            "id": 2,
            "category": "Waste",
            "content": "Reduce portion sizes",
            "impact_score": 300.00
        }
        
        before_metrics = {
            "revenue": 4500,
            "profit": 675,
            "profit_margin": 15,
            "specific_item_sales": 100,
            "item_profit": 150,
            "days_elapsed": 7
        }
        
        after_metrics = {
            "revenue": 4400,
            "profit": 750,
            "profit_margin": 17,
            "specific_item_sales": 95,
            "item_profit": 160,
            "days_elapsed": 7
        }
        
        result = await verify_recommendation_impact(recommendation, before_metrics, after_metrics)
        
        assert result["status"] == "success"
        assert result["actual_impact"] == 75.00
        assert result["success_level"] == "Below Target"  # Predicted $300, got $75
    
    @pytest.mark.asyncio
    async def test_verify_impact_exceeded_expectations(self):
        """Test verify_impact exceeding predictions."""
        recommendation = {
            "id": 3,
            "category": "Menu",
            "content": "Feature Iced Lattes",
            "impact_score": 250.00
        }
        
        before_metrics = {
            "revenue": 4000,
            "profit": 600,
            "profit_margin": 15,
            "specific_item_sales": 80,
            "item_profit": 240,
            "days_elapsed": 7
        }
        
        after_metrics = {
            "revenue": 4600,
            "profit": 950,
            "profit_margin": 20.7,
            "specific_item_sales": 140,
            "item_profit": 420,
            "days_elapsed": 7
        }
        
        result = await verify_recommendation_impact(recommendation, before_metrics, after_metrics)
        
        assert result["status"] == "success"
        assert result["actual_impact"] == 350.00
        assert result["success_level"] == "Exceeded"
        assert "annual_projection" in result
        assert result["annual_projection"] > 18000  # $350 * 52 weeks
    
    @pytest.mark.asyncio
    async def test_annual_roi_projection(self):
        """Test annual ROI projection calculation."""
        recommendation = {
            "id": 4,
            "category": "Staffing",
            "content": "Optimize Tuesday staffing",
            "impact_score": 150.00
        }
        
        before_metrics = {
            "revenue": 3000,
            "profit": 450,
            "profit_margin": 15,
            "specific_item_sales": 50,
            "item_profit": 100,
            "days_elapsed": 4  # Only 4 days of data
        }
        
        after_metrics = {
            "revenue": 3100,
            "profit": 550,
            "profit_margin": 17.7,
            "specific_item_sales": 52,
            "item_profit": 130,
            "days_elapsed": 4
        }
        
        result = await verify_recommendation_impact(recommendation, before_metrics, after_metrics)
        
        # Profit change = $100 over 4 days
        # Annual projection = $100 * (365/4) = ~$9,125
        assert result["annual_projection"] > 8000


# ============================================================================
# Security Tests
# ============================================================================

class TestRecommendationsSecurity:
    """Test security and tenant isolation."""
    
    @pytest.mark.asyncio
    async def test_cannot_view_other_tenant_recommendation(self, auth_client, test_db, test_user):
        """Test that users can only view their own tenant's recommendations."""
        # Create another tenant with a recommendation
        async with test_db() as session:
            other_tenant = Tenant(
                tenant_id="other_restaurant",
                name="Other Restaurant"
            )
            session.add(other_tenant)
            await session.flush()
            
            rec = Recommendation(
                tenant_id=other_tenant.id,
                category=RecommendationCategory.PRICING.value,
                content="Other tenant's recommendation",
                impact_score=100.00,
                status=RecommendationStatus.PENDING.value
            )
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            rec_id = rec.id
        
        # Try to access with different tenant's token
        response = await auth_client.get(f"/recommendations/{rec_id}")
        
        assert response.status_code == 404


# ============================================================================
# Integration Tests
# ============================================================================

class TestDay14Integration:
    """Integration tests for complete Day 14 workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_recommendation_lifecycle(self, auth_client, test_db, test_user):
        """Test complete flow: Create -> Accept -> Verify Impact."""
        # 1. Create recommendation
        create_payload = {
            "category": RecommendationCategory.PRICING.value,
            "content": "Increase Iced Latte price",
            "impact_score": 400.00
        }
        
        create_response = await auth_client.post("/recommendations", json=create_payload)
        assert create_response.status_code == 201
        rec_id = create_response.json()["id"]
        assert create_response.json()["status"] == RecommendationStatus.PENDING.value
        
        # 2. Accept the recommendation
        accept_payload = {
            "status": RecommendationStatus.ACCEPTED.value
        }
        
        accept_response = await auth_client.patch(
            f"/recommendations/{rec_id}",
            json=accept_payload
        )
        assert accept_response.status_code == 200
        assert accept_response.json()["status"] == RecommendationStatus.ACCEPTED.value
        assert accept_response.json()["applied_date"] is not None
        
        # 3. Verify that it appears in accepted list
        list_response = await auth_client.get("/recommendations?status_filter=Accepted")
        assert list_response.status_code == 200
        recommendations = list_response.json()
        assert any(rec["id"] == rec_id for rec in recommendations)
        
        print("✅ Complete recommendation lifecycle test passed!")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
