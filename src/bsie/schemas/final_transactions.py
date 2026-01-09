"""Final transactions schema."""
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

from bsie.schemas.base import BsieBaseModel, Provenance


class CorrectionSource(str, Enum):
    """Source of the transaction data."""
    ORIGINAL = "original"
    EDITED = "edited"
    ADDED = "added"
    MERGED = "merged"


class FinalTransaction(BsieBaseModel):
    """Single final transaction."""
    row_id: str
    posted_date: date
    description: str
    amount: float
    provenance: Provenance

    # Optional fields
    balance: Optional[float] = None
    correction_source: Optional[CorrectionSource] = None


class FinalTransactionSource(BsieBaseModel):
    """Source information for final transactions."""
    raw_transactions_id: str
    correction_overlay_id: Optional[str] = None
    corrections_applied: int = 0


class FinalTransactionSummary(BsieBaseModel):
    """Summary of final transactions."""
    total_transactions: Optional[int] = None
    total_debits: Optional[float] = None
    total_credits: Optional[float] = None
    net_change: Optional[float] = None


class FinalTransactions(BsieBaseModel):
    """Schema for final_transactions.json artifact."""

    statement_id: str
    transactions: List[FinalTransaction]
    source: FinalTransactionSource
    finalized_at: datetime

    # Optional summary
    summary: Optional[FinalTransactionSummary] = None
