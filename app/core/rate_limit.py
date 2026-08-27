"""In-Memory Rate Limiter for Login Brute-Force Protection.

Tracks failed login attempts per IP address. After a configurable number of
failures within a time window, further attempts are rejected with HTTP 429.

This is a single-process, in-memory implementation suitable for development
and small-scale deployments. For production multi-instance deployments,
swap this for a Redis-backed store.
"""

import time
from typing import Dict, Tuple
from collections import defaultdict

# Store: IP -> (count, window_start)
_failures: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

# Configuration
MAX_ATTEMPTS = 5        # failed attempts before lockout
WINDOW_SECONDS = 300    # 5-minute sliding window


def _get_ip(request) -> str:
    """Extract client IP from a Starlette Request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def record_failed_attempt(ip: str) -> int:
    """Record a failed login for this IP and return the current count."""
    now = time.time()
    count, start = _failures[ip]

    # Reset window if expired
    if now - start > WINDOW_SECONDS:
        count = 0
        start = now

    count += 1
    _failures[ip] = (count, start)
    return count


def clear_failures(ip: str) -> None:
    """Clear failure record on successful login."""
    _failures.pop(ip, None)


def is_rate_limited(ip: str) -> Tuple[bool, int]:
    """Check if the IP is currently rate-limited.

    Returns:
        Tuple of (is_limited, seconds_remaining)
    """
    count, start = _failures[ip]
    now = time.time()

    if now - start > WINDOW_SECONDS:
        return False, 0

    if count >= MAX_ATTEMPTS:
        remaining = int(WINDOW_SECONDS - (now - start))
        return True, max(remaining, 0)

    return False, 0
