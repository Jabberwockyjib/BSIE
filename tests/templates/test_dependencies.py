"""Template dependency injection tests."""
import pytest
from pathlib import Path

from bsie.templates.dependencies import (
    get_template_registry,
    create_template_registry,
    reset_template_registry,
)
from bsie.templates.registry import TemplateRegistry


@pytest.fixture(autouse=True)
def reset_global_registry():
    """Reset global registry before and after each test."""
    reset_template_registry()
    yield
    reset_template_registry()


def test_get_template_registry_returns_registry(tmp_path):
    """Should return a TemplateRegistry instance."""
    registry = get_template_registry(templates_dir=tmp_path)
    assert isinstance(registry, TemplateRegistry)


def test_get_template_registry_singleton(tmp_path):
    """Should return the same instance on subsequent calls."""
    registry1 = get_template_registry(templates_dir=tmp_path)
    registry2 = get_template_registry(templates_dir=tmp_path)
    assert registry1 is registry2


def test_create_template_registry_new_instance(tmp_path):
    """Should create new instances each time."""
    registry1 = create_template_registry(templates_dir=tmp_path)
    registry2 = create_template_registry(templates_dir=tmp_path)
    assert registry1 is not registry2


def test_create_template_registry_auto_load(tmp_path):
    """Should auto-load templates when auto_load=True."""
    # Create a template file
    toml_content = '''
[metadata]
template_id = "test_v1"
version = "1.0.0"
bank_family = "test"
statement_type = "checking"
segment = "personal"

[detect]
keywords = ["TEST"]
'''
    (tmp_path / "test.toml").write_text(toml_content)

    registry = create_template_registry(templates_dir=tmp_path, auto_load=True)
    assert len(registry.templates) == 1


def test_create_template_registry_no_auto_load(tmp_path):
    """Should not load templates when auto_load=False."""
    toml_content = '''
[metadata]
template_id = "test_v1"
version = "1.0.0"
bank_family = "test"
statement_type = "checking"
segment = "personal"

[detect]
keywords = ["TEST"]
'''
    (tmp_path / "test.toml").write_text(toml_content)

    registry = create_template_registry(templates_dir=tmp_path, auto_load=False)
    assert len(registry.templates) == 0


def test_reset_template_registry(tmp_path):
    """Should reset global registry to None."""
    get_template_registry(templates_dir=tmp_path)
    reset_template_registry()

    # Should create a new instance after reset
    registry1 = get_template_registry(templates_dir=tmp_path)
    reset_template_registry()
    registry2 = get_template_registry(templates_dir=tmp_path)

    assert registry1 is not registry2
