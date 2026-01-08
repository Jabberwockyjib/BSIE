"""Storage utilities tests."""
import pytest
from pathlib import Path

from bsie.storage.paths import StoragePaths


def test_storage_paths_creates_directories(tmp_path):
    storage = StoragePaths(base_path=tmp_path)

    # Directories should be created
    assert storage.pdfs_dir.exists()
    assert storage.artifacts_dir.exists()
    assert storage.temp_dir.exists()


def test_statement_paths(tmp_path):
    storage = StoragePaths(base_path=tmp_path)
    statement_id = "stmt_abc123"

    pdf_path = storage.get_pdf_path(statement_id)
    artifacts_path = storage.get_artifacts_dir(statement_id)

    assert str(pdf_path).endswith("stmt_abc123.pdf")
    assert statement_id in str(artifacts_path)


def test_artifact_path(tmp_path):
    storage = StoragePaths(base_path=tmp_path)

    path = storage.get_artifact_path("stmt_abc123", "ingest_receipt.json")
    assert str(path).endswith("ingest_receipt.json")
    assert "stmt_abc123" in str(path)
