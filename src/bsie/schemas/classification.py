"""Classification schema."""
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class StatementType(str, Enum):
    """Statement type enumeration."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"


class Segment(str, Enum):
    """Customer segment enumeration."""
    PERSONAL = "personal"
    BUSINESS = "business"
    UNKNOWN = "unknown"


class CandidateTemplate(BsieBaseModel):
    """Candidate template match."""

    template_id: str
    version: str
    score: float = Field(..., ge=0.0, le=1.0)
    factors: Optional[Dict[str, float]] = None


class Classification(BsieBaseModel):
    """Schema for classification.json artifact."""

    statement_id: str
    bank_family: str
    statement_type: StatementType
    segment: Segment
    layout_fingerprint: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    candidate_templates: List[CandidateTemplate]
    classified_at: datetime

    # Optional confidence breakdowns
    bank_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    type_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    segment_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    classifier_version: Optional[str] = None
