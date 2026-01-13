"""Ingest service tests."""
import pytest
from pathlib import Path

from bsie.services.ingest import IngestService
from bsie.schemas import IngestReceipt
from bsie.storage import StoragePaths
from bsie.state.controller import StateController


@pytest.fixture
def storage(tmp_path):
    return StoragePaths(base_path=tmp_path)


@pytest.fixture
def ingest_service(db_session, storage):
    controller = StateController(session=db_session)
    return IngestService(
        session=db_session,
        storage=storage,
        state_controller=controller,
    )


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal PDF for testing."""
    pdf_path = tmp_path / "sample.pdf"
    # Minimal valid PDF content
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
    return pdf_path


@pytest.mark.asyncio
async def test_ingest_creates_statement(ingest_service, sample_pdf):
    """Ingesting PDF should create statement record."""
    result = await ingest_service.ingest(
        file_path=sample_pdf,
        original_filename="test_statement.pdf",
    )

    assert result.statement_id.startswith("stmt_")
    assert result.stored is True
    assert result.pages >= 1


@pytest.mark.asyncio
async def test_ingest_computes_sha256(ingest_service, sample_pdf):
    """Ingest should compute SHA256 of file."""
    result = await ingest_service.ingest(
        file_path=sample_pdf,
        original_filename="test.pdf",
    )

    assert len(result.sha256) == 64
    assert all(c in "0123456789abcdef" for c in result.sha256)


@pytest.mark.asyncio
async def test_ingest_stores_file(ingest_service, sample_pdf, storage):
    """Ingest should copy file to storage."""
    result = await ingest_service.ingest(
        file_path=sample_pdf,
        original_filename="test.pdf",
    )

    # Verify file exists in storage
    stored_path = storage.get_pdf_path(result.statement_id)
    assert stored_path.exists()


@pytest.mark.asyncio
async def test_ingest_creates_receipt_artifact(ingest_service, sample_pdf, storage):
    """Ingest should create ingest_receipt.json artifact."""
    result = await ingest_service.ingest(
        file_path=sample_pdf,
        original_filename="test.pdf",
    )

    receipt_path = storage.get_artifact_path(result.statement_id, "ingest_receipt.json")
    assert receipt_path.exists()


@pytest.mark.asyncio
async def test_ingest_transitions_to_ingested(ingest_service, sample_pdf, db_session):
    """Ingest should transition statement to INGESTED state."""
    result = await ingest_service.ingest(
        file_path=sample_pdf,
        original_filename="test.pdf",
    )

    controller = StateController(session=db_session)
    state = await controller.get_current_state(result.statement_id)

    from bsie.state.constants import State
    assert state == State.INGESTED
