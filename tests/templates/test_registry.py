"""Template registry tests."""
import pytest
from pathlib import Path

from bsie.templates.registry import TemplateRegistry


def test_registry_instantiation(tmp_path):
    """Registry should instantiate with a templates directory."""
    registry = TemplateRegistry(templates_dir=tmp_path)
    assert registry.templates_dir == tmp_path


def test_registry_default_templates_dir():
    """Registry should have a default templates directory."""
    registry = TemplateRegistry()
    assert registry.templates_dir is not None
    assert "templates" in str(registry.templates_dir)


def test_registry_templates_dict_empty_initially(tmp_path):
    """Registry should have empty templates dict before loading."""
    registry = TemplateRegistry(templates_dir=tmp_path)
    assert len(registry.templates) == 0
