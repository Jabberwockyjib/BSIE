"""Statement API routes."""
import tempfile
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bsie.api.deps import get_db
from bsie.db.models import Statement
from bsie.services.ingest import IngestService
from bsie.storage import StoragePaths
from bsie.state.controller import StateController
from bsie.state.constants import State
from bsie.config import get_settings

router = APIRouter(prefix="/api/v1/statements", tags=["statements"])


# Response models
class UploadResponse(BaseModel):
    """Response for statement upload."""
    statement_id: str
    sha256: str
    pages: int
    status: str
    has_text_layer: Optional[bool] = None


class StatementResponse(BaseModel):
    """Response for statement details."""
    statement_id: str
    sha256: str
    original_filename: str
    file_size_bytes: int
    page_count: int
    state: str
    template_id: Optional[str] = None


class StateResponse(BaseModel):
    """Response for statement state."""
    statement_id: str
    current_state: str
    version: int


class ArtifactInfo(BaseModel):
    """Information about an artifact."""
    name: str
    path: str


class ArtifactsResponse(BaseModel):
    """Response for statement artifacts."""
    statement_id: str
    artifacts: List[ArtifactInfo]


class StatementsListResponse(BaseModel):
    """Response for paginated statement list."""
    statements: List[StatementResponse]
    total: int
    page: int
    page_size: int


@router.post("", status_code=201, response_model=UploadResponse)
async def upload_statement(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF statement for processing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "File must be a PDF")

    settings = get_settings()
    storage = StoragePaths(settings.storage_path)
    controller = StateController(session=db)
    service = IngestService(session=db, storage=storage, state_controller=controller)

    # Save upload to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Validate PDF before processing
        if not service.validate_pdf(tmp_path):
            raise HTTPException(400, "Invalid or corrupted PDF file")

        # Check for duplicate by SHA256
        from bsie.utils import compute_sha256
        sha256 = compute_sha256(tmp_path)

        result = await db.execute(
            select(Statement).where(Statement.sha256 == sha256)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                409,
                f"Duplicate file. Statement {existing.id} has the same content."
            )

        receipt = await service.ingest(
            file_path=tmp_path,
            original_filename=file.filename,
        )
        return UploadResponse(
            statement_id=receipt.statement_id,
            sha256=receipt.sha256,
            pages=receipt.pages,
            status="INGESTED",
            has_text_layer=receipt.has_text_layer,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/{statement_id}", response_model=StatementResponse)
async def get_statement(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get statement details by ID."""
    result = await db.execute(
        select(Statement).where(Statement.id == statement_id)
    )
    statement = result.scalar_one_or_none()

    if not statement:
        raise HTTPException(404, f"Statement {statement_id} not found")

    return StatementResponse(
        statement_id=statement.id,
        sha256=statement.sha256,
        original_filename=statement.original_filename,
        file_size_bytes=statement.file_size_bytes,
        page_count=statement.page_count,
        state=statement.current_state,
        template_id=statement.template_id,
    )


@router.get("/{statement_id}/state", response_model=StateResponse)
async def get_statement_state(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current state of a statement."""
    controller = StateController(session=db)
    statement = await controller.get_statement(statement_id)

    if not statement:
        raise HTTPException(404, f"Statement {statement_id} not found")

    return StateResponse(
        statement_id=statement.id,
        current_state=statement.current_state,
        version=statement.state_version,
    )


@router.get("/{statement_id}/artifacts", response_model=ArtifactsResponse)
async def get_statement_artifacts(
    statement_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get list of artifacts for a statement."""
    # Verify statement exists
    result = await db.execute(
        select(Statement).where(Statement.id == statement_id)
    )
    statement = result.scalar_one_or_none()

    if not statement:
        raise HTTPException(404, f"Statement {statement_id} not found")

    settings = get_settings()
    storage = StoragePaths(settings.storage_path)
    artifacts_dir = storage.get_artifacts_dir(statement_id)

    artifacts = []
    if artifacts_dir.exists():
        for artifact_file in artifacts_dir.iterdir():
            if artifact_file.is_file():
                artifacts.append(ArtifactInfo(
                    name=artifact_file.name,
                    path=str(artifact_file),
                ))

    return ArtifactsResponse(
        statement_id=statement_id,
        artifacts=artifacts,
    )


@router.get("", response_model=StatementsListResponse)
async def list_statements(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    state: Optional[str] = Query(None, description="Filter by state"),
    db: AsyncSession = Depends(get_db),
):
    """List statements with pagination."""
    # Build query
    query = select(Statement)
    count_query = select(func.count(Statement.id))

    if state:
        # Validate state
        try:
            State(state)
        except ValueError:
            raise HTTPException(400, f"Invalid state: {state}")
        query = query.where(Statement.current_state == state)
        count_query = count_query.where(Statement.current_state == state)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Statement.created_at.desc())

    result = await db.execute(query)
    statements = result.scalars().all()

    return StatementsListResponse(
        statements=[
            StatementResponse(
                statement_id=s.id,
                sha256=s.sha256,
                original_filename=s.original_filename,
                file_size_bytes=s.file_size_bytes,
                page_count=s.page_count,
                state=s.current_state,
                template_id=s.template_id,
            )
            for s in statements
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
