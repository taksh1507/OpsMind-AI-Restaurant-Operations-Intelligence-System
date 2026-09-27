"""FastAPI Application Factory and Startup/Shutdown Events

Initializes the FastAPI application, configures routers, middleware, and lifecycle events.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import settings
from app.core.logging_config import setup_logging, setup_app_logger, AccessLogMiddleware
from app.database import init_db, close_db, get_db
from app.api import (
    auth,
    categories,
    menu_items,
    sales,
    analytics,
    recommendations,
    search,
    customers_router,
    data_import,
    training,
    users,
)
from app.api import ws
# Imported under an alias: the module name `settings` would otherwise shadow the
# `settings` config object imported above from app.core.
from app.api import settings as settings_api
from app.api import ai_usage
from app.api.deps import get_current_manager, get_current_owner

logger = setup_app_logger("opsmind.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events."""

    # Startup
    setup_logging()
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    # Fail fast on insecure configuration in non-development environments
    settings.validate_production_settings()
    await init_db(settings.database_url)

    # Ensure the schema exists. The app ships without Alembic migrations, so on a
    # fresh database (e.g. a new Postgres volume) the tables would otherwise be
    # missing and every DB-backed request would fail. Importing app.models
    # registers every ORM table on Base.metadata; create_all is a no-op for
    # tables that already exist.
    import app.models  # noqa: F401  (side effect: register models on metadata)
    from app.models.base import Base
    from app import database

    async with database.engine.begin() as conn:
        # Serialize schema creation across gunicorn workers. Every worker runs
        # create_all on boot; when a brand-new table is introduced, concurrent
        # workers otherwise race to create its sequence and one loses with a
        # "duplicate key ... pg_class" error, failing that worker's startup.
        # A transaction-scoped advisory lock lets the first worker create the
        # tables while the rest wait, then find everything already present.
        # (Postgres-only; the SQLite dev path has a single process, no race.)
        if database.engine.dialect.name == "postgresql":
            await conn.exec_driver_sql("SELECT pg_advisory_xact_lock(9130524217)")
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized")

    # Warm the currency exchange rate from the configured/live source (best-effort)
    try:
        from app.core.finance import refresh_exchange_rate_from_live_source

        await refresh_exchange_rate_from_live_source()
    except Exception:
        logger.warning("Currency exchange rate refresh failed; using configured fallback.")

    # Start automated retraining scheduler
    from app.core.scheduler import start_scheduler

    start_scheduler()

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Shutdown scheduler
    from app.core.scheduler import shutdown_scheduler

    await shutdown_scheduler()

    await close_db()
    logger.info("Database closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance

    OpenAPI Documentation:
        - Interactive API docs (Swagger UI): /docs
        - ReDoc documentation: /redoc

    System Architecture:
        User → Authentication (JWT) → Multi-Tenant Isolation → Business Logic
        → Claude AI Analysis → Database (PostgreSQL/SQLite)

    Core Capabilities:
        🤖 AI-Powered Analytics: Autonomous restaurant consultant via Anthropic Claude
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
            "By combining Claude AI reasoning with multi-tenant data isolation, "
            "we deliver context-aware recommendations that measure their real ROI.\n\n"
            "**Key Features:**\n"
            "- 🤖 **AI Strategy Agent**: Automated business recommendations via Anthropic Claude\n"
            "- 📈 **Revenue Forecasting**: Multi-day predictive sales with confidence scores\n"
            "- 💰 **Profit Optimization**: Margin analysis, cost reduction, pricing recommendations\n"
            "- 👥 **Labor Intelligence**: Staffing heatmaps and efficiency analysis\n"
            "- ⭐ **Sentiment Analysis**: Customer review processing and reputation tracking\n"
            "- 🌡️ **Environmental Awareness**: Weather-driven menu and staffing optimization\n"
            "- ✅ **Impact Verification**: Track, accept/reject, and measure AI recommendation ROI\n"
            "- 🔒 **Multi-Tenant Security**: Complete tenant isolation with JWT authentication\n\n"
            "**Tech Stack:**\n"
            "Backend: FastAPI (async) | Database: PostgreSQL/SQLite | ORM: SQLAlchemy 2.0 | "
            "AI: Anthropic Claude | Auth: JWT + Argon2/bcrypt | Analytics: NumPy/Pandas\n\n"
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
        debug=settings.debug,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Structured access logging for every HTTP request
    app.add_middleware(AccessLogMiddleware)

    # Include routers with /api/v1 prefix and tags for Swagger organization
    app.include_router(
        auth.router, prefix="/api/v1", tags=["🔐 Authentication & Authorization"]
    )
    app.include_router(
        users.router, prefix="/api/v1", tags=["👥 Team Management"]
    )
    app.include_router(
        settings_api.router, prefix="/api/v1", tags=["⚙️ Tenant Settings"]
    )
    app.include_router(
        ai_usage.router, prefix="/api/v1", tags=["📟 AI Usage & Limits"]
    )
    app.include_router(categories.router, prefix="/api/v1", tags=["🏷️ Menu Management"])
    app.include_router(
        menu_items.router, prefix="/api/v1", tags=["🍽️ Menu Items & Recipes"]
    )
    app.include_router(sales.router, prefix="/api/v1", tags=["💳 Sales & Transactions"])
    app.include_router(
        analytics.router,
        prefix="/api/v1",
        tags=["📊 Analytics & AI Insights"],
        dependencies=[Depends(get_current_manager)],
    )
    app.include_router(
        recommendations.router, prefix="/api/v1", tags=["✅ Recommendation Tracking"]
    )
    app.include_router(search.router, prefix="/api/v1", tags=["🔍 Global Search"])
    app.include_router(
        customers_router, prefix="/api/v1", tags=["👤 Customer Intelligence"]
    )
    app.include_router(data_import.router, prefix="/api/v1", tags=["📂 Data Import"])
    app.include_router(
        training.router,
        prefix="/api/v1",
        tags=["🏋️ Model Training"],
        dependencies=[Depends(get_current_owner)],
    )
    app.include_router(ws.router, tags=["🔌 WebSocket Real-Time"])

    # Health check endpoint
    @app.get(
        "/health",
        tags=["🏥 System Health"],
        summary="System Health Check",
        description="Returns the current health status of the OpsMind AI system with database connectivity check.",
    )
    async def health_check(db: AsyncSession = Depends(get_db)):
        """System health check endpoint for automated deployment monitoring.

        Checks:
        - Database connectivity and responsiveness
        - Application availability
        - Current server time in IST (Indian Standard Time)

        Returns:
            - status: "healthy" or "unhealthy"
            - app: Application name
            - version: Current version
            - timestamp_utc: Current time in UTC (ISO 8601 format)
            - timestamp_ist: Current time in IST (IS 8601 format)
            - database: "connected" or "disconnected"
            - uptime_check: True if responsive

        Use Cases:
            - AWS/Azure health checks for auto-scaling and load balancing
            - CloudWatch, DataDog, and other monitoring tools
            - Kubernetes liveness and readiness probes
            - Automated restart triggers on failure
        """
        try:
            # ✅ Check database connectivity by executing a simple query
            from sqlalchemy import text

            await db.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = "disconnected"
            # Log the error for debugging
            logger.error("Database health check failed: %s", e)

        # 🕐 Calculate current time in IST (UTC+5:30)
        utc_now = datetime.now(timezone.utc)
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        ist_now = utc_now.astimezone(ist_tz)

        # Determine overall health status
        is_healthy = db_status == "connected"
        status = "healthy" if is_healthy else "degraded"

        return {
            "status": status,
            "app": settings.app_name,
            "version": settings.app_version,
            "timestamp_utc": utc_now.isoformat(),
            "timestamp_ist": ist_now.isoformat(),
            "database": db_status,
            "uptime_check": True,
            "environment": "production" if not settings.debug else "development",
        }

    # Root endpoint
    @app.get(
        "/",
        tags=["📋 Welcome"],
        summary="API Welcome",
        description="Welcome endpoint with API information and documentation links.",
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
                "✅ Recommendation impact verification",
            ],
            "github": "https://github.com/taksh1507/OpsMind-AI-Restaurant-Operations-Intelligence-System",
        }

    return app


# Create the FastAPI application
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
