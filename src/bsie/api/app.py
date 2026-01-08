"""FastAPI application factory."""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from bsie.api.routes import health
from bsie.api.deps import init_db
from bsie.db.engine import create_engine
from bsie.db.base import Base
from bsie.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    engine = app.state.engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    init_db(engine)

    yield

    # Shutdown
    await engine.dispose()


def create_app(database_url: Optional[str] = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="BSIE",
        description="Bank Statement Intelligence Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Create database engine
    db_url = database_url or settings.database_url
    app.state.engine = create_engine(db_url)

    # Register routes
    app.include_router(health.router)

    return app
