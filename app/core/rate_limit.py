"""Atomic auth rate limits: Redis across workers, bounded memory otherwise."""

from dataclasses import dataclass
import hashlib
import hmac
from ipaddress import ip_address, ip_network
import logging
import math
import threading
import time
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300
POLICIES = {
    "login": (MAX_ATTEMPTS, WINDOW_SECONDS),
    "register": (5, 3600),
    "refresh": (30, 60),
    "change-password": (5, 300),
    "logout-all": (5, 300),
}


class RateLimited(Exception):
    def __init__(self, retry_after):
        self.retry_after = max(1, math.ceil(retry_after))


def _get_ip(request) -> str:
    """Walk XFF from the trusted peer backwards to the first untrusted hop."""
    peer = request.client.host if request and request.client else "unknown"
    try:
        address = ip_address(peer)
    except ValueError:
        return peer
    networks = [ip_network(value, strict=False) for value in settings.trusted_proxies]

    def trusted(value):
        return any(value in network for network in networks)

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded or not trusted(address):
        return str(address)
    hops = forwarded.split(",")
    if len(hops) > 20:
        return str(address)
    try:
        parsed = [ip_address(hop.strip()) for hop in hops]
    except ValueError:
        return str(address)
    for hop in reversed(parsed):
        if not trusted(address):
            break
        address = hop
    return str(address)


class MemoryStore:
    """Fixed windows, periodic expiry cleanup, hard capacity and atomic keys."""

    def __init__(self, max_keys=10000, clock=time.monotonic):
        self.entries = {}
        self.max_keys = max_keys
        self.clock = clock
        self.lock = threading.Lock()
        self.next_cleanup = 0

    async def acquire(self, keys, limit, window):
        with self.lock:
            now = self.clock()
            if now >= self.next_cleanup or len(self.entries) >= self.max_keys:
                self.entries = {k: v for k, v in self.entries.items() if v[1] > now}
                self.next_cleanup = now + 30
            for key in keys:
                count, expiry = self.entries.get(key, (0, now + window))
                if expiry > now and count >= limit:
                    raise RateLimited(expiry - now)
            new_keys = sum(key not in self.entries for key in keys)
            if len(self.entries) + new_keys > self.max_keys:
                # Never evict an active lockout to admit an attacker-chosen key.
                raise RateLimited(30)
            lease = {}
            for key in keys:
                count, expiry = self.entries.get(key, (0, now + window))
                if expiry <= now:
                    count, expiry = 0, now + window
                self.entries[key] = (count + 1, expiry)
                lease[key] = expiry
            return lease

    async def release(self, lease):
        with self.lock:
            for key, expected in lease.items():
                if key in self.entries:
                    count, expiry = self.entries[key]
                    if expiry == expected:
                        self.entries[key] = (max(0, count - 1), expiry)


# Each multi-key check/increment/TTL is a single operation across all workers.
_ACQUIRE = """
local retry = 0
for _, key in ipairs(KEYS) do
  if tonumber(redis.call('HGET', key, 'count') or '0') >= tonumber(ARGV[1]) then
    retry = math.max(retry, redis.call('TTL', key), 1)
  end
end
if retry > 0 then return {0, retry} end
local result = {1}
for _, key in ipairs(KEYS) do
  if redis.call('EXISTS', key) == 0 then
    redis.call('HSET', key, 'count', 0, 'window', ARGV[3])
    redis.call('EXPIRE', key, ARGV[2])
  end
  redis.call('HINCRBY', key, 'count', 1)
  table.insert(result, redis.call('HGET', key, 'window'))
end
return result
"""
_RELEASE = """
for index, key in ipairs(KEYS) do
  if redis.call('HGET', key, 'window') == ARGV[index] then
    local count = tonumber(redis.call('HGET', key, 'count') or '0')
    if count > 0 then redis.call('HINCRBY', key, 'count', -1) end
  end
end
return 1
"""


class RedisStore:
    def __init__(self, url):
        self.url = url

    def client(self):
        from redis.asyncio import Redis

        return Redis.from_url(
            self.url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )

    async def acquire(self, keys, limit, window):
        async with self.client() as client:
            result = await client.eval(_ACQUIRE, len(keys), *keys, limit, window, uuid4().hex)
        if int(result[0]) == 0:
            raise RateLimited(int(result[1]))
        return dict(zip(keys, result[1:]))

    async def release(self, lease):
        async with self.client() as client:
            await client.eval(_RELEASE, len(lease), *lease, *lease.values())


_memory_store = MemoryStore()


@dataclass
class Reservation:
    store: object
    windows: dict

    async def release(self):
        try:
            await self.store.release(self.windows)
        except Exception:
            # Retaining the attempt on a release failure is conservative.
            logger.exception("Could not release successful login reservation")


async def limit_request(request, action, account=None):
    limit, window = POLICIES[action]
    subjects = [f"ip:{_get_ip(request)}"]
    if account is not None:
        subjects.append(f"account:{str(account).strip().casefold()}")
    keys = [
        "opsmind:auth:{limits}:" + action + ":" + hmac.new(
            settings.secret_key.encode(), subject.encode(), hashlib.sha256
        ).hexdigest()
        for subject in subjects
    ]
    store = RedisStore(settings.redis_url) if settings.redis_url else _memory_store
    if store is _memory_store:
        store.max_keys = settings.rate_limit_max_keys
    try:
        windows = await store.acquire(keys, limit, window)
    except RateLimited as error:
        raise HTTPException(
            status_code=429, detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except Exception as error:
        # A Redis outage must never disable the shared rate limit silently.
        logger.exception("Authentication rate-limit store unavailable")
        raise HTTPException(status_code=503, detail="Authentication temporarily unavailable") from error
    return Reservation(store, windows)
