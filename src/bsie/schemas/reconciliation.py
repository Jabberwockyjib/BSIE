"""Reconciliation schema."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from bsie.schemas.base import BsieBaseModel


class ReconciliationStatus(str, Enum):
    """Reconciliation status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    OVERRIDDEN = "overridden"


class ReconciliationType(str, Enum):
    """Type of reconciliation."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"


class BalanceDiscontinuity(BsieBaseModel):
    """Running balance discontinuity."""
    row_id: str
    expected: float
    actual: float


class RunningBalanceCheck(BsieBaseModel):
    """Running balance check results."""
    performed: bool
    passed: Optional[bool] = None
    discontinuities: Optional[List[Dict[str, Any]]] = None


class ReconciliationOverride(BsieBaseModel):
    """Manual override details."""
    overridden: bool
    reason: Optional[str] = None
    overridden_by: Optional[str] = None
    overridden_at: Optional[datetime] = None


class Reconciliation(BsieBaseModel):
    """Schema for reconciliation.json artifact."""

    statement_id: str
    status: ReconciliationStatus
    reconciled_at: datetime

    # Balance details
    reconciliation_type: Optional[ReconciliationType] = None
    beginning_balance: Optional[float] = None
    ending_balance: Optional[float] = None
    calculated_ending_balance: Optional[float] = None
    total_debits: Optional[float] = None
    total_credits: Optional[float] = None
    transaction_count: Optional[int] = None

    # Delta tracking
    delta_cents: Optional[int] = None
    tolerance_cents: Optional[int] = None
    within_tolerance: Optional[bool] = None

    # Running balance verification
    running_balance_check: Optional[RunningBalanceCheck] = None

    # Override
    override: Optional[ReconciliationOverride] = None

    # Notes
    notes: Optional[str] = None
