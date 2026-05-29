"""Base model utilities."""
from datetime import datetime, timezone
from db import Base


def utc_now() -> datetime:
    """Get current UTC time as timezone-naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


__all__ = ["Base", "utc_now"]
