"""Ingest receipt schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.ingest import IngestReceipt


def test_ingest_receipt_valid():
    receipt = IngestReceipt(
        statement_id="stmt_abc123",
        sha256="a" * 64,
        pages=5,
        stored=True,
        original_path="/uploads/test.pdf",
        uploaded_at=datetime.now(timezone.utc),
    )
    assert receipt.statement_id == "stmt_abc123"
    assert receipt.pages == 5


def test_ingest_receipt_sha256_pattern():
    # Invalid SHA256 (wrong length)
    with pytest.raises(ValidationError):
        IngestReceipt(
            statement_id="stmt_abc123",
            sha256="abc",  # Too short
            pages=5,
            stored=True,
            original_path="/uploads/test.pdf",
            uploaded_at=datetime.now(timezone.utc),
        )


def test_ingest_receipt_pages_minimum():
    with pytest.raises(ValidationError):
        IngestReceipt(
            statement_id="stmt_abc123",
            sha256="a" * 64,
            pages=0,  # Must be >= 1
            stored=True,
            original_path="/uploads/test.pdf",
            uploaded_at=datetime.now(timezone.utc),
        )


def test_ingest_receipt_optional_fields():
    receipt = IngestReceipt(
        statement_id="stmt_abc123",
        sha256="a" * 64,
        pages=3,
        stored=True,
        original_path="/uploads/test.pdf",
        uploaded_at=datetime.now(timezone.utc),
        file_size_bytes=1024,
        has_text_layer=True,
        original_filename="statement.pdf",
        uploaded_by="user_123",
    )
    assert receipt.file_size_bytes == 1024
    assert receipt.has_text_layer is True


def test_ingest_receipt_mime_type_must_be_pdf():
    with pytest.raises(ValidationError):
        IngestReceipt(
            statement_id="stmt_abc123",
            sha256="a" * 64,
            pages=3,
            stored=True,
            original_path="/uploads/test.pdf",
            uploaded_at=datetime.now(timezone.utc),
            mime_type="text/plain",  # Must be application/pdf
        )
