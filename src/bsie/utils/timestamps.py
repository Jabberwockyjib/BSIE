# src/bsie/utils/timestamps.py
"""Timestamp utilities."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def format_iso8601(dt: datetime) -> str:
    """Format datetime as ISO-8601 string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso8601(s: str) -> datetime:
    """Parse ISO-8601 string to datetime."""
    # Handle Z suffix
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
