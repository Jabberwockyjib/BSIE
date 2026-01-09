"""Transaction schema tests."""
import pytest
from datetime import date, datetime, timezone
from pydantic import ValidationError

from bsie.schemas.transactions import Transaction, Transactions, TransactionType
from bsie.schemas.base import Provenance


def test_transaction_valid():
    tx = Transaction(
        row_id="row_001",
        posted_date=date(2024, 1, 15),
        description="AMAZON PURCHASE",
        amount=-45.99,
        provenance=Provenance(
            page=1,
            bbox=[0.1, 0.2, 0.9, 0.25],
            source_pdf="stmt_abc123",
        ),
    )
    assert tx.amount == -45.99


def test_transaction_with_all_fields():
    tx = Transaction(
        row_id="row_001",
        row_index=0,
        posted_date=date(2024, 1, 15),
        effective_date=date(2024, 1, 14),
        description="CHECK #1234",
        amount=-500.00,
        balance=1500.00,
        check_number="1234",
        reference_number="REF123",
        transaction_type=TransactionType.DEBIT,
        provenance=Provenance(
            page=1,
            bbox=[0.1, 0.2, 0.9, 0.25],
            source_pdf="stmt_abc123",
        ),
    )
    assert tx.check_number == "1234"
    assert tx.transaction_type == TransactionType.DEBIT


def test_transactions_container():
    txs = Transactions(
        statement_id="stmt_abc123",
        template_id="chase_checking_v1",
        transactions=[
            Transaction(
                row_id="row_001",
                posted_date=date(2024, 1, 15),
                description="DEPOSIT",
                amount=1000.00,
                provenance=Provenance(
                    page=1,
                    bbox=[0.1, 0.2, 0.9, 0.25],
                    source_pdf="stmt_abc123",
                ),
            ),
            Transaction(
                row_id="row_002",
                posted_date=date(2024, 1, 16),
                description="WITHDRAWAL",
                amount=-200.00,
                provenance=Provenance(
                    page=1,
                    bbox=[0.1, 0.25, 0.9, 0.30],
                    source_pdf="stmt_abc123",
                ),
            ),
        ],
        extracted_at=datetime.now(timezone.utc),
    )
    assert len(txs.transactions) == 2


def test_transaction_requires_provenance():
    with pytest.raises(ValidationError):
        Transaction(
            row_id="row_001",
            posted_date=date(2024, 1, 15),
            description="TEST",
            amount=100.00,
            # Missing provenance
        )
