"""Template metadata model."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column

from bsie.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TemplateMetadata(Base):
    """Template metadata for Postgres queries."""

    __tablename__ = "template_metadata"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Template identification
    template_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(32))
    bank_family: Mapped[str] = mapped_column(String(64), index=True)
    statement_type: Mapped[str] = mapped_column(String(32), index=True)
    segment: Mapped[str] = mapped_column(String(32), index=True)

    # Git tracking
    git_sha: Mapped[str] = mapped_column(String(40))
    file_path: Mapped[str] = mapped_column(String(512))

    # Status
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft, stable, deprecated

    # Statistics
    statements_processed: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    promoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
