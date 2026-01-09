"""Route decision schema."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class RouteDecisionType(str, Enum):
    """Route decision type."""
    TEMPLATE_SELECTED = "template_selected"
    TEMPLATE_MISSING = "template_missing"


class SelectedTemplate(BsieBaseModel):
    """Selected template details."""

    template_id: str
    version: str
    score: float = Field(..., ge=0.0, le=1.0)


class RouteDecision(BsieBaseModel):
    """Schema for route_decision.json artifact."""

    statement_id: str
    decision: RouteDecisionType
    decided_at: datetime

    # Template selection details
    selected_template: Optional[SelectedTemplate] = None
    selection_reason: Optional[str] = None

    # Alternative consideration
    alternatives_considered: Optional[List[Dict[str, Any]]] = None
    confidence_threshold_used: Optional[float] = Field(None, ge=0.0, le=1.0)
