"""Tests for Chase template fixture."""
import pytest
from pathlib import Path

from bsie.templates import parse_template, TemplateRegistry


# Path to the actual templates directory
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "templates"


def test_chase_checking_template_parses():
    """The Chase checking template should parse without errors."""
    template_path = TEMPLATES_DIR / "chase" / "checking_personal_v1.toml"

    if not template_path.exists():
        pytest.skip(f"Template not found: {template_path}")

    template = parse_template(template_path)

    assert template.metadata.template_id == "chase_checking_personal_v1"
    assert template.metadata.bank_family == "chase"
    assert template.metadata.statement_type == "checking"
    assert template.metadata.segment == "personal"
    assert template.metadata.version == "1.0.0"


def test_chase_template_has_detect_section():
    """Chase template should have proper detection rules."""
    template_path = TEMPLATES_DIR / "chase" / "checking_personal_v1.toml"

    if not template_path.exists():
        pytest.skip(f"Template not found: {template_path}")

    template = parse_template(template_path)

    assert "CHASE" in template.detect.keywords
    assert len(template.detect.required_text) > 0
    assert template.detect.detect_pages == [1]


def test_chase_fixture_loads_in_registry():
    """Chase fixture should load via TemplateRegistry."""
    if not FIXTURES_DIR.exists():
        pytest.skip(f"Fixtures directory not found: {FIXTURES_DIR}")

    registry = TemplateRegistry(templates_dir=FIXTURES_DIR)
    loaded = registry.load_all()

    assert loaded >= 1
    assert "chase_checking_personal_v1" in registry.templates

    template = registry.get_template_by_id("chase_checking_personal_v1")
    assert template is not None
    assert template.metadata.bank_family == "chase"


def test_chase_template_findable_by_classification():
    """Chase template should be findable by bank/type classification."""
    if not FIXTURES_DIR.exists():
        pytest.skip(f"Fixtures directory not found: {FIXTURES_DIR}")

    registry = TemplateRegistry(templates_dir=FIXTURES_DIR)
    registry.load_all()

    matches = registry.find_templates_for_classification(
        bank_family="chase",
        statement_type="checking",
    )

    assert len(matches) >= 1
    assert any(t.metadata.template_id == "chase_checking_personal_v1" for t in matches)
