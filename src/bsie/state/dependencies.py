"""FastAPI dependency injection for StateController."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from bsie.state.controller import StateController


async def get_state_controller(
    session: AsyncSession,
) -> AsyncGenerator[StateController, None]:
    """
    Dependency that provides a StateController.

    Usage in FastAPI:
        @app.post("/statements/{id}/transition")
        async def transition_statement(
            id: str,
            controller: StateController = Depends(get_state_controller),
        ):
            ...

    Note: This requires the session to be injected separately.
    For full FastAPI integration, combine with a session dependency.
    """
    yield StateController(session=session)


def create_state_controller(session: AsyncSession) -> StateController:
    """
    Factory function to create a StateController.

    Useful for non-FastAPI contexts where you have a session.
    """
    return StateController(session=session)
