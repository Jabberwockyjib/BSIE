"""Route decision schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.routing import RouteDecision, SelectedTemplate, RouteDecisionType


def test_route_decision_template_selected():
    decision = RouteDecision(
        statement_id="stmt_abc123",
        decision=RouteDecisionType.TEMPLATE_SELECTED,
        selected_template=SelectedTemplate(
            template_id="chase_checking_v1",
            version="1.0.0",
            score=0.95,
        ),
        selection_reason="Score 0.95 >= threshold 0.80",
        decided_at=datetime.now(timezone.utc),
    )
    assert decision.decision == RouteDecisionType.TEMPLATE_SELECTED
    assert decision.selected_template is not None


def test_route_decision_template_missing():
    decision = RouteDecision(
        statement_id="stmt_abc123",
        decision=RouteDecisionType.TEMPLATE_MISSING,
        selection_reason="No candidate templates found",
        decided_at=datetime.now(timezone.utc),
    )
    assert decision.decision == RouteDecisionType.TEMPLATE_MISSING
    assert decision.selected_template is None


def test_route_decision_with_alternatives():
    decision = RouteDecision(
        statement_id="stmt_abc123",
        decision=RouteDecisionType.TEMPLATE_MISSING,
        selection_reason="Top score 0.65 < threshold 0.80",
        alternatives_considered=[
            {"template_id": "chase_v1", "score": 0.65, "rejection_reason": "Below threshold"},
        ],
        confidence_threshold_used=0.80,
        decided_at=datetime.now(timezone.utc),
    )
    assert len(decision.alternatives_considered) == 1
