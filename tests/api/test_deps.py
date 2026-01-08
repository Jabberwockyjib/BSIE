"""API dependency tests."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bsie.api.deps import get_db


@pytest.mark.asyncio
async def test_get_db_yields_session(db_engine):
    from bsie.api.deps import init_db
    init_db(db_engine)

    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break
