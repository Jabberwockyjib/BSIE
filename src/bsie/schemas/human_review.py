"""Human review schemas."""
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

from bsie.schemas.base import BsieBaseModel


class ReviewDecisionType(str, Enum):
    """Human review decision types."""
    APPROVE = "approve"
    APPROVE_WITH_CORRECTIONS = "approve_with_corrections"
    REQUEST_REPROCESSING = "request_reprocessing"
    REJECT = "reject"


class CorrectionType(str, Enum):
    """Type of correction."""
    EDIT = "edit"
    ADD = "add"
    DELETE = "delete"


class TransactionCorrection(BsieBaseModel):
    """Single transaction correction."""
    row_id: str
    correction_type: CorrectionType
    field: Optional[str] = None
    original_value: Optional[Any] = None
    corrected_value: Optional[Any] = None
    reason: Optional[str] = None


class CorrectionOverlay(BsieBaseModel):
    """Schema for correction_overlay.json artifact."""

    statement_id: str
    overlay_id: str
    reviewer_id: str
    corrections: List[TransactionCorrection]
    created_at: datetime

    # Metadata
    notes: Optional[str] = None


class HumanReviewDecision(BsieBaseModel):
    """Schema for human_review_decision.json artifact."""

    statement_id: str
    decision: ReviewDecisionType
    reviewer_id: str
    decided_at: datetime

    # For approve_with_corrections
    correction_overlay_id: Optional[str] = None

    # For request_reprocessing
    reprocessing_hints: Optional[str] = None

    # For reject
    rejection_reason: Optional[str] = None

    # Notes
    notes: Optional[str] = None
