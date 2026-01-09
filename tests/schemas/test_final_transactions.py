"""Final transactions schema tests."""
import pytest
from datetime import date, datetime, timezone

from bsie.schemas.final_transactions import (
    FinalTransactions,
    FinalTransaction,
    FinalTransactionSource,
    CorrectionSource,
)
from bsie.schemas.base import Provenance


def test_final_transaction_from_original():
    tx = FinalTransaction(
        row_id="row_001",
        posted_date=date(2024, 1, 15),
        description="DEPOSIT",
        amount=1000.00,
        provenance=Provenance(
            page=1,
            bbox=[0.1, 0.2, 0.9, 0.25],
            source_pdf="stmt_abc123",
        ),
        correction_source=CorrectionSource.ORIGINAL,
    )
    assert tx.correction_source == CorrectionSource.ORIGINAL


def test_final_transaction_edited():
    tx = FinalTransaction(
        row_id="row_002",
        posted_date=date(2024, 1, 16),
        description="CORRECTED DESCRIPTION",
        amount=500.00,
        provenance=Provenance(
            page=1,
            bbox=[0.1, 0.3, 0.9, 0.35],
            source_pdf="stmt_abc123",
        ),
        correction_source=CorrectionSource.EDITED,
    )
    assert tx.correction_source == CorrectionSource.EDITED


def test_final_transactions_container():
    final = FinalTransactions(
        statement_id="stmt_abc123",
        transactions=[
            FinalTransaction(
                row_id="row_001",
                posted_date=date(2024, 1, 15),
                description="TEST",
                amount=100.00,
                provenance=Provenance(
                    page=1,
                    bbox=[0.1, 0.2, 0.9, 0.25],
                    source_pdf="stmt_abc123",
                ),
            ),
        ],
        source=FinalTransactionSource(
            raw_transactions_id="txn_abc123",
            correction_overlay_id=None,
            corrections_applied=0,
        ),
        finalized_at=datetime.now(timezone.utc),
    )
    assert final.source.corrections_applied == 0


def test_final_transactions_with_corrections():
    final = FinalTransactions(
        statement_id="stmt_abc123",
        transactions=[],
        source=FinalTransactionSource(
            raw_transactions_id="txn_abc123",
            correction_overlay_id="corr_xyz789",
            corrections_applied=3,
        ),
        finalized_at=datetime.now(timezone.utc),
    )
    assert final.source.correction_overlay_id == "corr_xyz789"
    assert final.source.corrections_applied == 3
