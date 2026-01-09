"""State controller tests."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from bsie.state.controller import StateController
from bsie.state.constants import State
from bsie.state.types import TransitionResult, TransitionError


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def controller(mock_session):
    """Create a StateController instance."""
    return StateController(session=mock_session)


@pytest.mark.asyncio
async def test_validate_transition_valid(controller):
    """Valid transitions should pass validation."""
    is_valid = controller.validate_transition(State.UPLOADED, State.INGESTED)
    assert is_valid is True


@pytest.mark.asyncio
async def test_validate_transition_invalid(controller):
    """Invalid transitions should fail validation."""
    is_valid = controller.validate_transition(State.UPLOADED, State.COMPLETED)
    assert is_valid is False


@pytest.mark.asyncio
async def test_get_allowed_transitions(controller):
    """Should return allowed transitions for a state."""
    allowed = controller.get_allowed_transitions(State.ROUTED)
    assert State.TEMPLATE_SELECTED in allowed
    assert State.TEMPLATE_MISSING in allowed


@pytest.mark.asyncio
async def test_get_current_state(db_session_with_statement):
    """Should retrieve current state of a statement."""
    controller = StateController(session=db_session_with_statement)
    state = await controller.get_current_state("stmt_test001")
    assert state == State.UPLOADED


@pytest.mark.asyncio
async def test_get_current_state_not_found(db_session):
    """Should return None for non-existent statement."""
    controller = StateController(session=db_session)
    state = await controller.get_current_state("stmt_nonexistent")
    assert state is None


@pytest.mark.asyncio
async def test_get_statement(db_session_with_statement):
    """Should retrieve statement by ID."""
    controller = StateController(session=db_session_with_statement)
    statement = await controller.get_statement("stmt_test001")
    assert statement is not None
    assert statement.id == "stmt_test001"
    assert statement.current_state == "UPLOADED"


@pytest.mark.asyncio
async def test_get_statement_not_found(db_session):
    """Should return None for non-existent statement."""
    controller = StateController(session=db_session)
    statement = await controller.get_statement("stmt_nonexistent")
    assert statement is None
