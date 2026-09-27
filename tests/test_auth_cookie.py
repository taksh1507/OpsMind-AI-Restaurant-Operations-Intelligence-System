"""Endpoint tests for the httpOnly refresh-token cookie flow.

Verifies the Phase-5 hardening follow-up: the refresh token is delivered only
as an httpOnly cookie (never in the JSON body), and /auth/refresh reads that
cookie to rotate the session.

A minimal app (auth router only) is used so the real app's lifespan — which
starts the scheduler and hits external services — is never triggered.
"""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from app.api import auth
from app.database import get_db
from app.core.config import settings


def _build_app(db_session) -> FastAPI:
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


def _register_payload(email: str = "owner@test.com") -> dict:
    return {
        "restaurant_name": "Test Bistro",
        "email": email,
        "password": "password123",
    }


async def test_register_sets_httponly_cookie_and_hides_token_in_body(db_session):
    app = _build_app(db_session)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/register", json=_register_payload())

    assert resp.status_code == 201
    body = resp.json()
    # Access token is returned; refresh token is NOT exposed to JavaScript.
    assert body["access_token"]
    assert body.get("refresh_token") is None

    set_cookie = resp.headers.get("set-cookie", "").lower()
    assert settings.refresh_cookie_name.lower() in set_cookie
    assert "httponly" in set_cookie


async def test_refresh_reads_cookie_and_rotates(db_session):
    app = _build_app(db_session)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/auth/register", json=_register_payload())
        assert reg.status_code == 201
        first_access = reg.json()["access_token"]
        # The client cookie jar now holds the refresh cookie set by register.
        assert settings.refresh_cookie_name in client.cookies

        # No body token: the httpOnly cookie carries the refresh token.
        refreshed = await client.post("/api/v1/auth/refresh", json={})

    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    # Rotation re-issues the cookie.
    assert settings.refresh_cookie_name.lower() in refreshed.headers.get(
        "set-cookie", ""
    ).lower()


async def test_refresh_without_cookie_is_unauthorized(db_session):
    app = _build_app(db_session)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/refresh", json={})

    assert resp.status_code == 401
