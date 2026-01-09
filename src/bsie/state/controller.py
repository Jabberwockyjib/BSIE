"""State Controller - owns all pipeline state transitions."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bsie.db.models import Statement
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

    async def get_current_state(self, statement_id: str) -> Optional[State]:
        """Get the current state of a statement."""
        result = await self._session.execute(
            select(Statement.current_state).where(Statement.id == statement_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return State(row)

    async def get_statement(self, statement_id: str) -> Optional[Statement]:
        """Get a statement by ID."""
        result = await self._session.execute(
            select(Statement).where(Statement.id == statement_id)
        )
        return result.scalar_one_or_none()

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
        artifacts = artifacts or {}
        metadata = metadata or {}
        timestamp = datetime.now(timezone.utc)

        # Get current statement
        statement = await self.get_statement(statement_id)
        if statement is None:
            return TransitionResult(
                success=False,
                previous_state="UNKNOWN",
                current_state="UNKNOWN",
                statement_id=statement_id,
                timestamp=timestamp,
                error=f"Statement {statement_id} not found",
                error_type=TransitionError.STATE_NOT_FOUND,
            )

        from_state = State(statement.current_state)

        # Validate transition
        if not self.validate_transition(from_state, to_state):
            return TransitionResult(
                success=False,
                previous_state=from_state.value,
                current_state=from_state.value,
                statement_id=statement_id,
                timestamp=timestamp,
                error=f"Invalid transition: {from_state.value} -> {to_state.value}",
                error_type=TransitionError.INVALID_TRANSITION,
            )

        # Update state
        statement.current_state = to_state.value
        statement.state_version += 1

        await self._session.commit()

        return TransitionResult(
            success=True,
            previous_state=from_state.value,
            current_state=to_state.value,
            statement_id=statement_id,
            timestamp=timestamp,
            artifacts_created=list(artifacts.keys()),
            metadata=metadata,
        )
