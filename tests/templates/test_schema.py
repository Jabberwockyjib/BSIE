"""Template schema tests."""
import pytest
from pydantic import ValidationError

from bsie.templates.schema import (
    TemplateMetadataSection,
    TemplateDetectSection,
    Template,
)


def test_metadata_section_valid():
    meta = TemplateMetadataSection(
        template_id="chase_checking_v1",
        version="1.0.0",
        bank_family="chase",
        statement_type="checking",
        segment="personal",
    )
    assert meta.template_id == "chase_checking_v1"


def test_metadata_section_requires_fields():
    with pytest.raises(ValidationError):
        TemplateMetadataSection(
            template_id="test",
            # Missing required fields
        )


def test_detect_section():
    detect = TemplateDetectSection(
        keywords=["CHASE", "JPMorgan"],
        required_text=["Account Activity"],
    )
    assert len(detect.keywords) == 2


def test_template_minimal():
    template = Template(
        metadata=TemplateMetadataSection(
            template_id="test_v1",
            version="1.0.0",
            bank_family="test",
            statement_type="checking",
            segment="personal",
        ),
        detect=TemplateDetectSection(
            keywords=["TEST"],
        ),
    )
    assert template.metadata.template_id == "test_v1"
