"""State Controller - owns all pipeline state transitions."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bsie.db.models import Statement, StateHistory
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

        # Check optimistic locking if expected_version is provided
        expected_version = metadata.get("expected_version")
        if expected_version is not None and statement.state_version != expected_version:
            return TransitionResult(
                success=False,
                previous_state=from_state.value,
                current_state=from_state.value,
                statement_id=statement_id,
                timestamp=timestamp,
                error=f"Version mismatch: expected {expected_version}, got {statement.state_version}",
                error_type=TransitionError.CONCURRENT_MODIFICATION,
            )

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

        # Check required artifacts
        required_artifacts = self.get_required_artifacts(to_state)
        missing = [a for a in required_artifacts if a not in artifacts]
        if missing:
            return TransitionResult(
                success=False,
                previous_state=from_state.value,
                current_state=from_state.value,
                statement_id=statement_id,
                timestamp=timestamp,
                error=f"Missing required artifacts: {', '.join(missing)}",
                error_type=TransitionError.MISSING_ARTIFACT,
            )

        # Update state
        statement.current_state = to_state.value
        statement.state_version += 1

        # Record history
        history_entry = StateHistory(
            statement_id=statement_id,
            from_state=from_state.value,
            to_state=to_state.value,
            trigger=trigger,
            worker_id=worker_id,
            artifacts_created=list(artifacts.keys()),
            transition_metadata=metadata,
        )
        self._session.add(history_entry)

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

    async def force_transition(
        self,
        statement_id: str,
        to_state: State,
        reason: str,
        actor: str,
    ) -> TransitionResult:
        """
        Force a state transition (admin override).

        This bypasses normal validation but still records full audit trail.
        """
        timestamp = datetime.now(timezone.utc)

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

        # Update state (no validation)
        statement.current_state = to_state.value
        statement.state_version += 1

        # Record history with override details
        history_entry = StateHistory(
            statement_id=statement_id,
            from_state=from_state.value,
            to_state=to_state.value,
            trigger="admin_force",
            transition_metadata={
                "actor": actor,
                "reason": reason,
                "forced": True,
            },
        )
        self._session.add(history_entry)

        await self._session.commit()

        return TransitionResult(
            success=True,
            previous_state=from_state.value,
            current_state=to_state.value,
            statement_id=statement_id,
            timestamp=timestamp,
            metadata={"transition_type": "forced", "actor": actor},
        )

    async def get_state_history(self, statement_id: str) -> List[StateHistory]:
        """Get complete state transition history for a statement."""
        result = await self._session.execute(
            select(StateHistory)
            .where(StateHistory.statement_id == statement_id)
            .order_by(StateHistory.created_at)
        )
        return list(result.scalars().all())

    async def create_statement(
        self,
        statement_id: str,
        sha256: str,
        original_filename: str,
        file_size_bytes: int,
        page_count: int,
        storage_path: Optional[str] = None,
    ) -> Statement:
        """
        Create a new statement with initial UPLOADED state.

        This is the ONLY way to create a statement - ensures
        proper initial state.
        """
        statement = Statement(
            id=statement_id,
            sha256=sha256,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            page_count=page_count,
            storage_path=storage_path,
            current_state=State.UPLOADED.value,
            state_version=1,
        )
        self._session.add(statement)

        # Record initial state in history
        history_entry = StateHistory(
            statement_id=statement_id,
            from_state=None,
            to_state=State.UPLOADED.value,
            trigger="upload",
        )
        self._session.add(history_entry)

        await self._session.commit()
        return statement
