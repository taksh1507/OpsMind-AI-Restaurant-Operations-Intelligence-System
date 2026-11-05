"""Tenant-isolated broadcasts; Redis shares events and connection leases."""

import asyncio
import json
import logging
import time
from uuid import uuid4

from app.core.config import settings
from app.core.time_utils import utc_now

logger = logging.getLogger(__name__)
CHANNEL = "opsmind:ws:events"
LEASE = """
local now = tonumber(ARGV[1])
for _, key in ipairs(KEYS) do redis.call('ZREMRANGEBYSCORE', key, '-inf', now) end
if ARGV[6] == 'new' or not redis.call('ZSCORE', KEYS[1], ARGV[3]) then
  if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[4]) or
     redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[5]) then return 0 end
end
for _, key in ipairs(KEYS) do
 redis.call('ZADD', key, ARGV[2], ARGV[3]); redis.call('EXPIRE', key, ARGV[7])
end
return 1
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.redis = None
        self.pubsub = None
        self.listener = None
        self.available = False

    async def start(self, redis_client=None):
        if not settings.redis_url and redis_client is None:
            return
        if redis_client is None:
            from redis.asyncio import from_url

            redis_client = from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
        self.redis = redis_client
        await self.redis.ping()
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(CHANNEL)
        self.available = True
        self.listener = asyncio.create_task(self._listen())

    async def stop(self):
        self.available = False
        if self.listener:
            self.listener.cancel()
            await asyncio.gather(self.listener, return_exceptions=True)
            self.listener = None
        for ws in list(self.active_connections):
            await self.disconnect(ws)
            await self._close(ws, 1001)
        if self.pubsub:
            await self.pubsub.aclose()
            self.pubsub = None
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    async def _listen(self):
        try:
            async for item in self.pubsub.listen():
                if item["type"] != "message":
                    continue
                try:
                    message = json.loads(item["data"])
                    if (
                        isinstance(message, dict)
                        and type(message.get("tenant_id")) is int
                        and isinstance(message.get("data"), dict)
                    ):
                        await self._broadcast_local(message["tenant_id"], message)
                except (ValueError, TypeError, KeyError):
                    logger.warning("Discarded invalid realtime event")
        except asyncio.CancelledError:
            raise
        except Exception:
            self.available = False
            logger.exception("Realtime Redis subscription failed")
            for ws in list(self.active_connections):
                await self.disconnect(ws)
                await self._close(ws, 1013)

    @staticmethod
    async def _close(ws, code):
        try:
            await asyncio.wait_for(
                ws.close(code=code), settings.ws_send_timeout_seconds
            )
        except Exception:
            pass

    def _keys(self, record):
        tenant, user, lease = record
        return [f"opsmind:ws:tenant:{tenant}", f"opsmind:ws:user:{tenant}:{user}"]

    async def _lease(self, record, mode):
        now = time.time()
        ttl = max(10, int(settings.ws_idle_timeout_seconds * 2))
        return await self.redis.eval(
            LEASE,
            2,
            *self._keys(record),
            now,
            now + ttl,
            record[2],
            settings.ws_max_connections_per_tenant,
            settings.ws_max_connections_per_user,
            mode,
            ttl,
        )

    async def connect(self, websocket, tenant_id, user_id):
        record = (tenant_id, user_id, uuid4().hex)
        if self.redis:
            if not self.available:
                raise RuntimeError("Realtime Redis subscriber is unavailable")
            allowed = await self._lease(record, "new")
        else:
            if settings.redis_url:
                raise RuntimeError("Realtime Redis is unavailable")
            allowed = (
                sum(r[0] == tenant_id for r in self.active_connections.values())
                < settings.ws_max_connections_per_tenant
                and sum(
                    r[:2] == (tenant_id, user_id)
                    for r in self.active_connections.values()
                )
                < settings.ws_max_connections_per_user
            )
        if not allowed:
            await self._close(websocket, 1013)
            return False
        self.active_connections[websocket] = record
        return True

    async def touch(self, websocket):
        record = self.active_connections.get(websocket)
        if not record:
            return False
        if record and self.redis:
            if not await self._lease(record, "touch"):
                await self.disconnect(websocket)
                await self._close(websocket, 1013)
                return False
        return True

    async def disconnect(self, websocket, tenant_id=None):
        record = self.active_connections.pop(websocket, None)
        if record and self.redis:
            try:
                async with self.redis.pipeline(transaction=True) as pipe:
                    for key in self._keys(record):
                        pipe.zrem(key, record[2])
                    await pipe.execute()
            except Exception:
                logger.exception("Could not release realtime lease; it will expire")

    async def send(self, websocket, message):
        try:
            await asyncio.wait_for(
                websocket.send_json(message), settings.ws_send_timeout_seconds
            )
            return True
        except Exception:
            await self.disconnect(websocket)
            await self._close(websocket, 1013)
            return False

    async def _broadcast_local(self, tenant_id, message):
        sockets = [
            ws
            for ws, record in list(self.active_connections.items())
            if record[0] == tenant_id
        ]
        return sum(await asyncio.gather(*(self.send(ws, message) for ws in sockets)))

    async def broadcast_named_event(self, tenant_id, event_type, data=None, **kwargs):
        message = {
            "event": event_type,
            "data": {**(data or {}), **kwargs},
            "tenant_id": tenant_id,
            "timestamp": utc_now().isoformat(),
        }
        if self.redis:
            return await self.redis.publish(CHANNEL, json.dumps(message))
        if settings.redis_url:
            raise RuntimeError("Realtime Redis is unavailable")
        return await self._broadcast_local(tenant_id, message)

    def get_connection_count(self, tenant_id):
        return {
            "tenant_id": tenant_id,
            "connections": sum(
                r[0] == tenant_id for r in self.active_connections.values()
            ),
            "scope": "this_worker",
        }


connection_manager = ConnectionManager()
