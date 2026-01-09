"""Transaction schemas."""
from typing import Optional, List, Dict
from datetime import date, datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel, Provenance


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    DEBIT = "debit"
    CREDIT = "credit"
    UNKNOWN = "unknown"


class RawData(BsieBaseModel):
    """Raw extraction data for debugging."""
    raw_row_text: Optional[str] = None
    raw_columns: Optional[List[str]] = None


class Transaction(BsieBaseModel):
    """Single transaction record."""

    row_id: str
    posted_date: date
    description: str
    amount: float
    provenance: Provenance

    # Optional fields
    row_index: Optional[int] = None
    effective_date: Optional[date] = None
    balance: Optional[float] = None
    check_number: Optional[str] = None
    reference_number: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    category: Optional[str] = None
    raw: Optional[RawData] = None


class TransactionSummary(BsieBaseModel):
    """Summary statistics for transactions."""
    total_transactions: Optional[int] = None
    total_debits: Optional[float] = None
    total_credits: Optional[float] = None
    date_range: Optional[Dict[str, date]] = None


class Transactions(BsieBaseModel):
    """Schema for transactions.json artifact."""

    statement_id: str
    template_id: str
    transactions: List[Transaction]
    extracted_at: datetime

    # Optional fields
    template_version: Optional[str] = None
    summary: Optional[TransactionSummary] = None
