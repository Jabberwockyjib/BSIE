"""Base schema classes and common types."""
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BsieBaseModel(BaseModel):
    """Base model for all BSIE schemas."""

    model_config = ConfigDict(
        extra="forbid",  # Fail on unknown fields (additionalProperties: false)
        str_strip_whitespace=True,
    )


class BoundingBox(BsieBaseModel):
    """Normalized bounding box [x0, y0, x1, y1] in range [0, 1]."""

    bbox: List[float] = Field(..., min_length=4, max_length=4)

    @field_validator("bbox")
    @classmethod
    def validate_bbox_range(cls, v: List[float]) -> List[float]:
        for val in v:
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"Bounding box values must be in [0, 1], got {val}")
        return v


class Provenance(BsieBaseModel):
    """Provenance information for extracted data."""

    page: int = Field(..., ge=1)
    bbox: List[float] = Field(..., min_length=4, max_length=4)
    source_pdf: str
    extraction_method: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator("bbox")
    @classmethod
    def validate_bbox_range(cls, v: List[float]) -> List[float]:
        for val in v:
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"Bounding box values must be in [0, 1], got {val}")
        return v
