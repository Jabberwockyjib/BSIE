"""Storage path management."""
from pathlib import Path


class StoragePaths:
    """Manages storage directory structure."""

    def __init__(self, base_path: Path | str):
        self.base_path = Path(base_path)

        # Create directory structure
        self.pdfs_dir = self.base_path / "pdfs"
        self.artifacts_dir = self.base_path / "artifacts"
        self.temp_dir = self.base_path / "temp"

        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_pdf_path(self, statement_id: str) -> Path:
        """Get the storage path for a PDF."""
        return self.pdfs_dir / f"{statement_id}.pdf"

    def get_artifacts_dir(self, statement_id: str) -> Path:
        """Get the artifacts directory for a statement."""
        path = self.artifacts_dir / statement_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_artifact_path(self, statement_id: str, artifact_name: str) -> Path:
        """Get the path for a specific artifact."""
        return self.get_artifacts_dir(statement_id) / artifact_name
