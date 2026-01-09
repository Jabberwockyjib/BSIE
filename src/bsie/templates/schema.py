"""Template Pydantic schema matching TOML structure."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TemplateMetadataSection(BaseModel):
    """Template metadata section."""
    template_id: str
    version: str
    bank_family: str
    statement_type: str  # checking, savings, credit_card
    segment: str  # personal, business, unknown
    description: Optional[str] = None


class TemplateDetectSection(BaseModel):
    """Template detection section."""
    keywords: List[str] = Field(default_factory=list)
    keyword_match_threshold: int = 1
    header_patterns: List[str] = Field(default_factory=list)
    required_text: List[str] = Field(default_factory=list)
    negative_patterns: List[str] = Field(default_factory=list)
    detect_pages: List[int] = Field(default_factory=lambda: [1])


class TemplateTableSection(BaseModel):
    """Template table location section."""
    primary: Optional[Dict[str, Any]] = None
    multi_page: Optional[Dict[str, Any]] = None


class TemplateColumnsSection(BaseModel):
    """Template column mapping section."""
    expected_count: Optional[int] = None
    map: Dict[str, str] = Field(default_factory=dict)


class Template(BaseModel):
    """Complete template schema."""
    metadata: TemplateMetadataSection
    detect: TemplateDetectSection
    preprocess: Optional[Dict[str, Any]] = None
    table: Optional[TemplateTableSection] = None
    extraction: Optional[Dict[str, Any]] = None
    columns: Optional[TemplateColumnsSection] = None
    parsing: Optional[Dict[str, Any]] = None
    normalization: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
