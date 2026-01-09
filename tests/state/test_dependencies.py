"""State controller dependency tests."""
import pytest
from unittest.mock import AsyncMock

from bsie.state.dependencies import create_state_controller, get_state_controller
from bsie.state.controller import StateController


def test_create_state_controller():
    """Factory function should create StateController."""
    mock_session = AsyncMock()
    controller = create_state_controller(mock_session)

    assert isinstance(controller, StateController)
    assert controller._session is mock_session


@pytest.mark.asyncio
async def test_get_state_controller():
    """Dependency should yield StateController."""
    mock_session = AsyncMock()

    async for controller in get_state_controller(mock_session):
        assert isinstance(controller, StateController)
        assert controller._session is mock_session
