"""FastAPI Application Factory and Startup/Shutdown Events

Initializes the FastAPI application, configures routers, middleware, and lifecycle events.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from app.core import settings
from app.database import init_db, close_db
from app.api import auth, categories, menu_items, sales, analytics, recommendations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events."""
    
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    await init_db(settings.database_url)
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    await close_db()
    print("✅ Database closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    
    OpenAPI Documentation:
        - Interactive API docs (Swagger UI): /docs
        - ReDoc documentation: /redoc
    
    System Architecture:
        User → Authentication (JWT) → Multi-Tenant Isolation → Business Logic
        → Gemini AI Analysis → Database (PostgreSQL/SQLite)
    
    Core Capabilities:
        🤖 AI-Powered Analytics: Autonomous restaurant consultant via Gemini 1.5
        📊 Real-Time Insights: Revenue forecasting, staffing optimization, margin analysis
        💰 Profit Intelligence: Cost reduction recommendations, waste detection
        🎯 Agentic Learning Loop: Track, accept/reject, and verify AI recommendation impact
        🌍 Environmental Awareness: Weather-aware menu promotions and staffing
    
    Implementation Highlights:
        ✅ Days 2-3: Multi-tenant SaaS foundation with JWT auth
        ✅ Days 7-11: AI strategy, forecasting, costs, sentiment, labor optimization
        ✅ Days 12-14: Mathematical confidence scoring, weather integration, feedback loop
        ✅ Day 15: Professional documentation and live demo capability
    """
    
    app = FastAPI(
        title="OpsMind AI — Restaurant Operations Intelligence",
        version=settings.app_version,
        description=(
            "**AI-Powered Multi-Tenant SaaS for Restaurant Operations**\n\n"
            "OpsMind AI empowers restaurant owners with autonomous AI consulting, "
            "predictive analytics, and real-time operational intelligence. "
            "By combining Gemini AI reasoning with multi-tenant data isolation, "
            "we deliver context-aware recommendations that measure their real ROI.\n\n"
            "**Key Features:**\n"
            "- 🤖 **AI Strategy Agent**: Automated business recommendations via Gemini\n"
            "- 📈 **Revenue Forecasting**: Multi-day predictive sales with confidence scores\n"
            "- 💰 **Profit Optimization**: Margin analysis, cost reduction, pricing recommendations\n"
            "- 👥 **Labor Intelligence**: Staffing heatmaps and efficiency analysis\n"
            "- ⭐ **Sentiment Analysis**: Customer review processing and reputation tracking\n"
            "- 🌡️ **Environmental Awareness**: Weather-driven menu and staffing optimization\n"
            "- ✅ **Impact Verification**: Track, accept/reject, and measure AI recommendation ROI\n"
            "- 🔒 **Multi-Tenant Security**: Complete tenant isolation with JWT authentication\n\n"
            "**Tech Stack:**\n"
            "Backend: FastAPI (async) | Database: PostgreSQL/SQLite | ORM: SQLAlchemy 2.0 | "
            "AI: Google Gemini 1.5 Flash | Auth: JWT + bcrypt | Analytics: NumPy/Pandas\n\n"
            "**Live Demo:** Seed the database with `scripts/seed_data.py` to see AI analytics in action."
        ),
        contact={
            "name": "OpsMind AI Support",
            "url": "https://github.com/taksh1507/OpsMind-AI-Restaurant-Operations-Intelligence-System",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        lifespan=lifespan,
        debug=settings.debug
    )
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Include routers with /api/v1 prefix and tags for Swagger organization
    app.include_router(
        auth.router,
        prefix="/api/v1",
        tags=["🔐 Authentication & Authorization"]
    )
    app.include_router(
        categories.router,
        prefix="/api/v1",
        tags=["🏷️ Menu Management"]
    )
    app.include_router(
        menu_items.router,
        prefix="/api/v1",
        tags=["🍽️ Menu Items & Recipes"]
    )
    app.include_router(
        sales.router,
        prefix="/api/v1",
        tags=["💳 Sales & Transactions"]
    )
    app.include_router(
        analytics.router,
        prefix="/api/v1",
        tags=["📊 Analytics & AI Insights"]
    )
    app.include_router(
        recommendations.router,
        prefix="/api/v1",
        tags=["✅ Recommendation Tracking"]
    )
    
    # Health check endpoint
    @app.get(
        "/health",
        tags=["🏥 System Health"],
        summary="System Health Check",
        description="Returns the current health status of the OpsMind AI system."
    )
    async def health_check():
        """System health check endpoint.
        
        Returns:
            - status: healthy/unhealthy
            - app: Application name
            - version: Current version
        """
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version
        }
    
    # Root endpoint
    @app.get(
        "/",
        tags=["📋 Welcome"],
        summary="API Welcome",
        description="Welcome endpoint with API information and documentation links."
    )
    async def root():
        """Welcome to OpsMind AI.
        
        Returns:
            - message: Welcome message
            - version: Current API version
            - docs: Link to interactive API documentation
            - features: List of core AI capabilities
        """
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "docs": "/docs",
            "redoc": "/redoc",
            "features": [
                "🤖 AI-powered strategic recommendations",
                "📈 Revenue forecasting with confidence scores",
                "💰 Profit margin optimization",
                "👥 Labor efficiency analysis",
                "⭐ Customer sentiment analysis",
                "🌡️ Weather-aware promotions",
                "✅ Recommendation impact verification"
            ],
            "github": "https://github.com/taksh1507/OpsMind-AI-Restaurant-Operations-Intelligence-System"
        }
    
    return app


# Create the FastAPI application
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
