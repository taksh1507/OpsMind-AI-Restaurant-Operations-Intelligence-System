"""Application Configuration

Manages environment variables and application settings using Pydantic.
Use a .env file for sensitive values.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from .env file and environment variables."""
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://opsmind:password@localhost:5432/opsmind_ai",
        description="Async database URL for SQLAlchemy"
    )
    
    # JWT Configuration
    secret_key: str = Field(
        default="your-super-secret-key-change-this-in-production",
        description="Secret key for JWT token signing"
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
    
    # Application
    app_name: str = Field(default="OpsMind AI", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )
    
    # AI/LLM Configuration
    google_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key for AI consulting features"
    )
    
    # Weather API Configuration (Day 13 - Environmental Awareness)
    openweather_api_key: Optional[str] = Field(
        default=None,
        description="OpenWeatherMap API key for weather-aware intelligence"
    )
    weather_enabled: bool = Field(
        default=True,
        description="Enable weather-aware reasoning in AI agent"
    )
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
