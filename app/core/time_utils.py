"""Consistent timezone-aware UTC clock for persisted application timestamps."""

from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


def as_utc(value):
    """SQLite strips timezone information; interpret stored naive values as UTC."""
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )
