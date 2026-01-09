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
from bsie.templates.dependencies import (
    get_template_registry,
    create_template_registry,
    reset_template_registry,
)

__all__ = [
    "Template",
    "TemplateMetadataSection",
    "TemplateDetectSection",
    "TemplateTableSection",
    "TemplateColumnsSection",
    "parse_template",
    "TemplateParseError",
    "TemplateRegistry",
    "get_template_registry",
    "create_template_registry",
    "reset_template_registry",
]
