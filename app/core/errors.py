"""Safe client errors with server-side correlation references."""

import logging
from uuid import uuid4
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler

logger = logging.getLogger(__name__)


def safe_error_detail(message="Unable to complete request"):
    reference = uuid4().hex
    logger.exception("Request failed; correlation_id=%s", reference)
    return f"{message}. Reference: {reference}"


async def unexpected_error_handler(request, exc):
    reference = uuid4().hex
    logger.error(
        "Unhandled request error; correlation_id=%s",
        reference,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "correlation_id": reference},
        headers={"X-Correlation-ID": reference},
    )


async def safe_http_error_handler(request, exc):
    """Also sanitize service failures forwarded as HTTPException details."""
    if exc.status_code < 500:
        return await http_exception_handler(request, exc)
    reference = uuid4().hex
    logger.error(
        "HTTP service error; correlation_id=%s",
        reference,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    headers = dict(exc.headers or {})
    headers["X-Correlation-ID"] = reference
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "detail": f"Service temporarily unavailable. Reference: {reference}",
            "correlation_id": reference,
        },
    )
