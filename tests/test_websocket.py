import asyncio
from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from starlette.websockets import WebSocketDisconnect

from app.api import ws, sales
from app.api.deps import get_current_user
from app.api.ws_manager import ConnectionManager
from app.core.config import settings
from app.core.security import create_access_token
from app.database import get_db
from app.models import Tenant, User, UserRole, Category, MenuItem
from app.models.base import Base

ORIGIN = {"origin": "http://localhost:3000"}


@pytest.fixture
def realtime(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'sockets.sqlite'}"
    users = []

    async def seed():
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            for number in (1, 2):
                db.add(Tenant(id=number, tenant_id=f"ws-{number}", name="Socket test"))
                await db.flush()
                user = User(
                    id=number,
                    tenant_id=number,
                    email=f"ws{number}@example.com",
                    hashed_password="unused",
                    role=UserRole.OWNER,
                )
                db.add(user)
                users.append(user)
            db.add(Category(id=1, tenant_id=1, name="Meals"))
            await db.flush()
            db.add(
                MenuItem(
                    id=1,
                    tenant_id=1,
                    category_id=1,
                    name="Meal",
                    price=Decimal("10"),
                    cost_price=Decimal("2"),
                )
            )
            await db.commit()
        await engine.dispose()

    asyncio.run(seed())
    closed = []

    async def database():
        engine = create_async_engine(url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                yield db
        finally:
            await engine.dispose()
            closed.append(True)

    async def user():
        return users[0]

    manager = ConnectionManager()
    monkeypatch.setattr(ws, "connection_manager", manager)
    monkeypatch.setattr(sales, "connection_manager", manager)
    monkeypatch.setattr(ws, "get_db", database)
    monkeypatch.setattr(settings, "cors_origins", [ORIGIN["origin"]])
    app = FastAPI()
    app.include_router(ws.router, prefix="/api/v1")
    app.include_router(sales.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = user
    with TestClient(app) as client:
        yield client, manager, closed


def token(tenant=1, **overrides):
    claims = {
        "sub": f"ws{tenant}@example.com",
        "tenant_id": tenant,
        "token_version": 0,
        **overrides,
    }
    return create_access_token(claims)


def authorize(socket, value=None):
    socket.send_json({"event": "AUTH", "token": value or token()})
    assert socket.receive_json()["event"] == "CONNECTED"


def test_sale_event_contract_and_database_released(realtime):
    client, manager, closed = realtime
    with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
        authorize(socket)
        assert closed == [True]
        response = client.post(
            "/api/v1/sales", json={"items": [{"menu_item_id": 1, "quantity": 3}]}
        )
        assert response.status_code == 201
        event = socket.receive_json()
        assert event["event"] == "NEW_SALE"
        assert event["data"]["amount"] == 30
        assert event["data"]["item_count"] == 3
        assert event["tenant_id"] == 1 and event["timestamp"]
        socket.send_text("ping")
        assert socket.receive_json()["event"] == "PONG"
    assert not manager.active_connections


def test_real_application_routes(realtime):
    from app.main import create_app

    client = TestClient(create_app())
    with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
        authorize(socket)
    for path in ("/ws/ws", "/api/v1/ws/ws"):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(path, headers=ORIGIN):
                pass


def test_invalid_json_auth_timeout_expiry_and_unauthenticated_frames(
    realtime, monkeypatch
):
    client, _, _ = realtime
    for frame in ("not-json", "[]", '{"event":"AUTH","token":"invalid"}', '"ping"'):
        with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
            socket.send_text(frame)
            with pytest.raises(WebSocketDisconnect):
                socket.receive_json()
    monkeypatch.setattr(settings, "ws_auth_timeout_seconds", 0.02)
    with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()
    expired = create_access_token(
        {"sub": "ws1@example.com", "tenant_id": 1}, expires_delta=timedelta(seconds=-1)
    )
    with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
        socket.send_json({"event": "AUTH", "token": expired})
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()


def test_inactive_and_temporary_password_user_rejected(realtime, monkeypatch):
    for changes in ({"is_active": False}, {"must_change_password": True}):

        class FakeSession:
            async def scalar(self, statement):
                return User(
                    id=1,
                    tenant_id=1,
                    email="ws1@example.com",
                    token_version=0,
                    is_active=changes.get("is_active", True),
                    must_change_password=changes.get("must_change_password", False),
                )

        async def database():
            yield FakeSession()

        monkeypatch.setattr(ws, "get_db", database)
        with realtime[0].websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
            socket.send_json({"event": "AUTH", "token": token()})
            with pytest.raises(WebSocketDisconnect):
                socket.receive_json()


@pytest.mark.parametrize(
    "claims", [{"tenant_id": 2}, {"token_version": 2}, {"token_version": "0"}]
)
def test_mismatched_claims_rejected(realtime, claims):
    client, _, _ = realtime
    with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
        socket.send_json({"event": "AUTH", "token": token(**claims)})
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 1008


@pytest.mark.parametrize(
    "headers,path",
    [
        ({}, "/api/v1/ws"),
        ({"origin": "https://evil.example"}, "/api/v1/ws"),
        (ORIGIN, "/api/v1/ws?token=secret"),
    ],
)
def test_origin_and_query_credentials_rejected(realtime, headers, path):
    with pytest.raises(WebSocketDisconnect):
        with realtime[0].websocket_connect(path, headers=headers):
            pass


def test_oversized_frame_and_idle_timeout(realtime, monkeypatch):
    client, _, _ = realtime
    with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
        authorize(socket)
        socket.send_text("x" * (settings.ws_max_message_bytes + 1))
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 1009
    monkeypatch.setattr(settings, "ws_idle_timeout_seconds", 0.05)
    with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as socket:
        authorize(socket)
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()


def test_connection_caps_release_and_tenant_isolation(realtime, monkeypatch):
    client, manager, _ = realtime
    monkeypatch.setattr(settings, "ws_max_connections_per_user", 1)
    with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as first:
        authorize(first)
        with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as second:
            second.send_json({"event": "AUTH", "token": token()})
            with pytest.raises(WebSocketDisconnect) as error:
                second.receive_json()
            assert error.value.code == 1013
        with client.websocket_connect("/api/v1/ws", headers=ORIGIN) as other:
            authorize(other, token(2))
            client.post(
                "/api/v1/sales", json={"items": [{"menu_item_id": 1, "quantity": 1}]}
            )
            assert first.receive_json()["event"] == "NEW_SALE"
            other.send_text("ping")
            assert other.receive_json()["event"] == "PONG"
    assert not manager.active_connections


async def test_slow_and_failed_sockets_do_not_block_peers(monkeypatch):
    manager = ConnectionManager()
    fast, slow = AsyncMock(), AsyncMock()

    async def stall(*args):
        await asyncio.sleep(10)

    slow.send_json.side_effect = stall
    monkeypatch.setattr(settings, "ws_send_timeout_seconds", 0.02)
    await manager.connect(fast, 1, 1)
    await manager.connect(slow, 1, 2)
    assert await manager.broadcast_named_event(1, "NEW_SALE", {"amount": 10}) == 1
    assert slow not in manager.active_connections


async def test_redis_shares_broadcasts_and_global_caps(monkeypatch):
    import fakeredis.aioredis
    import fakeredis

    server = fakeredis.FakeServer()
    first, second = ConnectionManager(), ConnectionManager()
    monkeypatch.setattr(settings, "ws_max_connections_per_user", 1)
    try:
        await first.start(
            fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
        )
        await second.start(
            fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
        )
        socket = AsyncMock()
        assert await first.connect(socket, 1, 1)
        assert not await second.connect(AsyncMock(), 1, 1)
        await second.broadcast_named_event(1, "NEW_SALE", {"amount": 10})
        for _ in range(100):
            if socket.send_json.called:
                break
            await asyncio.sleep(0.01)
        assert socket.send_json.call_args.args[0]["data"]["amount"] == 10
        await first.disconnect(socket)
        assert await second.connect(AsyncMock(), 1, 1)
        monkeypatch.setattr(settings, "ws_max_connections_per_tenant", 1)
        assert not await first.connect(AsyncMock(), 1, 2)
        assert await first.connect(AsyncMock(), 2, 2)
    finally:
        await first.stop()
        await second.stop()


async def test_notification_outage_does_not_fail_committed_sale(realtime, monkeypatch):
    client, manager, _ = realtime
    monkeypatch.setattr(
        manager,
        "broadcast_named_event",
        AsyncMock(side_effect=RuntimeError("Redis unavailable")),
    )
    response = await asyncio.to_thread(
        client.post,
        "/api/v1/sales",
        json={"items": [{"menu_item_id": 1, "quantity": 1}]},
    )
    assert response.status_code == 201


def test_downloadable_csv_template_matches_import_contract():
    import csv
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "frontend/public/sales-import-template.csv"
    )
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert {row["order_id"] for row in rows} == {"EXAMPLE-1042"}
    assert all(
        row["payment_method"] == "upi"
        and Decimal(row["tax_amount"]) == Decimal("12.50")
        for row in rows
    )
    assert sum(
        Decimal(row["unit_price"]) * int(row["quantity"]) for row in rows
    ) == Decimal(rows[0]["total_amount"])
