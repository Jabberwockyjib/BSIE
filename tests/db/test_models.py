"""Database model tests."""
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bsie.db.engine import create_engine, get_session_factory
from bsie.db.base import Base
from bsie.db.models import Statement


@pytest.fixture
async def db_session():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_statement_model_has_required_fields():
    stmt = Statement(
        id="stmt_test123",
        sha256="a" * 64,
        original_filename="test.pdf",
        file_size_bytes=1024,
        page_count=5,
        current_state="UPLOADED",
    )
    assert stmt.id == "stmt_test123"
    assert stmt.sha256 == "a" * 64
    assert stmt.current_state == "UPLOADED"


@pytest.mark.asyncio
async def test_statement_can_be_persisted(db_session: AsyncSession):
    stmt = Statement(
        id="stmt_persist",
        sha256="b" * 64,
        original_filename="persist.pdf",
        file_size_bytes=2048,
        page_count=3,
        current_state="UPLOADED",
    )
    db_session.add(stmt)
    await db_session.commit()

    result = await db_session.execute(
        select(Statement).where(Statement.id == "stmt_persist")
    )
    loaded = result.scalar_one()
    assert loaded.sha256 == "b" * 64
    assert loaded.page_count == 3
