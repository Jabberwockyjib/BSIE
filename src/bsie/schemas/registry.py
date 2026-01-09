"""Schema registry and validation utilities."""
from enum import Enum
from typing import Any, Type

from pydantic import ValidationError as PydanticValidationError

from bsie.schemas.base import BsieBaseModel
from bsie.schemas.ingest import IngestReceipt
from bsie.schemas.classification import Classification
from bsie.schemas.routing import RouteDecision
from bsie.schemas.transactions import Transactions
from bsie.schemas.extraction import ExtractionResult
from bsie.schemas.reconciliation import Reconciliation
from bsie.schemas.pipeline_state import PipelineState
from bsie.schemas.errors import ExtractionError
from bsie.schemas.human_review import HumanReviewDecision, CorrectionOverlay
from bsie.schemas.final_transactions import FinalTransactions


class ValidationError(Exception):
    """Schema validation error."""

    def __init__(self, message: str, errors: list | None = None):
        super().__init__(message)
        self.errors = errors or []


class ArtifactType(str, Enum):
    """Artifact type enumeration."""
    INGEST_RECEIPT = "ingest_receipt"
    CLASSIFICATION = "classification"
    ROUTE_DECISION = "route_decision"
    TRANSACTIONS = "transactions"
    EXTRACTION_RESULT = "extraction_result"
    RECONCILIATION = "reconciliation"
    PIPELINE_STATE = "pipeline_state"
    EXTRACTION_ERROR = "extraction_error"
    HUMAN_REVIEW_DECISION = "human_review_decision"
    CORRECTION_OVERLAY = "correction_overlay"
    FINAL_TRANSACTIONS = "final_transactions"


# Registry mapping artifact types to schema classes
_SCHEMA_REGISTRY: dict[ArtifactType, Type[BsieBaseModel]] = {
    ArtifactType.INGEST_RECEIPT: IngestReceipt,
    ArtifactType.CLASSIFICATION: Classification,
    ArtifactType.ROUTE_DECISION: RouteDecision,
    ArtifactType.TRANSACTIONS: Transactions,
    ArtifactType.EXTRACTION_RESULT: ExtractionResult,
    ArtifactType.RECONCILIATION: Reconciliation,
    ArtifactType.PIPELINE_STATE: PipelineState,
    ArtifactType.EXTRACTION_ERROR: ExtractionError,
    ArtifactType.HUMAN_REVIEW_DECISION: HumanReviewDecision,
    ArtifactType.CORRECTION_OVERLAY: CorrectionOverlay,
    ArtifactType.FINAL_TRANSACTIONS: FinalTransactions,
}


def get_schema_for_artifact(artifact_type: ArtifactType) -> Type[BsieBaseModel]:
    """Get the schema class for an artifact type."""
    return _SCHEMA_REGISTRY[artifact_type]


def validate_artifact(artifact_type: ArtifactType, data: dict[str, Any]) -> BsieBaseModel:
    """Validate artifact data against its schema.

    Args:
        artifact_type: Type of artifact to validate
        data: Dictionary of artifact data

    Returns:
        Validated Pydantic model instance

    Raises:
        ValidationError: If validation fails
    """
    schema_class = get_schema_for_artifact(artifact_type)

    try:
        return schema_class.model_validate(data)
    except PydanticValidationError as e:
        raise ValidationError(
            f"Validation failed for {artifact_type.value}",
            errors=e.errors(),
        ) from e
