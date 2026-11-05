"""Regression cases for Step 3 authentication failures."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from app.api import auth, sales, users
from app.database import get_db
from app.models import Category, MenuItem
from decimal import Decimal


@pytest.fixture
async def client(db_session):
    application = FastAPI()
    for router in (auth.router, sales.router, users.router):
        application.include_router(router, prefix="/api/v1")

    async def database():
        yield db_session

    application.dependency_overrides[get_db] = database
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as http:
        yield http


async def register(client):
    response = await client.post("/api/v1/auth/register", json={
        "restaurant_name": "Security Bistro", "email": "owner@example.com",
        "password": "password123",
    })
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_spoofed_forwarded_headers_cannot_evade_login_limit(client):
    codes = []
    for index in range(6):
        response = await client.post("/api/v1/auth/login", json={
            "email": f"unknown{index}@example.com", "password": "wrongpassword",
        }, headers={"X-Forwarded-For": f"192.0.2.{index}"})
        codes.append(response.status_code)
    assert codes == [401] * 5 + [429]
    assert int(response.headers["Retry-After"]) > 0


async def test_password_change_revokes_old_access_token(client):
    headers = await register(client)
    from app.core.config import settings
    old_refresh = client.cookies.get(settings.refresh_cookie_name)
    response = await client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": "password123", "new_password": "newpassword123",
    })
    assert response.status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401
    fresh = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert (await client.get("/api/v1/auth/me", headers=fresh)).status_code == 200
    new_refresh = client.cookies.get(settings.refresh_cookie_name)
    client.cookies.clear()
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})).status_code == 200


async def test_temporary_password_user_cannot_create_sale(client, db_session):
    owner = await register(client)
    category = Category(id=1, tenant_id=1, name="Food")
    db_session.add(category)
    await db_session.flush()
    db_session.add(MenuItem(
        id=1, tenant_id=1, category_id=1, name="Meal", price=Decimal("20"),
        cost_price=Decimal("10"),
    ))
    await db_session.commit()
    created = await client.post("/api/v1/users", headers=owner, json={
        "email": "staff@example.com", "role": "staff", "temp_password": "temporary123",
    })
    assert created.status_code == 201
    login = await client.post("/api/v1/auth/login", json={
        "email": "staff@example.com", "password": "temporary123",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = await client.post("/api/v1/sales", headers=headers, json={
        "items": [{"menu_item_id": 1, "quantity": 1}], "payment_method": "cash",
    })
    assert response.status_code == 403
    assert response.json()["detail"] == "password change required"
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    assert (await client.get("/api/v1/sales", headers=headers)).status_code == 403
    changed = await client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": "temporary123", "new_password": "permanent123",
    })
    assert changed.status_code == 200
    fresh = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert (await client.post("/api/v1/sales", headers=fresh, json={
        "items": [{"menu_item_id": 1, "quantity": 1}], "payment_method": "cash",
    })).status_code == 201


async def test_account_lockout_survives_changing_trusted_client_ips(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "trusted_proxies", ["127.0.0.1"])
    codes = []
    for index in range(6):
        response = await client.post("/api/v1/auth/login", json={
            "email": "victim@example.com", "password": "wrongpassword",
        }, headers={"X-Forwarded-For": f"192.0.2.{index}"})
        codes.append(response.status_code)
    assert codes == [401] * 5 + [429]


async def test_logout_all_revokes_access_and_refresh_sessions(client):
    headers = await register(client)
    assert (await client.post("/api/v1/auth/logout-all", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={})).status_code == 401


async def test_role_change_and_deactivation_do_not_resurrect_old_sessions(client):
    owner = await register(client)
    created = await client.post("/api/v1/users", headers=owner, json={
        "email": "member@example.com", "role": "staff", "temp_password": "temporary123",
    })
    member_id = created.json()["member"]["id"]
    login = await client.post("/api/v1/auth/login", json={
        "email": "member@example.com", "password": "temporary123",
    })
    old = {"Authorization": f"Bearer {login.json()['access_token']}"}
    for update in ({"role": "manager"}, {"is_active": False}, {"is_active": True}):
        assert (await client.put(f"/api/v1/users/{member_id}", headers=owner, json=update)).status_code == 200
        assert (await client.get("/api/v1/auth/me", headers=old)).status_code in (401, 403)
    assert (await client.get("/api/v1/auth/me", headers=old)).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={})).status_code == 401


@pytest.mark.parametrize("route,maximum", [("register", 5), ("refresh", 30)])
async def test_public_auth_endpoints_are_limited(client, route, maximum):
    payload = {"restaurant_name": "Bistro", "email": "repeat@example.com", "password": "password123"}
    for _ in range(maximum):
        await client.post(f"/api/v1/auth/{route}", json=payload if route == "register" else {})
    response = await client.post(f"/api/v1/auth/{route}", json=payload if route == "register" else {})
    assert response.status_code == 429


async def test_password_change_attempts_are_limited(client):
    headers = await register(client)
    for _ in range(5):
        response = await client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": "wrongpassword", "new_password": "newpassword123",
        })
        assert response.status_code == 400
    response = await client.post("/api/v1/auth/change-password", headers=headers, json={
        "current_password": "password123", "new_password": "newpassword123",
    })
    assert response.status_code == 429


async def test_registration_text_does_not_disclose_duplicate_email(client):
    payload = {"restaurant_name": "Bistro", "email": "same@example.com", "password": "password123"}
    first = await client.post("/api/v1/auth/register", json=payload)
    duplicate = await client.post("/api/v1/auth/register", json=payload)
    assert first.json()["message"] == duplicate.json()["detail"]
    assert "same@example.com" not in duplicate.text


@pytest.mark.parametrize("version", [None, True, "0", -1, 1])
async def test_missing_or_mismatched_access_versions_are_rejected(client, version):
    import jwt
    from app.core.config import settings
    await register(client)
    payload = {"sub": "owner@example.com", "tenant_id": 1}
    if version is not None:
        payload["token_version"] = version
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_old_refresh_version_cannot_restore_a_revoked_session(client, db_session):
    from sqlalchemy import select
    from app.core.config import settings
    from app.models import RefreshToken
    headers = await register(client)
    old_refresh = client.cookies.get(settings.refresh_cookie_name)
    await client.post("/api/v1/auth/logout-all", headers=headers)
    row = (await db_session.execute(select(RefreshToken))).scalar_one()
    row.revoked = False  # Simulate a token record arriving after a concurrent revocation.
    await db_session.commit()
    client.cookies.clear()
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert response.status_code == 401
