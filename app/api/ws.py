"""Authenticate in the first frame, never in a URL; release the DB immediately."""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.deps import get_current_manager
from app.api.ws_manager import connection_manager
from app.core.config import settings
from app.core.security import decode_access_token
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def authenticate(token):
    claims = decode_access_token(token)
    if (
        not claims
        or type(claims.get("token_version")) is not int
        or type(claims.get("tenant_id")) is not int
    ):
        return None
    sessions = get_db()
    try:
        db = await anext(sessions)
        user = await db.scalar(
            select(User).where(
                User.email == claims.get("sub"), User.tenant_id == claims["tenant_id"]
            )
        )
        if (
            not user
            or not user.is_active
            or user.must_change_password
            or user.token_version != claims["token_version"]
        ):
            return None
        return (user.tenant_id, user.id, claims["exp"])
    finally:
        await sessions.aclose()


async def receive(websocket, timeout):
    message = await asyncio.wait_for(websocket.receive(), timeout)
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(message.get("code", 1000))
    text = message.get("text")
    if text is None or len(text.encode("utf-8")) > settings.ws_max_message_bytes:
        await websocket.close(code=1009)
        raise WebSocketDisconnect(1009)
    return text


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    if (
        websocket.headers.get("origin") not in settings.cors_origins
        or websocket.query_params
    ):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        frame = json.loads(await receive(websocket, settings.ws_auth_timeout_seconds))
        if (
            not isinstance(frame, dict)
            or frame.get("event") != "AUTH"
            or not isinstance(frame.get("token"), str)
        ):
            await websocket.close(code=1008)
            return
        identity = await authenticate(frame["token"])
        if identity is None:
            await websocket.close(code=1008)
            return
        tenant_id, user_id, expires = identity
        if not await connection_manager.connect(websocket, tenant_id, user_id):
            return
        if not await connection_manager.send(
            websocket, {"event": "CONNECTED", "data": {"tenant_id": tenant_id}}
        ):
            return
        while True:
            remaining = expires - time.time()
            if remaining <= 0:
                await websocket.close(code=4001)
                return
            try:
                text = await receive(
                    websocket, min(settings.ws_idle_timeout_seconds, remaining)
                )
            except TimeoutError:
                await websocket.close(code=4001 if time.time() >= expires else 1008)
                return
            if text != "ping":
                await websocket.close(code=1008)
                return
            if not await connection_manager.touch(websocket):
                return
            if not await connection_manager.send(
                websocket, {"event": "PONG", "data": {}}
            ):
                return
    except (ValueError, TypeError):
        await websocket.close(code=1008)
    except TimeoutError:
        await websocket.close(code=1008)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Realtime connection failed")
        await connection_manager._close(websocket, 1013)
    finally:
        await connection_manager.disconnect(websocket)


@router.get("/stats")
async def get_websocket_stats(user: User = Depends(get_current_manager)):
    return connection_manager.get_connection_count(user.tenant_id)
