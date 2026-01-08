"""Base schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.base import BsieBaseModel, BoundingBox, Provenance


def test_bsie_base_model_serializes_to_json():
    class TestModel(BsieBaseModel):
        name: str
        value: int

    model = TestModel(name="test", value=42)
    json_str = model.model_dump_json()
    assert '"name":"test"' in json_str or '"name": "test"' in json_str


def test_bounding_box_validates_range():
    # Valid
    bbox = BoundingBox(bbox=[0.0, 0.1, 0.9, 1.0])
    assert bbox.bbox == [0.0, 0.1, 0.9, 1.0]

    # Invalid - out of range
    with pytest.raises(ValidationError):
        BoundingBox(bbox=[0.0, 0.1, 1.5, 1.0])


def test_bounding_box_requires_four_values():
    with pytest.raises(ValidationError):
        BoundingBox(bbox=[0.0, 0.1, 0.9])


def test_provenance_requires_all_fields():
    prov = Provenance(
        page=1,
        bbox=[0.1, 0.2, 0.8, 0.9],
        source_pdf="stmt_abc123",
    )
    assert prov.page == 1


def test_provenance_optional_fields():
    prov = Provenance(
        page=1,
        bbox=[0.1, 0.2, 0.8, 0.9],
        source_pdf="stmt_abc123",
        extraction_method="camelot_stream",
        confidence=0.95,
    )
    assert prov.confidence == 0.95
