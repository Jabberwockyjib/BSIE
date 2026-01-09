"""Template package."""
from bsie.templates.schema import (
    Template,
    TemplateMetadataSection,
    TemplateDetectSection,
    TemplateTableSection,
    TemplateColumnsSection,
)
from bsie.templates.parser import parse_template, TemplateParseError
from bsie.templates.registry import TemplateRegistry

__all__ = [
    "Template",
    "TemplateMetadataSection",
    "TemplateDetectSection",
    "TemplateTableSection",
    "TemplateColumnsSection",
    "parse_template",
    "TemplateParseError",
    "TemplateRegistry",
]
