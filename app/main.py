"""FastAPI Application Factory and Startup/Shutdown Events

Initializes the FastAPI application, configures routers, middleware, and lifecycle events.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import settings
from app.database import init_db, close_db
from app.api import auth, categories, menu_items


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
    """
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-Tenant Restaurant Operations Intelligence System",
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
    
    # Include routers
    app.include_router(auth.router)
    app.include_router(categories.router)
    app.include_router(menu_items.router)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "docs": "/docs"
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
