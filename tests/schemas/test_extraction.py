"""Extraction result schema tests."""
import pytest
from datetime import datetime, timezone

from bsie.schemas.extraction import (
    ExtractionResult,
    ExtractionStatus,
    ExtractionMethod,
    MethodAttempt,
    ExtractedBalances,
)


def test_extraction_result_complete():
    result = ExtractionResult(
        statement_id="stmt_abc123",
        template_id="chase_checking_v1",
        status=ExtractionStatus.COMPLETE,
        extracted_at=datetime.now(timezone.utc),
        method_used=ExtractionMethod.CAMELOT_STREAM,
        pages_processed=[1, 2, 3],
        tables_found=2,
        rows_extracted=45,
    )
    assert result.status == ExtractionStatus.COMPLETE
    assert result.rows_extracted == 45


def test_extraction_result_with_balances():
    result = ExtractionResult(
        statement_id="stmt_abc123",
        template_id="chase_checking_v1",
        status=ExtractionStatus.COMPLETE,
        extracted_at=datetime.now(timezone.utc),
        balances=ExtractedBalances(
            beginning_balance=1000.00,
            ending_balance=1500.00,
            beginning_balance_found=True,
            ending_balance_found=True,
        ),
    )
    assert result.balances.beginning_balance == 1000.00


def test_extraction_result_with_method_attempts():
    result = ExtractionResult(
        statement_id="stmt_abc123",
        template_id="chase_checking_v1",
        status=ExtractionStatus.COMPLETE,
        extracted_at=datetime.now(timezone.utc),
        method_used=ExtractionMethod.CAMELOT_STREAM,
        methods_attempted=[
            MethodAttempt(
                method="camelot_lattice",
                success=False,
                rows_extracted=0,
                error="No tables found with lattice detection",
            ),
            MethodAttempt(
                method="camelot_stream",
                success=True,
                rows_extracted=45,
            ),
        ],
    )
    assert len(result.methods_attempted) == 2


def test_extraction_status_enum():
    assert ExtractionStatus.COMPLETE == "complete"
    assert ExtractionStatus.PARTIAL == "partial"
    assert ExtractionStatus.FAILED == "failed"
