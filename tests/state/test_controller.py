"""State controller tests."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from bsie.db.models import StateHistory
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


@pytest.mark.asyncio
async def test_transition_success(db_session_with_statement):
    """Successful transition should update state."""
    controller = StateController(session=db_session_with_statement)

    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingestion_complete",
        artifacts={"ingest_receipt": {"statement_id": "stmt_test001"}},
    )

    assert result.success is True
    assert result.previous_state == "UPLOADED"
    assert result.current_state == "INGESTED"

    # Verify state was persisted
    new_state = await controller.get_current_state("stmt_test001")
    assert new_state == State.INGESTED


@pytest.mark.asyncio
async def test_transition_invalid(db_session_with_statement):
    """Invalid transition should fail."""
    controller = StateController(session=db_session_with_statement)

    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.COMPLETED,  # Invalid from UPLOADED
        trigger="test",
    )

    assert result.success is False
    assert result.error_type == TransitionError.INVALID_TRANSITION

    # Verify state was NOT changed
    current_state = await controller.get_current_state("stmt_test001")
    assert current_state == State.UPLOADED


@pytest.mark.asyncio
async def test_transition_not_found(db_session):
    """Transition on non-existent statement should fail."""
    controller = StateController(session=db_session)

    result = await controller.transition(
        statement_id="stmt_nonexistent",
        to_state=State.INGESTED,
        trigger="test",
    )

    assert result.success is False
    assert result.error_type == TransitionError.STATE_NOT_FOUND


@pytest.mark.asyncio
async def test_transition_missing_required_artifact(db_session_with_statement):
    """Transition without required artifact should fail."""
    controller = StateController(session=db_session_with_statement)

    # INGESTED requires ingest_receipt artifact
    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingestion_complete",
        artifacts={},  # Missing required artifact
    )

    assert result.success is False
    assert result.error_type == TransitionError.MISSING_ARTIFACT
    assert "ingest_receipt" in result.error


@pytest.mark.asyncio
async def test_transition_records_history(db_session_with_statement):
    """Successful transition should record history."""
    controller = StateController(session=db_session_with_statement)

    await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingestion_complete",
        artifacts={"ingest_receipt": {"statement_id": "stmt_test001"}},
        worker_id="worker_01",
    )

    # Check history was recorded
    result = await db_session_with_statement.execute(
        select(StateHistory).where(StateHistory.statement_id == "stmt_test001")
    )
    history = result.scalars().all()

    assert len(history) == 1
    assert history[0].from_state == "UPLOADED"
    assert history[0].to_state == "INGESTED"
    assert history[0].trigger == "ingestion_complete"
    assert history[0].worker_id == "worker_01"


@pytest.mark.asyncio
async def test_transition_with_expected_version(db_session_with_statement):
    """Transition should support optimistic locking."""
    controller = StateController(session=db_session_with_statement)

    # First transition should work with correct version
    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingestion_complete",
        artifacts={"ingest_receipt": {"statement_id": "stmt_test001"}},
        metadata={"expected_version": 1},
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_transition_stale_version(db_session_with_statement):
    """Transition with stale version should fail."""
    controller = StateController(session=db_session_with_statement)

    # First, do a successful transition to increment version
    await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="test",
        artifacts={"ingest_receipt": {}},
    )

    # Now try with old version - should fail
    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.CLASSIFIED,
        trigger="test",
        artifacts={"classification": {}},
        metadata={"expected_version": 1},  # Old version
    )
    assert result.success is False
    assert result.error_type == TransitionError.CONCURRENT_MODIFICATION


@pytest.mark.asyncio
async def test_force_transition(db_session_with_statement):
    """Admin should be able to force invalid transitions."""
    controller = StateController(session=db_session_with_statement)

    # Force transition that would normally be invalid
    result = await controller.force_transition(
        statement_id="stmt_test001",
        to_state=State.COMPLETED,
        reason="Admin override for testing",
        actor="admin_user",
    )

    assert result.success is True
    assert result.current_state == "COMPLETED"
    assert "forced" in result.metadata.get("transition_type", "")


@pytest.mark.asyncio
async def test_force_transition_records_actor(db_session_with_statement):
    """Force transition should record who performed it."""
    controller = StateController(session=db_session_with_statement)

    await controller.force_transition(
        statement_id="stmt_test001",
        to_state=State.HUMAN_REVIEW_REQUIRED,
        reason="Manual escalation",
        actor="admin_user",
    )

    # Check history
    result = await db_session_with_statement.execute(
        select(StateHistory).where(StateHistory.statement_id == "stmt_test001")
    )
    history = result.scalar_one()
    assert history.transition_metadata.get("actor") == "admin_user"
    assert history.transition_metadata.get("reason") == "Manual escalation"


@pytest.mark.asyncio
async def test_get_state_history(db_session_with_statement):
    """Should retrieve complete state history."""
    controller = StateController(session=db_session_with_statement)

    # Perform several transitions
    await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingest",
        artifacts={"ingest_receipt": {}},
    )
    await controller.transition(
        statement_id="stmt_test001",
        to_state=State.CLASSIFIED,
        trigger="classify",
        artifacts={"classification": {}},
    )

    # Get history
    history = await controller.get_state_history("stmt_test001")

    assert len(history) == 2
    assert history[0].from_state == "UPLOADED"
    assert history[0].to_state == "INGESTED"
    assert history[1].from_state == "INGESTED"
    assert history[1].to_state == "CLASSIFIED"


@pytest.mark.asyncio
async def test_create_initial_state(db_session):
    """Should create statement with initial UPLOADED state."""
    controller = StateController(session=db_session)

    statement = await controller.create_statement(
        statement_id="stmt_new001",
        sha256="b" * 64,
        original_filename="new.pdf",
        file_size_bytes=2048,
        page_count=5,
    )

    assert statement.id == "stmt_new001"
    assert statement.current_state == State.UPLOADED.value
    assert statement.state_version == 1

    # Verify we can get it
    state = await controller.get_current_state("stmt_new001")
    assert state == State.UPLOADED
