"""Pipeline state schema tests."""
import pytest
from datetime import datetime, timezone

from bsie.schemas.pipeline_state import (
    PipelineState,
    PipelineStateEnum,
    StateHistoryEntry,
    TemplateBinding,
)


def test_pipeline_state_valid():
    state = PipelineState(
        statement_id="stmt_abc123",
        current_state=PipelineStateEnum.UPLOADED,
        state_history=[
            StateHistoryEntry(
                state="UPLOADED",
                entered_at=datetime.now(timezone.utc),
            ),
        ],
        updated_at=datetime.now(timezone.utc),
    )
    assert state.current_state == PipelineStateEnum.UPLOADED


def test_pipeline_state_all_states():
    """Verify all MVP states are defined."""
    states = [
        PipelineStateEnum.UPLOADED,
        PipelineStateEnum.INGESTED,
        PipelineStateEnum.CLASSIFIED,
        PipelineStateEnum.ROUTED,
        PipelineStateEnum.TEMPLATE_SELECTED,
        PipelineStateEnum.TEMPLATE_MISSING,
        PipelineStateEnum.EXTRACTION_READY,
        PipelineStateEnum.EXTRACTING,
        PipelineStateEnum.EXTRACTION_FAILED,
        PipelineStateEnum.RECONCILING,
        PipelineStateEnum.RECONCILIATION_FAILED,
        PipelineStateEnum.HUMAN_REVIEW_REQUIRED,
        PipelineStateEnum.COMPLETED,
    ]
    assert len(states) == 13


def test_pipeline_state_with_template_binding():
    state = PipelineState(
        statement_id="stmt_abc123",
        current_state=PipelineStateEnum.TEMPLATE_SELECTED,
        state_history=[],
        updated_at=datetime.now(timezone.utc),
        template_binding=TemplateBinding(
            template_id="chase_checking_v1",
            template_version="1.0.0",
            bound_at=datetime.now(timezone.utc),
        ),
    )
    assert state.template_binding.template_id == "chase_checking_v1"


def test_state_history_entry():
    entry = StateHistoryEntry(
        state="INGESTED",
        entered_at=datetime.now(timezone.utc),
        exited_at=datetime.now(timezone.utc),
        duration_ms=1500,
        trigger="ingestion_complete",
        metadata={"worker_id": "worker_01"},
    )
    assert entry.duration_ms == 1500
