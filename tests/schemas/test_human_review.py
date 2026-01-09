"""Human review schema tests."""
import pytest
from datetime import datetime, timezone

from bsie.schemas.human_review import (
    HumanReviewDecision,
    ReviewDecisionType,
    CorrectionOverlay,
    TransactionCorrection,
    CorrectionType,
)


def test_human_review_approve():
    decision = HumanReviewDecision(
        statement_id="stmt_abc123",
        decision=ReviewDecisionType.APPROVE,
        reviewer_id="user_123",
        decided_at=datetime.now(timezone.utc),
    )
    assert decision.decision == ReviewDecisionType.APPROVE


def test_human_review_approve_with_corrections():
    decision = HumanReviewDecision(
        statement_id="stmt_abc123",
        decision=ReviewDecisionType.APPROVE_WITH_CORRECTIONS,
        reviewer_id="user_123",
        decided_at=datetime.now(timezone.utc),
        correction_overlay_id="corr_xyz789",
        notes="Fixed date on row 5",
    )
    assert decision.correction_overlay_id == "corr_xyz789"


def test_human_review_reject():
    decision = HumanReviewDecision(
        statement_id="stmt_abc123",
        decision=ReviewDecisionType.REJECT,
        reviewer_id="user_123",
        decided_at=datetime.now(timezone.utc),
        rejection_reason="PDF is corrupted, transactions unreadable",
    )
    assert decision.rejection_reason is not None


def test_correction_overlay():
    overlay = CorrectionOverlay(
        statement_id="stmt_abc123",
        overlay_id="corr_xyz789",
        reviewer_id="user_123",
        corrections=[
            TransactionCorrection(
                row_id="row_005",
                correction_type=CorrectionType.EDIT,
                field="amount",
                original_value="-100.00",
                corrected_value="-1000.00",
                reason="OCR misread amount",
            ),
        ],
        created_at=datetime.now(timezone.utc),
    )
    assert len(overlay.corrections) == 1
    assert overlay.corrections[0].corrected_value == "-1000.00"


def test_correction_types():
    assert CorrectionType.EDIT == "edit"
    assert CorrectionType.ADD == "add"
    assert CorrectionType.DELETE == "delete"
