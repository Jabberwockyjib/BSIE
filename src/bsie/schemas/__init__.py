"""Pydantic schemas for BSIE artifacts."""

# Base types
from bsie.schemas.base import BsieBaseModel, BoundingBox, Provenance

# Artifact schemas
from bsie.schemas.ingest import IngestReceipt
from bsie.schemas.classification import (
    Classification,
    CandidateTemplate,
    StatementType,
    Segment,
)
from bsie.schemas.routing import RouteDecision, SelectedTemplate, RouteDecisionType
from bsie.schemas.transactions import (
    Transaction,
    Transactions,
    TransactionType,
    TransactionSummary,
)
from bsie.schemas.extraction import (
    ExtractionResult,
    ExtractionStatus,
    ExtractionMethod,
    MethodAttempt,
    ExtractedBalances,
)
from bsie.schemas.reconciliation import (
    Reconciliation,
    ReconciliationStatus,
    ReconciliationType,
    RunningBalanceCheck,
)
from bsie.schemas.pipeline_state import (
    PipelineState,
    PipelineStateEnum,
    StateHistoryEntry,
    TemplateBinding,
)
from bsie.schemas.errors import ExtractionError, ErrorCategory
from bsie.schemas.human_review import (
    HumanReviewDecision,
    ReviewDecisionType,
    CorrectionOverlay,
    TransactionCorrection,
    CorrectionType,
)
from bsie.schemas.final_transactions import (
    FinalTransactions,
    FinalTransaction,
    FinalTransactionSource,
    CorrectionSource,
)

# Registry and validation
from bsie.schemas.registry import (
    ArtifactType,
    get_schema_for_artifact,
    validate_artifact,
    ValidationError,
)

__all__ = [
    # Base
    "BsieBaseModel",
    "BoundingBox",
    "Provenance",
    # Ingest
    "IngestReceipt",
    # Classification
    "Classification",
    "CandidateTemplate",
    "StatementType",
    "Segment",
    # Routing
    "RouteDecision",
    "SelectedTemplate",
    "RouteDecisionType",
    # Transactions
    "Transaction",
    "Transactions",
    "TransactionType",
    "TransactionSummary",
    # Extraction
    "ExtractionResult",
    "ExtractionStatus",
    "ExtractionMethod",
    "MethodAttempt",
    "ExtractedBalances",
    # Reconciliation
    "Reconciliation",
    "ReconciliationStatus",
    "ReconciliationType",
    "RunningBalanceCheck",
    # Pipeline State
    "PipelineState",
    "PipelineStateEnum",
    "StateHistoryEntry",
    "TemplateBinding",
    # Errors
    "ExtractionError",
    "ErrorCategory",
    # Human Review
    "HumanReviewDecision",
    "ReviewDecisionType",
    "CorrectionOverlay",
    "TransactionCorrection",
    "CorrectionType",
    # Final Transactions
    "FinalTransactions",
    "FinalTransaction",
    "FinalTransactionSource",
    "CorrectionSource",
    # Registry
    "ArtifactType",
    "get_schema_for_artifact",
    "validate_artifact",
    "ValidationError",
]
