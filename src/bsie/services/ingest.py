"""PDF ingestion service."""
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from bsie.schemas import IngestReceipt
from bsie.state.controller import StateController
from bsie.state.constants import State
from bsie.storage import StoragePaths
from bsie.utils import generate_statement_id, compute_sha256


class IngestService:
    """Service for ingesting PDF statements."""

    def __init__(
        self,
        session: AsyncSession,
        storage: StoragePaths,
        state_controller: StateController,
    ):
        self._session = session
        self._storage = storage
        self._state_controller = state_controller

    async def ingest(
        self,
        file_path: Path,
        original_filename: str,
        uploaded_by: Optional[str] = None,
    ) -> IngestReceipt:
        """
        Ingest a PDF file.

        1. Generate statement_id
        2. Compute SHA256
        3. Copy to storage
        4. Get page count
        5. Create statement record (UPLOADED state)
        6. Transition to INGESTED with ingest_receipt
        """
        statement_id = generate_statement_id()
        sha256 = compute_sha256(file_path)
        file_size = file_path.stat().st_size

        # Copy to storage
        storage_path = self._storage.get_pdf_path(statement_id)
        shutil.copy2(file_path, storage_path)

        # Get page count (simplified - will use pypdf in next task)
        page_count = self._get_page_count(storage_path)

        # Create statement in UPLOADED state
        await self._state_controller.create_statement(
            statement_id=statement_id,
            sha256=sha256,
            original_filename=original_filename,
            file_size_bytes=file_size,
            page_count=page_count,
            storage_path=str(storage_path),
        )

        # Create ingest receipt
        receipt = IngestReceipt(
            statement_id=statement_id,
            sha256=sha256,
            pages=page_count,
            stored=True,
            original_path=str(file_path),
            uploaded_at=datetime.now(timezone.utc),
            file_size_bytes=file_size,
            original_filename=original_filename,
            uploaded_by=uploaded_by,
        )

        # Save receipt artifact
        receipt_path = self._storage.get_artifact_path(statement_id, "ingest_receipt.json")
        receipt_path.write_text(receipt.model_dump_json(indent=2))

        # Transition to INGESTED
        await self._state_controller.transition(
            statement_id=statement_id,
            to_state=State.INGESTED,
            trigger="ingestion_complete",
            artifacts={"ingest_receipt": str(receipt_path)},
        )

        return receipt

    def _get_page_count(self, pdf_path: Path) -> int:
        """Get page count from PDF. Simplified implementation."""
        # Will be updated with pypdf in Task 5.2
        return 1
