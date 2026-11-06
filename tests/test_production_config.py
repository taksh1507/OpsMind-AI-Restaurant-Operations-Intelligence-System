"""Configuration, startup and health regression tests for production defaults."""

import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
import pytest

import app.main as main
from app.core.config import Settings


@pytest.fixture(autouse=True)
def clean_config_environment(monkeypatch):
    for name in (
        "ENVIRONMENT", "SECRET_KEY", "COOKIE_SECURE", "CORS_ORIGINS", "DEBUG",
        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)


def production_settings(**overrides):
    values = dict(
        environment="production",
        secret_key="a-secure-test-secret-with-at-least-32-characters",
        cookie_secure=True,
        cors_origins=["https://restaurant.example"],
        anthropic_api_key="test-only-no-network",
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("environment", ["production", "staging"])
@pytest.mark.parametrize("secret", ["", "short", "x" * 31, " " * 32,
                                    "dev-only-change-in-production"])
def test_non_development_rejects_weak_secrets(environment, secret):
    with pytest.raises(ValidationError, match="SECRET_KEY must"):
        production_settings(environment=environment, secret_key=secret)


@pytest.mark.parametrize("secret", ["", "short", "dev-only-change-in-production"])
def test_development_accepts_local_defaults(secret):
    config = Settings(_env_file=None, secret_key=secret)
    assert config.environment == "development"


def test_minimum_secret_length_and_environment_normalization():
    config = production_settings(secret_key="x" * 32, environment=" Production ")
    assert config.environment == "production"


@pytest.mark.parametrize("environment", ["", "prod", "unknown"])
def test_unknown_environment_cannot_bypass_validation(environment):
    with pytest.raises(ValidationError):
        production_settings(environment=environment)


def test_production_rejects_insecure_cookie():
    with pytest.raises(ValidationError, match="COOKIE_SECURE must be true"):
        production_settings(cookie_secure=False)


@pytest.mark.parametrize("debug", [False, True])
def test_existing_production_ai_credential_requirement_is_preserved(debug):
    with pytest.raises(ValidationError, match="Anthropic credentials must"):
        production_settings(anthropic_api_key=None, debug=debug)


@pytest.mark.parametrize("origins", [[], [""], [" "], ["*"],
                                     ["https://*.example.com"]])
def test_production_rejects_empty_or_wildcard_cors(origins):
    with pytest.raises(ValidationError, match="CORS_ORIGINS must"):
        production_settings(cors_origins=origins)


def test_production_requires_explicit_cors():
    with pytest.raises(ValidationError, match="CORS_ORIGINS must"):
        Settings(
            _env_file=None, environment="production", secret_key="x" * 32,
            cookie_secure=True, anthropic_api_key="test-only",
        )


def test_production_config_loads_from_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ORIGINS", '["https://restaurant.example"]')
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only")
    config = Settings(_env_file=None)
    assert config.cookie_secure is True
    assert config.cors_origins == ["https://restaurant.example"]


def test_startup_revalidates_mutated_settings(monkeypatch):
    config = production_settings()
    config.secret_key = ""
    monkeypatch.setattr(main, "settings", config)
    with pytest.raises(ValueError, match="SECRET_KEY must"):
        main.create_app()


@pytest.mark.parametrize("secret", ["", "short"])
def test_invalid_production_secret_prevents_app_import(secret):
    env = os.environ.copy()
    env.update(
        ENVIRONMENT="production", SECRET_KEY=secret, COOKIE_SECURE="true",
        CORS_ORIGINS='["https://restaurant.example"]',
        ANTHROPIC_API_KEY="test-only",
        PYTHONPATH=str(Path(__file__).resolve().parents[1]),
    )
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "SECRET_KEY must" in result.stderr


@pytest.mark.parametrize("environment", ["development", "production"])
async def test_docs_visibility(monkeypatch, environment):
    monkeypatch.setattr(main, "settings", production_settings(environment=environment))
    application = main.create_app()
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            response = await client.get(path)
            assert response.status_code == (404 if environment == "production" else 200)
        root = (await client.get("/")).json()
        assert root["docs"] == (None if environment == "production" else "/docs")


@pytest.mark.parametrize("environment", ["development", "staging", "production"])
@pytest.mark.parametrize("failure", [None, "execute", "connect"])
async def test_health_status_and_environment(monkeypatch, environment, failure):
    monkeypatch.setattr(main, "settings", production_settings(environment=environment))
    session = AsyncMock()
    if failure == "execute":
        session.execute.side_effect = RuntimeError("private database error")
    closed = []

    async def fake_get_db():
        if failure == "connect":
            raise RuntimeError("private connection error")
        try:
            yield session
        finally:
            closed.append(True)

    monkeypatch.setattr(main, "get_db", fake_get_db)
    application = main.create_app()
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == (503 if failure else 200)
    body = response.json()
    assert body["environment"] == environment
    assert body["database"] == ("disconnected" if failure else "connected")
    assert "private" not in response.text
    if failure != "connect":
        assert closed == [True]
