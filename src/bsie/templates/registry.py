"""Template registry for managing TOML templates."""
import logging
from pathlib import Path
from typing import Dict, Optional

from bsie.templates.schema import Template
from bsie.templates.parser import parse_template, TemplateParseError

logger = logging.getLogger(__name__)


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

    def load_template(self, file_path: Path) -> Template:
        """
        Load a single template from a TOML file.

        Args:
            file_path: Path to the TOML template file.

        Returns:
            Parsed and validated Template object.

        Raises:
            TemplateParseError: If parsing or validation fails.
        """
        template = parse_template(file_path)
        self._templates[template.metadata.template_id] = template
        return template

    def load_all(self) -> int:
        """
        Load all templates from the templates directory.

        Recursively searches for .toml files and loads them.
        Invalid templates are skipped with a warning log.

        Returns:
            Number of templates successfully loaded.
        """
        if not self._templates_dir.exists():
            logger.warning(f"Templates directory does not exist: {self._templates_dir}")
            return 0

        loaded = 0
        for toml_file in self._templates_dir.rglob("*.toml"):
            try:
                self.load_template(toml_file)
                loaded += 1
                logger.debug(f"Loaded template: {toml_file}")
            except TemplateParseError as e:
                logger.warning(f"Failed to load template {toml_file}: {e}")

        logger.info(f"Loaded {loaded} templates from {self._templates_dir}")
        return loaded
