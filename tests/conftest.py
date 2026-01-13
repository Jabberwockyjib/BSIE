"""Shared pytest fixtures."""
import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from bsie.db.engine import create_engine, get_session_factory
from bsie.db.base import Base
# Import models to register them with Base.metadata
from bsie.db.models import Statement, StateHistory  # noqa: F401


# Minimal valid PDF content
MINIMAL_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""


@pytest.fixture
def minimal_pdf_bytes():
    """Minimal valid PDF content as bytes."""
    return MINIMAL_PDF_BYTES


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal PDF file for testing."""
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(MINIMAL_PDF_BYTES)
    return pdf_path


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncSession:
    """Create a database session for testing."""
    session_factory = get_session_factory(db_engine)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def db_session_with_statement(db_engine) -> AsyncSession:
    """Create a database session with a test statement in UPLOADED state."""
    session_factory = get_session_factory(db_engine)
    async with session_factory() as session:
        statement = Statement(
            id="stmt_test001",
            sha256="a" * 64,
            original_filename="test.pdf",
            file_size_bytes=1024,
            page_count=2,
            current_state="UPLOADED",
            state_version=1,
        )
        session.add(statement)
        await session.commit()
        yield session
