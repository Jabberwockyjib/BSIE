"""State machine constants and transition definitions."""
from enum import Enum
from typing import Dict, List, Set, Optional


class State(str, Enum):
    """Pipeline states."""
    # Phase 1 MVP states
    UPLOADED = "UPLOADED"
    INGESTED = "INGESTED"
    CLASSIFIED = "CLASSIFIED"
    ROUTED = "ROUTED"
    TEMPLATE_SELECTED = "TEMPLATE_SELECTED"
    TEMPLATE_MISSING = "TEMPLATE_MISSING"
    EXTRACTION_READY = "EXTRACTION_READY"
    EXTRACTING = "EXTRACTING"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    RECONCILING = "RECONCILING"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"


# Valid state transitions (from_state -> set of allowed to_states)
TRANSITION_MATRIX: Dict[State, Set[State]] = {
    State.UPLOADED: {State.INGESTED, State.HUMAN_REVIEW_REQUIRED},
    State.INGESTED: {State.CLASSIFIED},
    State.CLASSIFIED: {State.ROUTED},
    State.ROUTED: {State.TEMPLATE_SELECTED, State.TEMPLATE_MISSING},
    State.TEMPLATE_SELECTED: {State.EXTRACTION_READY},
    State.TEMPLATE_MISSING: {State.HUMAN_REVIEW_REQUIRED},
    State.EXTRACTION_READY: {State.EXTRACTING},
    State.EXTRACTING: {State.RECONCILING, State.EXTRACTION_FAILED},
    State.EXTRACTION_FAILED: {State.HUMAN_REVIEW_REQUIRED},
    State.RECONCILING: {State.COMPLETED, State.RECONCILIATION_FAILED},
    State.RECONCILIATION_FAILED: {State.HUMAN_REVIEW_REQUIRED},
    State.HUMAN_REVIEW_REQUIRED: {State.COMPLETED, State.EXTRACTION_READY},
    State.COMPLETED: set(),  # Terminal state
}


# State timeouts in seconds (None = no timeout)
STATE_TIMEOUTS: Dict[State, Optional[int]] = {
    State.UPLOADED: 30,
    State.INGESTED: None,  # Stable
    State.CLASSIFIED: None,  # Stable
    State.ROUTED: 5,
    State.TEMPLATE_SELECTED: None,  # Stable
    State.TEMPLATE_MISSING: None,  # Terminal in Phase 1
    State.EXTRACTION_READY: 10,
    State.EXTRACTING: 120,
    State.EXTRACTION_FAILED: None,  # Error state
    State.RECONCILING: 10,
    State.RECONCILIATION_FAILED: None,  # Error state
    State.HUMAN_REVIEW_REQUIRED: 7 * 24 * 3600,  # 7 days
    State.COMPLETED: None,  # Terminal
}


# Required artifacts to enter each state
STATE_REQUIRED_ARTIFACTS: Dict[State, List[str]] = {
    State.INGESTED: ["ingest_receipt"],
    State.CLASSIFIED: ["classification"],
    State.ROUTED: ["route_decision"],
    State.RECONCILING: ["extraction_result", "transactions"],
    State.COMPLETED: ["reconciliation", "final_transactions"],
}


def get_allowed_transitions(from_state: State) -> Set[State]:
    """Get allowed transitions from a state."""
    return TRANSITION_MATRIX.get(from_state, set())


def is_valid_transition(from_state: State, to_state: State) -> bool:
    """Check if a transition is valid."""
    return to_state in get_allowed_transitions(from_state)
