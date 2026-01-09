"""State controller type definitions."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class TransitionError(str, Enum):
    """Transition error categories."""
    INVALID_TRANSITION = "invalid_transition"
    MISSING_ARTIFACT = "missing_artifact"
    VALIDATION_FAILED = "validation_failed"
    CONCURRENT_MODIFICATION = "concurrent_modification"
    STATE_NOT_FOUND = "state_not_found"
    TIMEOUT = "timeout"


@dataclass
class TransitionResult:
    """Result of a state transition attempt."""
    success: bool
    previous_state: str
    current_state: str
    statement_id: str
    timestamp: datetime
    error: Optional[str] = None
    error_type: Optional[TransitionError] = None
    artifacts_created: List[str] = field(default_factory=list)
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransitionRequest:
    """Request to perform a state transition."""
    statement_id: str
    to_state: str
    trigger: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
