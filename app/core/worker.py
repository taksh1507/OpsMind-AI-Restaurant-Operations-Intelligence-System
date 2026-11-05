"""Gunicorn worker with bounded WebSocket transport buffers."""

from uvicorn.workers import UvicornWorker
from app.core.config import settings


class OpsMindWorker(UvicornWorker):
    CONFIG_KWARGS = {
        **UvicornWorker.CONFIG_KWARGS,
        "ws_max_size": settings.ws_max_message_bytes,
        "ws_max_queue": 4,
        "ws_ping_interval": 20,
        "ws_ping_timeout": 20,
    }
