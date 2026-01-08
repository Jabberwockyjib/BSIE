"""Statement database model."""
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from bsie.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Statement(Base):
    """Bank statement record."""

    __tablename__ = "statements"

    # Primary key - statement_id
    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # File metadata
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Pipeline state
    current_state: Mapped[str] = mapped_column(String(50), index=True)
    state_version: Mapped[int] = mapped_column(Integer, default=1)

    # Template binding (set after TEMPLATE_SELECTED)
    template_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    template_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Error tracking
    error_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Artifacts paths (JSON object mapping artifact name to path)
    artifacts: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
