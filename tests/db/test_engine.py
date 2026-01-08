"""Database engine tests."""
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bsie.db.engine import create_engine, get_session_factory
from bsie.db.base import Base


def test_create_engine_returns_async_engine():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    assert isinstance(engine, AsyncEngine)


@pytest.mark.asyncio
async def test_session_factory_creates_sessions():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        assert isinstance(session, AsyncSession)


def test_base_has_metadata():
    assert hasattr(Base, "metadata")
