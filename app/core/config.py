"""Application Configuration

Manages environment variables and application settings using Pydantic.
All sensitive data is loaded from environment variables (not committed to git).
Use a .env file for local development.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator, model_validator
from typing import Literal, Optional
from decimal import Decimal
from ipaddress import ip_network


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    Production-Ready: All sensitive data must be provided via environment variables.
    Never commit secrets to git. Use GitHub Secrets for CI/CD.
    """

    # ===== DATABASE (REQUIRED FOR PRODUCTION) =====
    database_url: str = Field(
        default="sqlite+aiosqlite:///./opsmind_demo.db",
        description="Async database URL for SQLAlchemy",
    )

    # ===== JWT CONFIGURATION (SECURITY CRITICAL) =====
    secret_key: str = Field(
        default="dev-only-change-in-production",
        description="Secret key for JWT token signing - MUST be set in production via env var",
    )
    algorithm: str = Field(
        default="HS256", description="Algorithm for JWT token encoding"
    )
    access_token_expire_minutes: int = Field(
        default=15,
        description="Expiration time for access tokens in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=30, description="Expiration time for refresh tokens in days"
    )
    trusted_proxies: list[str] = Field(default_factory=list)
    redis_url: Optional[str] = None
    rate_limit_max_keys: int = Field(default=10000, ge=10)
    web_concurrency: int = Field(default=1, ge=1)
    run_scheduler: bool = False
    migrate_on_startup: bool = True
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_pool_timeout: int = Field(default=30, ge=1)
    ws_max_connections_per_tenant: int = Field(default=100, ge=1, le=10000)
    ws_max_connections_per_user: int = Field(default=5, ge=1, le=100)
    ws_max_message_bytes: int = Field(default=4096, ge=256, le=65536)
    ws_idle_timeout_seconds: float = Field(default=60, ge=1)
    ws_auth_timeout_seconds: float = Field(default=5, ge=1)
    ws_send_timeout_seconds: float = Field(default=3, gt=0)

    @field_validator("trusted_proxies")
    @classmethod
    def validate_trusted_proxies(cls, values):
        for value in values:
            ip_network(value, strict=False)
        return values

    @field_validator("anthropic_available_models")
    @classmethod
    def validate_available_models(cls, values):
        models = [value.strip() for value in values if value.strip()]
        if len(models) != len(values) or len(set(models)) != len(models):
            raise ValueError("ANTHROPIC_AVAILABLE_MODELS must contain unique, non-empty model IDs.")
        return models

    # ===== REFRESH-TOKEN COOKIE (httpOnly) =====
    # The refresh token is delivered to the browser only as an httpOnly cookie so
    # JavaScript (and therefore XSS) can never read it. The short-lived access
    # token still travels in the JSON body / Authorization header.
    refresh_cookie_name: str = Field(
        default="opsmind_refresh_token",
        description="Name of the httpOnly cookie that stores the refresh token",
    )
    cookie_secure: bool = Field(
        default=False,
        description="Set the Secure flag on the refresh cookie (MUST be True in production/HTTPS)",
    )
    cookie_samesite: str = Field(
        default="lax",
        description="SameSite policy for the refresh cookie: 'lax', 'strict', or 'none'. "
        "'lax' blocks the cookie on cross-site POSTs, which is our CSRF defense.",
    )
    cookie_domain: Optional[str] = Field(
        default=None,
        description="Domain for the refresh cookie (None = host-only, correct for localhost dev)",
    )
    cookie_path: str = Field(
        default="/api/v1/auth",
        description="Path scope for the refresh cookie so it is only sent to the auth endpoints",
    )

    # ===== APPLICATION CONFIGURATION =====
    app_name: str = Field(default="OpsMind AI", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(
        default=False, description="Debug mode - set to False in production"
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment: development, staging, production",
    )

    # ===== CORS CONFIGURATION =====
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )

    # ===== AI/LLM CONFIGURATION (REQUIRED FOR AI FEATURES) =====
    # Primary LLM is Anthropic Claude (default model: claude-opus-4-8).
    # Supply credentials as EITHER an auth token (bearer — used by
    # Anthropic-compatible gateway/proxy endpoints) OR an API key (x-api-key —
    # used by the official Anthropic API).
    anthropic_auth_token: Optional[str] = Field(
        default=None,
        description="Anthropic bearer auth token (set via ANTHROPIC_AUTH_TOKEN). Used with gateway/proxy endpoints.",
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key for the official API (set via ANTHROPIC_API_KEY).",
    )
    anthropic_base_url: Optional[str] = Field(
        default=None,
        description="Override base URL for an Anthropic-compatible endpoint (set via ANTHROPIC_BASE_URL). Leave unset for the official Anthropic API.",
    )
    anthropic_model: str = Field(
        default="claude-opus-4-8",
        description="Anthropic model ID used by the AI agent (set via ANTHROPIC_MODEL).",
    )
    anthropic_timeout_seconds: float = Field(default=40, gt=0, le=100)
    anthropic_max_retries: int = Field(default=1, ge=0, le=5)
    anthropic_available_models: list[str] = Field(
        default_factory=lambda: [
            "claude-opus-4-8",
            "claude-sonnet-5",
            "claude-haiku-4-5-20251001",
        ]
    )
    ai_request_token_reservation: int = Field(default=24576, ge=1)
    ai_max_input_characters: int = Field(default=48000, ge=1000, le=200000)
    ai_untrusted_text_max_characters: int = Field(default=5000, ge=100, le=50000)
    ai_max_output_tokens: int = Field(default=2048, ge=64, le=8192)

    # Per-tenant monthly AI spend guardrail (Phase 4). Counts input+output tokens
    # across ALL AI features for a restaurant within the current UTC month. When a
    # tenant reaches the cap, AI endpoints return HTTP 429 until the month rolls
    # over. Set to 0 (or a negative value) to disable enforcement entirely.
    ai_monthly_token_cap: int = Field(
        default=1_500_000,
        description="Per-tenant monthly AI token cap (input+output). 0 or negative disables enforcement. Set via AI_MONTHLY_TOKEN_CAP.",
    )

    # [DEPRECATED] Google Gemini key — no longer used by the AI agent; retained
    # so existing .env files do not fail validation with extra="ignore".
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="[DEPRECATED] Google Gemini API key. No longer used by the AI agent.",
    )

    # ===== WEATHER API CONFIGURATION (OPTIONAL) =====
    openweather_api_key: Optional[str] = Field(
        default=None,
        description="OpenWeatherMap API key - Required for weather-aware intelligence (set via OPENWEATHER_API_KEY env var)",
    )
    weather_enabled: bool = Field(
        default=True, description="Enable weather-aware reasoning in AI agent"
    )

    # ===== CURRENCY (USD -> INR) =====
    usd_to_inr_rate: Decimal = Field(
        default=Decimal("94.05"),
        description="USD to INR exchange rate (1 USD in INR). Override via USD_TO_INR_RATE env var or refresh live.",
    )
    fx_live_enabled: bool = Field(
        default=True,
        description="Automatically refresh the exchange rate from a live public FX API at startup",
    )
    fx_fallback_rate: Decimal = Field(
        default=Decimal("94.05"),
        description="Fallback rate used when the live FX source is unavailable",
    )

    # ===== RETRAINING CONFIGURATION =====
    retrain_cron: str = Field(
        default="0 2 * * 0",
        description="Cron expression for automated model retraining (default: Sunday 2 AM)",
    )

    # ===== SECURITY & VALIDATION =====
    @property
    def anthropic_credentials_present(self) -> bool:
        """True when a usable Anthropic credential (token or API key) is set."""
        return bool(self.anthropic_auth_token or self.anthropic_api_key)

    @model_validator(mode="after")
    def reject_insecure_defaults(self):
        """Reject default/dev-only secrets in any non-development environment.

        Runs automatically on Settings instantiation (i.e. on import), so a
        forgotten SECRET_KEY can never silently reach staging or production.
        """
        self.validate_production_settings()
        return self

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    def validate_production_settings(self):
        """Fail at configuration loading and startup when defaults are unsafe."""
        if self.web_concurrency > 1 and not self.redis_url:
            raise ValueError("REDIS_URL is required when WEB_CONCURRENCY is greater than 1.")
        if self.run_scheduler and self.web_concurrency != 1:
            raise ValueError("RUN_SCHEDULER=true requires WEB_CONCURRENCY=1; run one dedicated scheduler process.")
        if self.environment != "development":
            secret = self.secret_key.strip()
            if secret == "dev-only-change-in-production" or len(secret) < 32:
                raise ValueError(
                    "SECRET_KEY must be non-empty, at least 32 characters, "
                    "and different from the development default outside development."
                )
        if self.environment == "production":
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production (HTTPS required).")
            if (
                "cors_origins" not in self.model_fields_set
                or not self.cors_origins
                or any(not origin.strip() or "*" in origin for origin in self.cors_origins)
            ):
                raise ValueError(
                    "CORS_ORIGINS must be explicitly configured with non-empty, "
                    "non-wildcard origins in production."
                )
        if self.environment != "development":
            if not self.anthropic_credentials_present and (
                self.environment == "production" or not self.debug
            ):
                raise ValueError(
                    "Anthropic credentials must be set in a non-development "
                    "environment (set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY)."
                )

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra env vars without validation error
    )


# Global settings instance
settings = Settings()
