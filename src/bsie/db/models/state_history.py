"""State history model for audit trail."""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from bsie.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_id() -> str:
    return str(uuid4())


class StateHistory(Base):
    """Record of state transitions for audit trail."""

    __tablename__ = "state_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    statement_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("statements.id"), index=True
    )

    # Transition details
    from_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_state: Mapped[str] = mapped_column(String(50))
    trigger: Mapped[str] = mapped_column(String(100))

    # Metadata
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    artifacts_created: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    transition_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Duration tracking
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
