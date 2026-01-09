"""Shared pytest fixtures."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bsie.db.engine import create_engine, get_session_factory
from bsie.db.base import Base
# Import models to register them with Base.metadata
from bsie.db.models import Statement, StateHistory  # noqa: F401


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
