"""Reconciliation schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.reconciliation import (
    Reconciliation,
    ReconciliationStatus,
    ReconciliationType,
    RunningBalanceCheck,
)


def test_reconciliation_pass():
    recon = Reconciliation(
        statement_id="stmt_abc123",
        status=ReconciliationStatus.PASS,
        reconciled_at=datetime.now(timezone.utc),
        beginning_balance=1000.00,
        ending_balance=1500.00,
        calculated_ending_balance=1500.00,
        total_debits=-500.00,
        total_credits=1000.00,
        transaction_count=10,
        delta_cents=0,
        tolerance_cents=2,
        within_tolerance=True,
    )
    assert recon.status == ReconciliationStatus.PASS
    assert recon.within_tolerance is True


def test_reconciliation_fail():
    recon = Reconciliation(
        statement_id="stmt_abc123",
        status=ReconciliationStatus.FAIL,
        reconciled_at=datetime.now(timezone.utc),
        beginning_balance=1000.00,
        ending_balance=1500.00,
        calculated_ending_balance=1495.00,
        delta_cents=500,  # $5.00 off
        tolerance_cents=2,
        within_tolerance=False,
    )
    assert recon.status == ReconciliationStatus.FAIL


def test_reconciliation_with_running_balance():
    recon = Reconciliation(
        statement_id="stmt_abc123",
        status=ReconciliationStatus.WARNING,
        reconciled_at=datetime.now(timezone.utc),
        running_balance_check=RunningBalanceCheck(
            performed=True,
            passed=False,
            discontinuities=[
                {"row_id": "row_005", "expected": 1200.00, "actual": 1195.00},
            ],
        ),
    )
    assert recon.running_balance_check.passed is False


def test_reconciliation_status_enum():
    assert ReconciliationStatus.PASS == "pass"
    assert ReconciliationStatus.FAIL == "fail"
    assert ReconciliationStatus.WARNING == "warning"
    assert ReconciliationStatus.OVERRIDDEN == "overridden"
