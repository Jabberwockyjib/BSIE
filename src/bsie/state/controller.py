"""State Controller - owns all pipeline state transitions."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set, List

from sqlalchemy.ext.asyncio import AsyncSession

from bsie.state.constants import (
    State,
    TRANSITION_MATRIX,
    STATE_REQUIRED_ARTIFACTS,
    get_allowed_transitions,
    is_valid_transition,
)
from bsie.state.types import TransitionResult, TransitionError, TransitionRequest


class StateController:
    """
    Centralized state controller for pipeline transitions.

    All state transitions MUST go through this controller.
    Workers and agents may NOT mutate state directly.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def validate_transition(self, from_state: State, to_state: State) -> bool:
        """Validate that a transition is allowed."""
        return is_valid_transition(from_state, to_state)

    def get_allowed_transitions(self, from_state: State) -> Set[State]:
        """Get the set of allowed target states from current state."""
        return get_allowed_transitions(from_state)

    def get_required_artifacts(self, to_state: State) -> List[str]:
        """Get required artifacts to enter a state."""
        return STATE_REQUIRED_ARTIFACTS.get(to_state, [])

    async def transition(
        self,
        statement_id: str,
        to_state: State,
        trigger: str,
        artifacts: Optional[Dict[str, Any]] = None,
        worker_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TransitionResult:
        """
        Attempt a state transition.

        Args:
            statement_id: Statement to transition
            to_state: Target state
            trigger: What triggered this transition
            artifacts: Artifacts to validate and store
            worker_id: ID of the worker performing the transition
            metadata: Additional metadata

        Returns:
            TransitionResult indicating success or failure
        """
        # Implementation will be added in subsequent tasks
        raise NotImplementedError("Full transition logic coming in Task 3.4+")
