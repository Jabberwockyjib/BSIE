"""Schema registry tests."""
import pytest
from datetime import datetime, timezone

from bsie.schemas.registry import (
    get_schema_for_artifact,
    validate_artifact,
    ArtifactType,
    ValidationError as SchemaValidationError,
)


def test_get_schema_for_ingest_receipt():
    schema = get_schema_for_artifact(ArtifactType.INGEST_RECEIPT)
    assert schema is not None


def test_get_schema_for_all_artifact_types():
    for artifact_type in ArtifactType:
        schema = get_schema_for_artifact(artifact_type)
        assert schema is not None, f"No schema for {artifact_type}"


def test_validate_artifact_valid():
    data = {
        "statement_id": "stmt_abc123",
        "sha256": "a" * 64,
        "pages": 5,
        "stored": True,
        "original_path": "/uploads/test.pdf",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    result = validate_artifact(ArtifactType.INGEST_RECEIPT, data)
    assert result.statement_id == "stmt_abc123"


def test_validate_artifact_invalid():
    data = {
        "statement_id": "stmt_abc123",
        # Missing required fields
    }
    with pytest.raises(SchemaValidationError):
        validate_artifact(ArtifactType.INGEST_RECEIPT, data)
