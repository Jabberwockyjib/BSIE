"""Classification schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.classification import (
    Classification,
    CandidateTemplate,
    StatementType,
    Segment,
)


def test_classification_valid():
    classification = Classification(
        statement_id="stmt_abc123",
        bank_family="chase",
        statement_type=StatementType.CHECKING,
        segment=Segment.PERSONAL,
        layout_fingerprint="HML-HHM-LLM-abc123",
        confidence=0.95,
        candidate_templates=[],
        classified_at=datetime.now(timezone.utc),
    )
    assert classification.bank_family == "chase"


def test_candidate_template():
    candidate = CandidateTemplate(
        template_id="chase_checking_v1",
        version="1.0.0",
        score=0.92,
        factors={"bank_match": 1.0, "layout_match": 0.85},
    )
    assert candidate.score == 0.92


def test_classification_with_candidates():
    classification = Classification(
        statement_id="stmt_abc123",
        bank_family="chase",
        statement_type=StatementType.CHECKING,
        segment=Segment.PERSONAL,
        layout_fingerprint="HML-HHM-LLM-abc123",
        confidence=0.95,
        candidate_templates=[
            CandidateTemplate(
                template_id="chase_checking_v1",
                version="1.0.0",
                score=0.92,
            ),
            CandidateTemplate(
                template_id="chase_checking_v2",
                version="2.0.0",
                score=0.88,
            ),
        ],
        classified_at=datetime.now(timezone.utc),
    )
    assert len(classification.candidate_templates) == 2


def test_confidence_range():
    with pytest.raises(ValidationError):
        Classification(
            statement_id="stmt_abc123",
            bank_family="chase",
            statement_type=StatementType.CHECKING,
            segment=Segment.PERSONAL,
            layout_fingerprint="test",
            confidence=1.5,  # Out of range
            candidate_templates=[],
            classified_at=datetime.now(timezone.utc),
        )


def test_statement_type_enum():
    assert StatementType.CHECKING == "checking"
    assert StatementType.SAVINGS == "savings"
    assert StatementType.CREDIT_CARD == "credit_card"
