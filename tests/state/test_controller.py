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
