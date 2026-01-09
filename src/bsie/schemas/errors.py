"""Error schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class ErrorCategory(str, Enum):
    """Error category for classification."""
    VALIDATION = "VALIDATION"
    TRANSIENT = "TRANSIENT"
    EXTRACTION = "EXTRACTION"
    RECONCILIATION = "RECONCILIATION"
    CONFIGURATION = "CONFIGURATION"
    SYSTEM = "SYSTEM"


class ExtractionError(BsieBaseModel):
    """Schema for extraction_error.json artifact."""

    statement_id: str
    error_code: str = Field(..., pattern=r"^E[0-9]{4}$")
    error_category: ErrorCategory
    message: str
    occurred_at: datetime

    # Context
    template_id: Optional[str] = None
    method_attempted: Optional[str] = None
    page: Optional[int] = None

    # Recovery
    recoverable: Optional[bool] = None
    suggested_actions: Optional[List[str]] = None

    # Additional details
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
