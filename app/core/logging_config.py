"""Structured Logging Configuration

Provides a JSON-formatted logging setup that works well with log aggregators
(CloudWatch, Datadog, Papertrail, Loki, etc.) and an access-log middleware
for HTTP request telemetry.

Usage:
    from app.core.logging_config import setup_logging, setup_app_logger
    setup_logging()
    logger = setup_app_logger("opsmind.my_module")
    logger.info("hello", extra={"user_id": 123})
"""

import json
import logging
import time
from typing import Dict, Any, Optional

from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

_configured = False


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Merge any structured extra fields supplied by callers
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Configure the root logger with a JSON formatter and console handler.

    Safe to call multiple times (idempotent).
    """
    global _configured
    if _configured:
        return

    level = logging.DEBUG if settings.debug else logging.INFO

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers on repeated instantiation
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.StreamHandler)]
    root.addHandler(handler)

    # Keep uvicorn/starlette noisy logs at WARNING unless debugging
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.DEBUG if settings.debug else logging.WARNING)

    _configured = True


def setup_app_logger(name: str) -> logging.Logger:
    """Return (create) a namespaced logger with structured extras support.

    The returned logger is a subclass that forwards any kwargs under `extra`
    into the JSON output via a dedicated field.
    """
    setup_logging()
    logger = logging.getLogger(name)
    return logger


class _StructuredLogger(logging.Logger):
    """Logger that converts provided ``**context`` into structured log fields."""

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **context):
        if context:
            base_extra = dict(extra or {})
            combined = dict(base_extra.get("extra_fields") or {})
            combined.update(context)
            base_extra["extra_fields"] = combined
            extra = base_extra
        super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)


class AccessLogMiddleware:
    """Starlette middleware that logs one structured entry per HTTP request."""

    def __init__(self, app):
        self.app = app
        self.logger = setup_app_logger("opsmind.access")
        try:
            # Prefer the structured subclass for key=value context
            self.logger = logging.getLogger("opsmind.access")
            logging.setLoggerClass(_StructuredLogger)
        except Exception:
            pass

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        start = time.perf_counter()

        status_code = {"value": 500}
        body_bytes = {"value": 0}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code["value"] = message["status"]
            elif message["type"] == "http.response.body":
                body_bytes["value"] += len(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            self.logger.exception("request failed", extra={"extra_fields": {"method": request.method, "path": request.url.path}})
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.logger.info(
                "request",
                extra={"extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code["value"],
                    "duration_ms": round(duration_ms, 2),
                    "bytes_out": body_bytes["value"],
                }},
            )
