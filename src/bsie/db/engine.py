"""Database engine and session management."""
from typing import Any, Callable

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(url: str, **kwargs: Any) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    return create_async_engine(url, **kwargs)


def get_session_factory(engine: AsyncEngine) -> Callable[[], AsyncSession]:
    """Create a session factory for the given engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
