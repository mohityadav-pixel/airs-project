from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, TypeDecorator, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UtcDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend.

    SQLite has no native timezone support, so values written as aware come back
    naive and every comparison with ``datetime.now(timezone.utc)`` raises. This
    normalises in both directions: stored as UTC, returned as UTC-aware,
    identically on SQLite and PostgreSQL.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None
                else value.astimezone(timezone.utc))


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(),
        nullable=False)
