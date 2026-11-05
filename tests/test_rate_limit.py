import asyncio
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.requests import Request
import pytest

from app.core.config import settings
from app.core.rate_limit import MemoryStore, RedisStore, RateLimited, _get_ip, limit_request


def request(peer, forwarded):
    return Request({"type": "http", "client": (peer, 1234), "headers": [
        (b"x-forwarded-for", forwarded.encode())], "method": "GET", "path": "/"})


@pytest.mark.parametrize("peer,forwarded,expected", [
    ("192.0.2.1", "203.0.113.5", "192.0.2.1"),
    ("10.0.0.1", "203.0.113.5, 10.0.0.2", "203.0.113.5"),
    ("10.0.0.1", "203.0.113.99, 192.0.2.2", "192.0.2.2"),
    ("10.0.0.1", "invalid", "10.0.0.1"),
    ("::1", "2001:db8::3", "2001:db8::3"),
])
def test_proxy_trust_walks_from_direct_peer(monkeypatch, peer, forwarded, expected):
    monkeypatch.setattr(settings, "trusted_proxies", ["10.0.0.0/8", "::1/128"])
    assert _get_ip(request(peer, forwarded)) == expected


async def test_memory_limits_are_atomic_and_success_does_not_clear_other_failures():
    store = MemoryStore()
    async def attempt():
        try:
            return await store.acquire(["ip", "account"], 5, 300)
        except RateLimited:
            return None
    results = await asyncio.gather(*(attempt() for _ in range(20)))
    leases = [result for result in results if result]
    assert len(leases) == 5
    await store.release(leases[0])
    assert store.entries["ip"][0] == 4
    await store.acquire(["ip", "account"], 5, 300)
    with pytest.raises(RateLimited):
        await store.acquire(["ip", "account"], 5, 300)


async def test_memory_expiry_cleanup_capacity_and_old_success_reservations():
    now = [0]
    store = MemoryStore(max_keys=2, clock=lambda: now[0])
    old = await store.acquire(["ip", "account"], 1, 5)
    with pytest.raises(RateLimited):
        await store.acquire(["new-account"], 1, 5)
    assert len(store.entries) == 2
    now[0] = 6
    await store.acquire(["ip"], 1, 5)
    await store.release(old)
    assert store.entries["ip"][0] == 1
    assert "account" not in store.entries


async def test_configured_redis_failure_is_closed(monkeypatch):
    monkeypatch.setattr(settings, "redis_url", "redis://unused")
    with patch.object(RedisStore, "acquire", AsyncMock(side_effect=ConnectionError)):
        with pytest.raises(HTTPException) as error:
            await limit_request(request("192.0.2.1", ""), "login", "unknown@example.com")
    assert error.value.status_code == 503


async def test_redis_lua_shares_atomic_limits_across_workers(monkeypatch):
    import fakeredis
    from fakeredis.aioredis import FakeRedis

    server = fakeredis.FakeServer()
    monkeypatch.setattr(RedisStore, "client", lambda self: FakeRedis(
        server=server, decode_responses=True))
    first, second = RedisStore("redis://one"), RedisStore("redis://two")
    keys = ["opsmind:test:ip", "opsmind:test:account"]
    reservations = []
    async def attempt(index):
        store = first if index % 2 else second
        try:
            reservations.append(await store.acquire(keys, 5, 300))
        except RateLimited:
            pass
    await asyncio.gather(*(attempt(index) for index in range(20)))
    assert len(reservations) == 5
    async with FakeRedis(server=server, decode_responses=True) as client:
        assert 0 < await client.ttl(keys[0]) <= 300
        assert await client.hget(keys[0], "count") == "5"
    await second.release(reservations[0])
    await first.acquire(keys, 5, 300)
    with pytest.raises(RateLimited):
        await second.acquire(keys, 5, 300)
