"""Error schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.errors import ExtractionError, ErrorCategory


def test_extraction_error_valid():
    error = ExtractionError(
        statement_id="stmt_abc123",
        error_code="E3001",
        error_category=ErrorCategory.EXTRACTION,
        message="No tables found in PDF",
        occurred_at=datetime.now(timezone.utc),
    )
    assert error.error_code == "E3001"


def test_error_code_pattern():
    # Valid pattern
    error = ExtractionError(
        statement_id="stmt_abc123",
        error_code="E1234",
        error_category=ErrorCategory.VALIDATION,
        message="Test error",
        occurred_at=datetime.now(timezone.utc),
    )
    assert error.error_code == "E1234"

    # Invalid pattern
    with pytest.raises(ValidationError):
        ExtractionError(
            statement_id="stmt_abc123",
            error_code="INVALID",
            error_category=ErrorCategory.VALIDATION,
            message="Test error",
            occurred_at=datetime.now(timezone.utc),
        )


def test_extraction_error_with_details():
    error = ExtractionError(
        statement_id="stmt_abc123",
        error_code="E3002",
        error_category=ErrorCategory.EXTRACTION,
        message="Partial extraction - missing columns",
        occurred_at=datetime.now(timezone.utc),
        template_id="chase_checking_v1",
        method_attempted="camelot_stream",
        page=2,
        recoverable=True,
        suggested_actions=["Try different extraction method", "Check template configuration"],
        details={"missing_columns": ["balance", "date"]},
    )
    assert error.recoverable is True
    assert len(error.suggested_actions) == 2


def test_error_category_enum():
    assert ErrorCategory.VALIDATION == "VALIDATION"
    assert ErrorCategory.TRANSIENT == "TRANSIENT"
    assert ErrorCategory.EXTRACTION == "EXTRACTION"
    assert ErrorCategory.RECONCILIATION == "RECONCILIATION"
    assert ErrorCategory.CONFIGURATION == "CONFIGURATION"
    assert ErrorCategory.SYSTEM == "SYSTEM"
