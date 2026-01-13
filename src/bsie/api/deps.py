"""FastAPI dependency injection."""
from typing import AsyncGenerator, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bsie.db.engine import get_session_factory
from bsie.services.ingest import IngestService
from bsie.state.controller import StateController
from bsie.storage import StoragePaths
from bsie.config import get_settings

_engine: Optional[AsyncEngine] = None
_session_factory = None


def init_db(engine: AsyncEngine) -> None:
    """Initialize database engine for dependency injection."""
    global _engine, _session_factory
    _engine = engine
    _session_factory = get_session_factory(engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _session_factory() as session:
        yield session


def get_ingest_service(db: AsyncSession = Depends(get_db)) -> IngestService:
    """Get IngestService dependency."""
    settings = get_settings()
    storage = StoragePaths(settings.storage_path)
    controller = StateController(session=db)
    return IngestService(session=db, storage=storage, state_controller=controller)
