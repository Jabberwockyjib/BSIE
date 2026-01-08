"""FastAPI application factory."""
from fastapi import FastAPI

from bsie.api.routes import health


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="BSIE",
        description="Bank Statement Intelligence Engine",
        version="0.1.0",
    )

    app.include_router(health.router)

    return app
