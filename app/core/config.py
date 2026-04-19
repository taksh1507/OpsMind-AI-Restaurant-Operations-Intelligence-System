"""Application Configuration

Manages environment variables and application settings using Pydantic.
All sensitive data is loaded from environment variables (not committed to git).
Use a .env file for local development.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.
    
    Production-Ready: All sensitive data must be provided via environment variables.
    Never commit secrets to git. Use GitHub Secrets for CI/CD.
    """
    
    # ===== DATABASE (REQUIRED FOR PRODUCTION) =====
    database_url: str = Field(
        default="sqlite+aiosqlite:///./opsmind_demo.db",
        description="Async database URL for SQLAlchemy"
    )
    
    # ===== JWT CONFIGURATION (SECURITY CRITICAL) =====
    secret_key: str = Field(
        default="dev-only-change-in-production",
        description="Secret key for JWT token signing - MUST be set in production via env var"
    )
    algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT token encoding"
    )
    access_token_expire_minutes: int = Field(
        default=1440,  # 24 hours
        description="Expiration time for access tokens in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=30,
        description="Expiration time for refresh tokens in days"
    )
    
    # ===== APPLICATION CONFIGURATION =====
    app_name: str = Field(
        default="OpsMind AI",
        description="Application name"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode - set to False in production"
    )
    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    
    # ===== CORS CONFIGURATION =====
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )
    
    # ===== AI/LLM CONFIGURATION (REQUIRED FOR AI FEATURES) =====
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key - Required for AI agent features (set via SECRET_GEMINI_API_KEY env var)"
    )
    
    # ===== WEATHER API CONFIGURATION (OPTIONAL) =====
    openweather_api_key: Optional[str] = Field(
        default=None,
        description="OpenWeatherMap API key - Required for weather-aware intelligence (set via OPENWEATHER_API_KEY env var)"
    )
    weather_enabled: bool = Field(
        default=True,
        description="Enable weather-aware reasoning in AI agent"
    )
    
    # ===== SECURITY & VALIDATION =====
    def validate_production_settings(self):
        """Validate that all critical secrets are set in production."""
        if self.environment == "production":
            missing_secrets = []
            if self.secret_key == "dev-only-change-in-production":
                missing_secrets.append("SECRET_KEY")
            if not self.gemini_api_key:
                missing_secrets.append("GEMINI_API_KEY")
            
            if missing_secrets:
                raise ValueError(
                    f"Production environment requires these secrets to be set: {', '.join(missing_secrets)}"
                )
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Validate production settings on app startup
if os.getenv("ENVIRONMENT", "development") == "production":
    settings.validate_production_settings()
