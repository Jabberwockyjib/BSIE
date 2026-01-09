"""State constants tests."""
import pytest

from bsie.state.constants import (
    State,
    TRANSITION_MATRIX,
    STATE_TIMEOUTS,
    STATE_REQUIRED_ARTIFACTS,
    get_allowed_transitions,
)


def test_all_mvp_states_defined():
    mvp_states = [
        State.UPLOADED,
        State.INGESTED,
        State.CLASSIFIED,
        State.ROUTED,
        State.TEMPLATE_SELECTED,
        State.TEMPLATE_MISSING,
        State.EXTRACTION_READY,
        State.EXTRACTING,
        State.EXTRACTION_FAILED,
        State.RECONCILING,
        State.RECONCILIATION_FAILED,
        State.HUMAN_REVIEW_REQUIRED,
        State.COMPLETED,
    ]
    assert len(mvp_states) == 13


def test_transition_matrix_uploaded():
    """UPLOADED can transition to INGESTED or HUMAN_REVIEW_REQUIRED."""
    allowed = get_allowed_transitions(State.UPLOADED)
    assert State.INGESTED in allowed
    assert State.HUMAN_REVIEW_REQUIRED in allowed
    assert State.COMPLETED not in allowed


def test_transition_matrix_routed():
    """ROUTED can transition to TEMPLATE_SELECTED or TEMPLATE_MISSING."""
    allowed = get_allowed_transitions(State.ROUTED)
    assert State.TEMPLATE_SELECTED in allowed
    assert State.TEMPLATE_MISSING in allowed


def test_completed_is_terminal():
    """COMPLETED has no outgoing transitions."""
    allowed = get_allowed_transitions(State.COMPLETED)
    assert len(allowed) == 0


def test_state_timeouts():
    assert STATE_TIMEOUTS[State.UPLOADED] == 30
    assert STATE_TIMEOUTS[State.EXTRACTING] == 120
    assert STATE_TIMEOUTS.get(State.COMPLETED) is None  # Terminal, no timeout


def test_required_artifacts_for_ingested():
    required = STATE_REQUIRED_ARTIFACTS.get(State.INGESTED, [])
    assert "ingest_receipt" in required
