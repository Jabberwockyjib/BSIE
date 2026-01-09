"""State types tests."""
import pytest
from datetime import datetime, timezone

from bsie.state.types import TransitionResult, TransitionError


def test_transition_result_success():
    result = TransitionResult(
        success=True,
        previous_state="UPLOADED",
        current_state="INGESTED",
        statement_id="stmt_abc123",
        timestamp=datetime.now(timezone.utc),
    )
    assert result.success is True
    assert result.error is None


def test_transition_result_failure():
    result = TransitionResult(
        success=False,
        previous_state="UPLOADED",
        current_state="UPLOADED",
        statement_id="stmt_abc123",
        timestamp=datetime.now(timezone.utc),
        error="Invalid transition: UPLOADED -> COMPLETED",
    )
    assert result.success is False
    assert result.error is not None


def test_transition_error_categories():
    assert TransitionError.INVALID_TRANSITION.value == "invalid_transition"
    assert TransitionError.MISSING_ARTIFACT.value == "missing_artifact"
    assert TransitionError.VALIDATION_FAILED.value == "validation_failed"
    assert TransitionError.CONCURRENT_MODIFICATION.value == "concurrent_modification"
