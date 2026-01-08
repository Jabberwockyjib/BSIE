"""Ingest receipt schema."""
from typing import Optional, Literal
from datetime import datetime

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class IngestReceipt(BsieBaseModel):
    """Schema for ingest_receipt.json artifact."""

    statement_id: str
    sha256: str = Field(..., min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    pages: int = Field(..., ge=1)
    stored: bool
    original_path: str
    uploaded_at: datetime

    # Optional fields
    file_size_bytes: Optional[int] = Field(None, ge=1)
    has_text_layer: Optional[bool] = None
    original_filename: Optional[str] = None
    mime_type: Optional[Literal["application/pdf"]] = None
    uploaded_by: Optional[str] = None
