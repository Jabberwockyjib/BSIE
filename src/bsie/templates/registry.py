"""Template registry for managing TOML templates."""
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bsie.db.models import TemplateMetadata
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
        self._file_paths: Dict[str, Path] = {}  # template_id -> file_path

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
        template_id = template.metadata.template_id
        self._templates[template_id] = template
        self._file_paths[template_id] = file_path
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

    async def sync_to_database(
        self, session: AsyncSession, git_sha: str
    ) -> int:
        """
        Sync loaded template metadata to Postgres.

        Creates or updates TemplateMetadata records for all loaded templates.

        Args:
            session: SQLAlchemy async session.
            git_sha: Current Git SHA for version tracking.

        Returns:
            Number of templates synced.
        """
        synced = 0

        for template_id, template in self._templates.items():
            meta = template.metadata
            file_path = self._file_paths.get(template_id)

            # Check if already exists
            result = await session.execute(
                select(TemplateMetadata).where(
                    TemplateMetadata.template_id == template_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.version = meta.version
                existing.bank_family = meta.bank_family
                existing.statement_type = meta.statement_type
                existing.segment = meta.segment
                existing.git_sha = git_sha
                existing.file_path = str(file_path) if file_path else ""
            else:
                # Create new
                new_meta = TemplateMetadata(
                    template_id=template_id,
                    version=meta.version,
                    bank_family=meta.bank_family,
                    statement_type=meta.statement_type,
                    segment=meta.segment,
                    git_sha=git_sha,
                    file_path=str(file_path) if file_path else "",
                    status="draft",
                )
                session.add(new_meta)

            synced += 1

        await session.commit()
        logger.info(f"Synced {synced} templates to database")
        return synced
