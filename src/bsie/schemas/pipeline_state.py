"""Pipeline state schema."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from bsie.schemas.base import BsieBaseModel


class PipelineStateEnum(str, Enum):
    """All valid pipeline states."""
    # Phase 1 MVP states
    UPLOADED = "UPLOADED"
    INGESTED = "INGESTED"
    CLASSIFIED = "CLASSIFIED"
    ROUTED = "ROUTED"
    TEMPLATE_SELECTED = "TEMPLATE_SELECTED"
    TEMPLATE_MISSING = "TEMPLATE_MISSING"
    EXTRACTION_READY = "EXTRACTION_READY"
    EXTRACTING = "EXTRACTING"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    RECONCILING = "RECONCILING"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"

    # Phase 2+ states
    TEMPLATE_DRAFTING = "TEMPLATE_DRAFTING"
    TEMPLATE_DRAFTED = "TEMPLATE_DRAFTED"
    TEMPLATE_REVIEW = "TEMPLATE_REVIEW"
    TEMPLATE_REVIEW_FAILED = "TEMPLATE_REVIEW_FAILED"
    TEMPLATE_APPROVED = "TEMPLATE_APPROVED"


class StateHistoryEntry(BsieBaseModel):
    """Single state history entry."""
    state: str
    entered_at: datetime
    exited_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    trigger: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TemplateBinding(BsieBaseModel):
    """Template binding information."""
    template_id: str
    template_version: str
    bound_at: datetime


class ErrorInfo(BsieBaseModel):
    """Error information."""
    code: str
    message: str
    occurred_at: datetime


class PipelineState(BsieBaseModel):
    """Schema for pipeline_state.json artifact."""

    statement_id: str
    current_state: PipelineStateEnum
    state_history: List[StateHistoryEntry]
    updated_at: datetime

    # Artifacts
    artifacts: Optional[Dict[str, str]] = None

    # Template binding
    template_binding: Optional[TemplateBinding] = None

    # Error info
    error: Optional[ErrorInfo] = None

    # Retry tracking
    retry_count: int = 0

    # Timestamps
    created_at: Optional[datetime] = None
