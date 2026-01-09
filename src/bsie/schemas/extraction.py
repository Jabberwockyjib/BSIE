"""Extraction result schema."""
from typing import Optional, List
from datetime import datetime
from enum import Enum

from bsie.schemas.base import BsieBaseModel


class ExtractionStatus(str, Enum):
    """Extraction status."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class ExtractionMethod(str, Enum):
    """Extraction method used."""
    CAMELOT_LATTICE = "camelot_lattice"
    CAMELOT_STREAM = "camelot_stream"
    TABULA_STREAM = "tabula_stream"
    PDFPLUMBER_COLUMNS = "pdfplumber_columns"


class MethodAttempt(BsieBaseModel):
    """Record of an extraction method attempt."""
    method: str
    success: bool
    rows_extracted: Optional[int] = None
    error: Optional[str] = None


class RowIssue(BsieBaseModel):
    """Issue with a specific row."""
    row_index: int
    issue: str
    severity: Optional[str] = None


class ExtractedBalances(BsieBaseModel):
    """Extracted balance information."""
    beginning_balance: Optional[float] = None
    ending_balance: Optional[float] = None
    beginning_balance_found: Optional[bool] = None
    ending_balance_found: Optional[bool] = None


class ExtractionResult(BsieBaseModel):
    """Schema for extraction_result.json artifact."""

    statement_id: str
    template_id: str
    status: ExtractionStatus
    extracted_at: datetime

    # Method details
    template_version: Optional[str] = None
    method_used: Optional[ExtractionMethod] = None
    methods_attempted: Optional[List[MethodAttempt]] = None

    # Results
    pages_processed: Optional[List[int]] = None
    tables_found: Optional[int] = None
    rows_extracted: Optional[int] = None
    rows_with_issues: Optional[List[RowIssue]] = None

    # Balances
    balances: Optional[ExtractedBalances] = None

    # Metadata
    warnings: Optional[List[str]] = None
    processing_time_ms: Optional[int] = None
