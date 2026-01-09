"""Template registry for managing TOML templates."""
from pathlib import Path
from typing import Dict, Optional

from bsie.templates.schema import Template


class TemplateRegistry:
    """
    Registry for loading and managing extraction templates.

    Templates are stored as TOML files in the filesystem (Git-versioned)
    and their metadata is indexed in Postgres for querying.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the template registry.

        Args:
            templates_dir: Directory containing template TOML files.
                          Defaults to 'templates/' relative to project root.
        """
        if templates_dir is None:
            # Default to templates/ in project root
            templates_dir = Path(__file__).parent.parent.parent.parent / "templates"

        self._templates_dir = templates_dir
        self._templates: Dict[str, Template] = {}

    @property
    def templates_dir(self) -> Path:
        """Get the templates directory."""
        return self._templates_dir

    @property
    def templates(self) -> Dict[str, Template]:
        """Get loaded templates (template_id -> Template)."""
        return self._templates
