"""FastAPI dependency injection for TemplateRegistry."""
from pathlib import Path
from typing import Optional

from bsie.templates.registry import TemplateRegistry

# Global registry instance (singleton pattern for caching)
_registry: Optional[TemplateRegistry] = None


def get_template_registry(
    templates_dir: Optional[Path] = None,
    auto_load: bool = True,
) -> TemplateRegistry:
    """
    Get the global TemplateRegistry instance.

    Creates and loads the registry on first call, returns cached instance after.

    Args:
        templates_dir: Override default templates directory.
        auto_load: If True, automatically loads all templates on creation.

    Returns:
        The global TemplateRegistry instance.

    Usage in FastAPI:
        @app.get("/templates")
        async def list_templates(
            registry: TemplateRegistry = Depends(get_template_registry),
        ):
            return list(registry.templates.keys())
    """
    global _registry

    if _registry is None:
        _registry = TemplateRegistry(templates_dir=templates_dir)
        if auto_load:
            _registry.load_all()

    return _registry


def create_template_registry(
    templates_dir: Optional[Path] = None,
    auto_load: bool = True,
) -> TemplateRegistry:
    """
    Factory function to create a new TemplateRegistry instance.

    Unlike get_template_registry, this always creates a new instance.
    Useful for testing or when you need isolated registries.

    Args:
        templates_dir: Directory containing template TOML files.
        auto_load: If True, automatically loads all templates.

    Returns:
        New TemplateRegistry instance.
    """
    registry = TemplateRegistry(templates_dir=templates_dir)
    if auto_load:
        registry.load_all()
    return registry


def reset_template_registry() -> None:
    """
    Reset the global registry instance.

    Useful for testing to ensure clean state between tests.
    """
    global _registry
    _registry = None
