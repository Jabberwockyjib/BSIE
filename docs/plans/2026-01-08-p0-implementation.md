# P0 Implementation Plan — BSIE Core Infrastructure

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the foundational P0 components: Schema Validation, State Controller, Template Registry, and Ingest Pipeline.

**Architecture:** FastAPI backend with PostgreSQL for state/metadata, Redis for job queues, local filesystem for PDF storage. All state transitions flow through a centralized State Controller. Templates stored as TOML in Git, metadata in Postgres.

**Tech Stack:** Python 3.11+, FastAPI, PostgreSQL 15, Redis 7, Pydantic v2, pytest, SQLAlchemy 2.0

---

## Sprint Overview

| Sprint | Focus | Tasks | Milestone |
|--------|-------|-------|-----------|
| 1 | Project Foundation | 15 | Runnable FastAPI app with test infrastructure |
| 2 | Schema Validation | 14 | All JSON schemas implemented with validators |
| 3 | State Controller | 18 | Full state machine with transitions |
| 4 | Template Registry | 16 | Git+Postgres template storage working |
| 5 | Ingest Pipeline | 15 | PDF upload through INGESTED state |

**Total: 78 tasks**

---

## Sprint 1: Project Foundation (15 tasks)

**Goal:** Establish project structure, database connections, and test infrastructure.

**Milestone:** `pytest` runs, FastAPI serves `/health`, database migrations work.

---

### Task 1.1: Initialize Python Package Structure

**Files:**
- Create: `pyproject.toml`
- Create: `src/bsie/__init__.py`
- Create: `src/bsie/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "bsie"
version = "0.1.0"
description = "Bank Statement Intelligence Engine"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "sqlalchemy>=2.0.25",
    "asyncpg>=0.29.0",
    "redis>=5.0.0",
    "python-multipart>=0.0.6",
    "toml>=0.10.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.26.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/bsie"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

**Step 2: Create package files**

```python
# src/bsie/__init__.py
"""Bank Statement Intelligence Engine."""
__version__ = "0.1.0"
```

```python
# src/bsie/py.typed
# Marker file for PEP 561
```

```python
# tests/__init__.py
"""BSIE test suite."""
```

```python
# tests/conftest.py
"""Shared pytest fixtures."""
import pytest

@pytest.fixture
def anyio_backend():
    return "asyncio"
```

**Step 3: Create virtual environment and install**

Run:
```bash
cd /Users/brian/dev/BSIE
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: Installation completes without errors.

**Step 4: Verify pytest runs**

Run: `pytest --collect-only`

Expected: "no tests ran" (collection works, no tests yet)

**Step 5: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: initialize python package structure"
```

---

### Task 1.2: Create FastAPI Application Skeleton

**Files:**
- Create: `src/bsie/api/__init__.py`
- Create: `src/bsie/api/app.py`
- Create: `src/bsie/api/routes/__init__.py`
- Create: `src/bsie/api/routes/health.py`
- Test: `tests/api/__init__.py`
- Test: `tests/api/test_health.py`

**Step 1: Write the failing test**

```python
# tests/api/__init__.py
"""API tests."""
```

```python
# tests/api/test_health.py
"""Health endpoint tests."""
import pytest
from httpx import AsyncClient, ASGITransport

from bsie.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_health.py -v`

Expected: FAIL with "cannot import name 'create_app'"

**Step 3: Write minimal implementation**

```python
# src/bsie/api/__init__.py
"""BSIE API package."""
```

```python
# src/bsie/api/routes/__init__.py
"""API route modules."""
```

```python
# src/bsie/api/routes/health.py
"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Return health status."""
    return {"status": "ok"}
```

```python
# src/bsie/api/app.py
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_health.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/api/ tests/api/
git commit -m "feat: add FastAPI app with health endpoint"
```

---

### Task 1.3: Add Configuration Management

**Files:**
- Create: `src/bsie/config.py`
- Create: `config/app.toml`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

```python
# tests/test_config.py
"""Configuration tests."""
import os
import pytest
from pathlib import Path

from bsie.config import Settings, load_settings


def test_settings_has_required_fields():
    settings = Settings()
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "redis_url")
    assert hasattr(settings, "storage_path")


def test_settings_loads_defaults():
    settings = Settings()
    assert settings.api_prefix == "/api/v1"
    assert settings.debug is False


def test_load_settings_from_toml(tmp_path):
    config_file = tmp_path / "app.toml"
    config_file.write_text('''
[database]
url = "postgresql+asyncpg://test:test@localhost/test"

[redis]
url = "redis://localhost:6379/1"

[storage]
path = "/tmp/bsie"
''')

    settings = load_settings(config_file)
    assert settings.database_url == "postgresql+asyncpg://test:test@localhost/test"
    assert settings.redis_url == "redis://localhost:6379/1"
    assert settings.storage_path == Path("/tmp/bsie")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`

Expected: FAIL with "cannot import name 'Settings'"

**Step 3: Write minimal implementation**

```python
# src/bsie/config.py
"""Application configuration."""
import os
from pathlib import Path
from typing import Optional

import toml
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings."""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://bsie:bsie@localhost:5432/bsie",
        description="PostgreSQL connection URL"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # Storage
    storage_path: Path = Field(
        default=Path("./storage"),
        description="Path for PDF and artifact storage"
    )

    # API
    api_prefix: str = Field(
        default="/api/v1",
        description="API route prefix"
    )

    # Debug
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Load settings from TOML file and environment."""
    config_data = {}

    if config_path and config_path.exists():
        raw = toml.load(config_path)
        # Flatten nested config
        if "database" in raw:
            config_data["database_url"] = raw["database"].get("url")
        if "redis" in raw:
            config_data["redis_url"] = raw["redis"].get("url")
        if "storage" in raw:
            config_data["storage_path"] = raw["storage"].get("path")
        if "api" in raw:
            config_data["api_prefix"] = raw["api"].get("prefix")
        if "debug" in raw:
            config_data["debug"] = raw.get("debug")

    # Filter None values
    config_data = {k: v for k, v in config_data.items() if v is not None}

    return Settings(**config_data)


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        config_path = Path(os.environ.get("BSIE_CONFIG", "config/app.toml"))
        _settings = load_settings(config_path)
    return _settings
```

```toml
# config/app.toml
# BSIE Application Configuration

[database]
url = "postgresql+asyncpg://bsie:bsie@localhost:5432/bsie"

[redis]
url = "redis://localhost:6379/0"

[storage]
path = "./storage"

[api]
prefix = "/api/v1"

debug = false
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/config.py config/ tests/test_config.py
git commit -m "feat: add TOML-based configuration management"
```

---

### Task 1.4: Add Database Connection Layer

**Files:**
- Create: `src/bsie/db/__init__.py`
- Create: `src/bsie/db/engine.py`
- Create: `src/bsie/db/base.py`
- Test: `tests/db/__init__.py`
- Test: `tests/db/test_engine.py`

**Step 1: Write the failing test**

```python
# tests/db/__init__.py
"""Database tests."""
```

```python
# tests/db/test_engine.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_engine.py -v`

Expected: FAIL with "cannot import name 'create_engine'"

**Step 3: Update dependencies and implement**

First, add aiosqlite for testing:
```bash
# Add to pyproject.toml under dev dependencies:
# "aiosqlite>=0.19.0",
pip install aiosqlite
```

```python
# src/bsie/db/__init__.py
"""Database package."""
from bsie.db.engine import create_engine, get_session_factory
from bsie.db.base import Base

__all__ = ["create_engine", "get_session_factory", "Base"]
```

```python
# src/bsie/db/base.py
"""SQLAlchemy declarative base."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass
```

```python
# src/bsie/db/engine.py
"""Database engine and session management."""
from typing import Callable
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(url: str, **kwargs) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    return create_async_engine(url, **kwargs)


def get_session_factory(engine: AsyncEngine) -> Callable[[], AsyncSession]:
    """Create a session factory for the given engine."""
    return asynccontextmanager(
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_engine.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/db/ tests/db/
git commit -m "feat: add async database engine and session factory"
```

---

### Task 1.5: Create Statement Model

**Files:**
- Create: `src/bsie/db/models/__init__.py`
- Create: `src/bsie/db/models/statement.py`
- Test: `tests/db/test_models.py`

**Step 1: Write the failing test**

```python
# tests/db/test_models.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_models.py -v`

Expected: FAIL with "cannot import name 'Statement'"

**Step 3: Write minimal implementation**

```python
# src/bsie/db/models/__init__.py
"""Database models."""
from bsie.db.models.statement import Statement

__all__ = ["Statement"]
```

```python
# src/bsie/db/models/statement.py
"""Statement database model."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from bsie.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Statement(Base):
    """Bank statement record."""

    __tablename__ = "statements"

    # Primary key - statement_id
    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # File metadata
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Pipeline state
    current_state: Mapped[str] = mapped_column(String(50), index=True)
    state_version: Mapped[int] = mapped_column(Integer, default=1)

    # Template binding (set after TEMPLATE_SELECTED)
    template_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    template_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Error tracking
    error_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Artifacts paths (JSON object mapping artifact name to path)
    artifacts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_models.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/db/models/ tests/db/test_models.py
git commit -m "feat: add Statement database model"
```

---

### Task 1.6: Create StateHistory Model

**Files:**
- Modify: `src/bsie/db/models/__init__.py`
- Create: `src/bsie/db/models/state_history.py`
- Modify: `tests/db/test_models.py`

**Step 1: Write the failing test**

Add to `tests/db/test_models.py`:

```python
from bsie.db.models import Statement, StateHistory


@pytest.mark.asyncio
async def test_state_history_records_transitions(db_session: AsyncSession):
    # Create statement
    stmt = Statement(
        id="stmt_history",
        sha256="c" * 64,
        original_filename="history.pdf",
        file_size_bytes=1024,
        page_count=1,
        current_state="UPLOADED",
    )
    db_session.add(stmt)
    await db_session.commit()

    # Record state transition
    history = StateHistory(
        statement_id="stmt_history",
        from_state=None,
        to_state="UPLOADED",
        trigger="upload",
    )
    db_session.add(history)
    await db_session.commit()

    result = await db_session.execute(
        select(StateHistory).where(StateHistory.statement_id == "stmt_history")
    )
    records = result.scalars().all()
    assert len(records) == 1
    assert records[0].to_state == "UPLOADED"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_models.py::test_state_history_records_transitions -v`

Expected: FAIL with "cannot import name 'StateHistory'"

**Step 3: Write minimal implementation**

```python
# src/bsie/db/models/state_history.py
"""State history model for audit trail."""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from bsie.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_id() -> str:
    return str(uuid4())


class StateHistory(Base):
    """Record of state transitions for audit trail."""

    __tablename__ = "state_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    statement_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("statements.id"), index=True
    )

    # Transition details
    from_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_state: Mapped[str] = mapped_column(String(50))
    trigger: Mapped[str] = mapped_column(String(100))

    # Metadata
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    artifacts_created: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Duration tracking
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
```

Update `src/bsie/db/models/__init__.py`:

```python
# src/bsie/db/models/__init__.py
"""Database models."""
from bsie.db.models.statement import Statement
from bsie.db.models.state_history import StateHistory

__all__ = ["Statement", "StateHistory"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_models.py -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/bsie/db/models/
git commit -m "feat: add StateHistory model for audit trail"
```

---

### Task 1.7: Add Database Test Fixtures

**Files:**
- Modify: `tests/conftest.py`
- Modify: `pyproject.toml` (add aiosqlite)

**Step 1: Update pyproject.toml**

Add `aiosqlite>=0.19.0` to dev dependencies in pyproject.toml.

**Step 2: Create shared database fixtures**

```python
# tests/conftest.py
"""Shared pytest fixtures."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bsie.db.engine import create_engine, get_session_factory
from bsie.db.base import Base


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
```

**Step 3: Simplify test_models.py to use shared fixtures**

Update `tests/db/test_models.py` to remove the local `db_session` fixture (now using the shared one from conftest.py).

**Step 4: Run all tests**

Run: `pytest tests/ -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add tests/conftest.py pyproject.toml
git commit -m "feat: add shared database fixtures for testing"
```

---

### Task 1.8: Add API Dependency Injection for Database

**Files:**
- Create: `src/bsie/api/deps.py`
- Modify: `src/bsie/api/app.py`
- Test: `tests/api/test_deps.py`

**Step 1: Write the failing test**

```python
# tests/api/test_deps.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_deps.py -v`

Expected: FAIL with "cannot import name 'get_db'"

**Step 3: Write minimal implementation**

```python
# src/bsie/api/deps.py
"""FastAPI dependency injection."""
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bsie.db.engine import get_session_factory

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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_deps.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/api/deps.py tests/api/test_deps.py
git commit -m "feat: add database dependency injection for FastAPI"
```

---

### Task 1.9: Add Application Lifespan for Startup/Shutdown

**Files:**
- Modify: `src/bsie/api/app.py`
- Test: `tests/api/test_app.py`

**Step 1: Write the failing test**

```python
# tests/api/test_app.py
"""Application lifecycle tests."""
import pytest
from httpx import AsyncClient, ASGITransport

from bsie.api.app import create_app


@pytest.fixture
def app():
    return create_app(database_url="sqlite+aiosqlite:///:memory:")


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_app_starts_and_stops(client):
    """Test app lifecycle - database initialized on startup."""
    response = await client.get("/health")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_app.py -v`

Expected: FAIL (create_app doesn't accept database_url parameter)

**Step 3: Write implementation**

```python
# src/bsie/api/app.py
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_app.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/api/app.py tests/api/test_app.py
git commit -m "feat: add application lifespan with database initialization"
```

---

### Task 1.10: Create Entry Point Script

**Files:**
- Create: `src/bsie/__main__.py`

**Step 1: Create entry point**

```python
# src/bsie/__main__.py
"""BSIE application entry point."""
import uvicorn

from bsie.api.app import create_app


def main():
    """Run the BSIE application."""
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
```

**Step 2: Test it runs (manual)**

Run: `python -m bsie` (Ctrl+C to stop)

Expected: Server starts on port 8000

**Step 3: Commit**

```bash
git add src/bsie/__main__.py
git commit -m "feat: add application entry point"
```

---

### Task 1.11: Add Storage Directory Utilities

**Files:**
- Create: `src/bsie/storage/__init__.py`
- Create: `src/bsie/storage/paths.py`
- Test: `tests/test_storage.py`

**Step 1: Write the failing test**

```python
# tests/test_storage.py
"""Storage utilities tests."""
import pytest
from pathlib import Path

from bsie.storage.paths import StoragePaths


def test_storage_paths_creates_directories(tmp_path):
    storage = StoragePaths(base_path=tmp_path)

    # Directories should be created
    assert storage.pdfs_dir.exists()
    assert storage.artifacts_dir.exists()
    assert storage.temp_dir.exists()


def test_statement_paths(tmp_path):
    storage = StoragePaths(base_path=tmp_path)
    statement_id = "stmt_abc123"

    pdf_path = storage.get_pdf_path(statement_id)
    artifacts_path = storage.get_artifacts_dir(statement_id)

    assert str(pdf_path).endswith("stmt_abc123.pdf")
    assert statement_id in str(artifacts_path)


def test_artifact_path(tmp_path):
    storage = StoragePaths(base_path=tmp_path)

    path = storage.get_artifact_path("stmt_abc123", "ingest_receipt.json")
    assert str(path).endswith("ingest_receipt.json")
    assert "stmt_abc123" in str(path)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`

Expected: FAIL with "cannot import name 'StoragePaths'"

**Step 3: Write minimal implementation**

```python
# src/bsie/storage/__init__.py
"""Storage package."""
from bsie.storage.paths import StoragePaths

__all__ = ["StoragePaths"]
```

```python
# src/bsie/storage/paths.py
"""Storage path management."""
from pathlib import Path


class StoragePaths:
    """Manages storage directory structure."""

    def __init__(self, base_path: Path | str):
        self.base_path = Path(base_path)

        # Create directory structure
        self.pdfs_dir = self.base_path / "pdfs"
        self.artifacts_dir = self.base_path / "artifacts"
        self.temp_dir = self.base_path / "temp"

        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_pdf_path(self, statement_id: str) -> Path:
        """Get the storage path for a PDF."""
        return self.pdfs_dir / f"{statement_id}.pdf"

    def get_artifacts_dir(self, statement_id: str) -> Path:
        """Get the artifacts directory for a statement."""
        path = self.artifacts_dir / statement_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_artifact_path(self, statement_id: str, artifact_name: str) -> Path:
        """Get the path for a specific artifact."""
        return self.get_artifacts_dir(statement_id) / artifact_name
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/storage/ tests/test_storage.py
git commit -m "feat: add storage path management utilities"
```

---

### Task 1.12: Add Identifier Generation Utilities

**Files:**
- Create: `src/bsie/utils/__init__.py`
- Create: `src/bsie/utils/identifiers.py`
- Test: `tests/test_utils.py`

**Step 1: Write the failing test**

```python
# tests/test_utils.py
"""Utility function tests."""
import pytest
import re

from bsie.utils.identifiers import generate_statement_id, compute_sha256


def test_generate_statement_id_format():
    stmt_id = generate_statement_id()
    assert stmt_id.startswith("stmt_")
    assert len(stmt_id) == 21  # stmt_ + 16 chars


def test_generate_statement_id_unique():
    ids = [generate_statement_id() for _ in range(100)]
    assert len(set(ids)) == 100  # All unique


def test_compute_sha256(tmp_path):
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"test content")

    hash_value = compute_sha256(test_file)

    assert len(hash_value) == 64
    assert re.match(r"^[a-f0-9]{64}$", hash_value)


def test_compute_sha256_deterministic(tmp_path):
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"same content")

    hash1 = compute_sha256(test_file)
    hash2 = compute_sha256(test_file)

    assert hash1 == hash2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_utils.py -v`

Expected: FAIL with "cannot import name 'generate_statement_id'"

**Step 3: Write minimal implementation**

```python
# src/bsie/utils/__init__.py
"""Utility functions."""
from bsie.utils.identifiers import generate_statement_id, compute_sha256

__all__ = ["generate_statement_id", "compute_sha256"]
```

```python
# src/bsie/utils/identifiers.py
"""Identifier generation utilities."""
import hashlib
import secrets
from pathlib import Path


def generate_statement_id() -> str:
    """Generate a unique statement identifier."""
    return f"stmt_{secrets.token_hex(8)}"


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_utils.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/utils/ tests/test_utils.py
git commit -m "feat: add identifier generation utilities"
```

---

### Task 1.13: Add Timestamp Utilities

**Files:**
- Modify: `src/bsie/utils/__init__.py`
- Create: `src/bsie/utils/timestamps.py`
- Modify: `tests/test_utils.py`

**Step 1: Write the failing test**

Add to `tests/test_utils.py`:

```python
from datetime import datetime, timezone
from bsie.utils.timestamps import utc_now, format_iso8601, parse_iso8601


def test_utc_now_returns_utc_datetime():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


def test_format_iso8601():
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
    formatted = format_iso8601(dt)
    assert formatted == "2024-01-15T10:30:45Z"


def test_parse_iso8601():
    parsed = parse_iso8601("2024-01-15T10:30:45Z")
    assert parsed.year == 2024
    assert parsed.month == 1
    assert parsed.day == 15
    assert parsed.tzinfo == timezone.utc


def test_roundtrip():
    original = utc_now()
    formatted = format_iso8601(original)
    parsed = parse_iso8601(formatted)
    # Microseconds are lost in formatting, so compare to second precision
    assert abs((original - parsed).total_seconds()) < 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_utils.py::test_utc_now_returns_utc_datetime -v`

Expected: FAIL with "cannot import name 'utc_now'"

**Step 3: Write minimal implementation**

```python
# src/bsie/utils/timestamps.py
"""Timestamp utilities."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def format_iso8601(dt: datetime) -> str:
    """Format datetime as ISO-8601 string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso8601(s: str) -> datetime:
    """Parse ISO-8601 string to datetime."""
    # Handle Z suffix
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
```

Update `src/bsie/utils/__init__.py`:

```python
# src/bsie/utils/__init__.py
"""Utility functions."""
from bsie.utils.identifiers import generate_statement_id, compute_sha256
from bsie.utils.timestamps import utc_now, format_iso8601, parse_iso8601

__all__ = [
    "generate_statement_id",
    "compute_sha256",
    "utc_now",
    "format_iso8601",
    "parse_iso8601",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_utils.py -v`

Expected: All PASS

**Step 5: Commit**

```bash
git add src/bsie/utils/
git commit -m "feat: add timestamp utilities"
```

---

### Task 1.14: Create .gitignore and Project Hygiene

**Files:**
- Create: `.gitignore`
- Create: `.python-version`

**Step 1: Create .gitignore**

```gitignore
# .gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# Type checking
.mypy_cache/

# Storage (local dev)
storage/

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db
```

**Step 2: Create .python-version**

```
3.11
```

**Step 3: Commit**

```bash
git add .gitignore .python-version
git commit -m "chore: add .gitignore and python version file"
```

---

### Task 1.15: Run Full Test Suite and Verify Sprint 1 Complete

**Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short`

Expected: All tests PASS (should be ~15 tests)

**Step 2: Run type checking**

Run: `mypy src/bsie/`

Expected: No errors (or minor ones to fix)

**Step 3: Run linting**

Run: `ruff check src/ tests/`

Expected: No errors (or fix any found)

**Step 4: Verify app starts**

Run: `python -m bsie` (Ctrl+C to stop)

Expected: Server starts successfully

**Step 5: Final commit for Sprint 1**

```bash
git add -A
git commit -m "chore: sprint 1 complete - project foundation"
```

---

## Sprint 1 Complete

**Milestone Achieved:**
- Python package structure established
- FastAPI app running with `/health` endpoint
- PostgreSQL database layer with models
- Test infrastructure with fixtures
- Configuration management (TOML)
- Storage path utilities
- Identifier and timestamp utilities

**Next:** Sprint 2 - Schema Validation

---

## Sprint 2: Schema Validation (14 tasks)

**Goal:** Implement all JSON schema validators using Pydantic v2 models matching `json_schema_v2.md`.

**Milestone:** All artifact schemas defined, validation utilities working, comprehensive tests.

**Reference:** `/Users/brian/dev/BSIE/json_schema_v2.md`

---

### Task 2.1: Create Schema Package Structure

**Files:**
- Create: `src/bsie/schemas/__init__.py`
- Create: `src/bsie/schemas/base.py`
- Test: `tests/schemas/__init__.py`
- Test: `tests/schemas/test_base.py`

**Step 1: Write the failing test**

```python
# tests/schemas/__init__.py
"""Schema tests."""
```

```python
# tests/schemas/test_base.py
"""Base schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.base import BsieBaseModel, BoundingBox, Provenance


def test_bsie_base_model_serializes_to_json():
    class TestModel(BsieBaseModel):
        name: str
        value: int

    model = TestModel(name="test", value=42)
    json_str = model.model_dump_json()
    assert '"name":"test"' in json_str or '"name": "test"' in json_str


def test_bounding_box_validates_range():
    # Valid
    bbox = BoundingBox(bbox=[0.0, 0.1, 0.9, 1.0])
    assert bbox.bbox == [0.0, 0.1, 0.9, 1.0]

    # Invalid - out of range
    with pytest.raises(ValidationError):
        BoundingBox(bbox=[0.0, 0.1, 1.5, 1.0])


def test_bounding_box_requires_four_values():
    with pytest.raises(ValidationError):
        BoundingBox(bbox=[0.0, 0.1, 0.9])


def test_provenance_requires_all_fields():
    prov = Provenance(
        page=1,
        bbox=[0.1, 0.2, 0.8, 0.9],
        source_pdf="stmt_abc123",
    )
    assert prov.page == 1


def test_provenance_optional_fields():
    prov = Provenance(
        page=1,
        bbox=[0.1, 0.2, 0.8, 0.9],
        source_pdf="stmt_abc123",
        extraction_method="camelot_stream",
        confidence=0.95,
    )
    assert prov.confidence == 0.95
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_base.py -v`

Expected: FAIL with "cannot import name 'BsieBaseModel'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/__init__.py
"""Pydantic schemas for BSIE artifacts."""
```

```python
# src/bsie/schemas/base.py
"""Base schema classes and common types."""
from typing import Optional, List, Annotated
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BsieBaseModel(BaseModel):
    """Base model for all BSIE schemas."""

    model_config = ConfigDict(
        extra="forbid",  # Fail on unknown fields (additionalProperties: false)
        str_strip_whitespace=True,
    )


class BoundingBox(BsieBaseModel):
    """Normalized bounding box [x0, y0, x1, y1] in range [0, 1]."""

    bbox: List[float] = Field(..., min_length=4, max_length=4)

    @field_validator("bbox")
    @classmethod
    def validate_bbox_range(cls, v: List[float]) -> List[float]:
        for val in v:
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"Bounding box values must be in [0, 1], got {val}")
        return v


class Provenance(BsieBaseModel):
    """Provenance information for extracted data."""

    page: int = Field(..., ge=1)
    bbox: List[float] = Field(..., min_length=4, max_length=4)
    source_pdf: str
    extraction_method: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator("bbox")
    @classmethod
    def validate_bbox_range(cls, v: List[float]) -> List[float]:
        for val in v:
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"Bounding box values must be in [0, 1], got {val}")
        return v
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_base.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/ tests/schemas/
git commit -m "feat: add base schema classes with bounding box and provenance"
```

---

### Task 2.2: Implement IngestReceipt Schema

**Files:**
- Create: `src/bsie/schemas/ingest.py`
- Test: `tests/schemas/test_ingest.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_ingest.py
"""Ingest receipt schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.ingest import IngestReceipt


def test_ingest_receipt_valid():
    receipt = IngestReceipt(
        statement_id="stmt_abc123",
        sha256="a" * 64,
        pages=5,
        stored=True,
        original_path="/uploads/test.pdf",
        uploaded_at=datetime.now(timezone.utc),
    )
    assert receipt.statement_id == "stmt_abc123"
    assert receipt.pages == 5


def test_ingest_receipt_sha256_pattern():
    # Invalid SHA256 (wrong length)
    with pytest.raises(ValidationError):
        IngestReceipt(
            statement_id="stmt_abc123",
            sha256="abc",  # Too short
            pages=5,
            stored=True,
            original_path="/uploads/test.pdf",
            uploaded_at=datetime.now(timezone.utc),
        )


def test_ingest_receipt_pages_minimum():
    with pytest.raises(ValidationError):
        IngestReceipt(
            statement_id="stmt_abc123",
            sha256="a" * 64,
            pages=0,  # Must be >= 1
            stored=True,
            original_path="/uploads/test.pdf",
            uploaded_at=datetime.now(timezone.utc),
        )


def test_ingest_receipt_optional_fields():
    receipt = IngestReceipt(
        statement_id="stmt_abc123",
        sha256="a" * 64,
        pages=3,
        stored=True,
        original_path="/uploads/test.pdf",
        uploaded_at=datetime.now(timezone.utc),
        file_size_bytes=1024,
        has_text_layer=True,
        original_filename="statement.pdf",
        uploaded_by="user_123",
    )
    assert receipt.file_size_bytes == 1024
    assert receipt.has_text_layer is True


def test_ingest_receipt_mime_type_must_be_pdf():
    with pytest.raises(ValidationError):
        IngestReceipt(
            statement_id="stmt_abc123",
            sha256="a" * 64,
            pages=3,
            stored=True,
            original_path="/uploads/test.pdf",
            uploaded_at=datetime.now(timezone.utc),
            mime_type="text/plain",  # Must be application/pdf
        )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_ingest.py -v`

Expected: FAIL with "cannot import name 'IngestReceipt'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/ingest.py
"""Ingest receipt schema."""
from typing import Optional, Literal
from datetime import datetime

from pydantic import Field, field_validator

from bsie.schemas.base import BsieBaseModel


class IngestReceipt(BsieBaseModel):
    """Schema for ingest_receipt.json artifact."""

    statement_id: str
    sha256: str = Field(..., min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    pages: int = Field(..., ge=1)
    stored: bool
    original_path: str
    uploaded_at: datetime

    # Optional fields
    file_size_bytes: Optional[int] = Field(None, ge=1)
    has_text_layer: Optional[bool] = None
    original_filename: Optional[str] = None
    mime_type: Optional[Literal["application/pdf"]] = None
    uploaded_by: Optional[str] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_ingest.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/ingest.py tests/schemas/test_ingest.py
git commit -m "feat: add IngestReceipt schema"
```

---

### Task 2.3: Implement Classification Schema

**Files:**
- Create: `src/bsie/schemas/classification.py`
- Test: `tests/schemas/test_classification.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_classification.py
"""Classification schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.classification import (
    Classification,
    CandidateTemplate,
    StatementType,
    Segment,
)


def test_classification_valid():
    classification = Classification(
        statement_id="stmt_abc123",
        bank_family="chase",
        statement_type=StatementType.CHECKING,
        segment=Segment.PERSONAL,
        layout_fingerprint="HML-HHM-LLM-abc123",
        confidence=0.95,
        candidate_templates=[],
        classified_at=datetime.now(timezone.utc),
    )
    assert classification.bank_family == "chase"


def test_candidate_template():
    candidate = CandidateTemplate(
        template_id="chase_checking_v1",
        version="1.0.0",
        score=0.92,
        factors={"bank_match": 1.0, "layout_match": 0.85},
    )
    assert candidate.score == 0.92


def test_classification_with_candidates():
    classification = Classification(
        statement_id="stmt_abc123",
        bank_family="chase",
        statement_type=StatementType.CHECKING,
        segment=Segment.PERSONAL,
        layout_fingerprint="HML-HHM-LLM-abc123",
        confidence=0.95,
        candidate_templates=[
            CandidateTemplate(
                template_id="chase_checking_v1",
                version="1.0.0",
                score=0.92,
            ),
            CandidateTemplate(
                template_id="chase_checking_v2",
                version="2.0.0",
                score=0.88,
            ),
        ],
        classified_at=datetime.now(timezone.utc),
    )
    assert len(classification.candidate_templates) == 2


def test_confidence_range():
    with pytest.raises(ValidationError):
        Classification(
            statement_id="stmt_abc123",
            bank_family="chase",
            statement_type=StatementType.CHECKING,
            segment=Segment.PERSONAL,
            layout_fingerprint="test",
            confidence=1.5,  # Out of range
            candidate_templates=[],
            classified_at=datetime.now(timezone.utc),
        )


def test_statement_type_enum():
    assert StatementType.CHECKING == "checking"
    assert StatementType.SAVINGS == "savings"
    assert StatementType.CREDIT_CARD == "credit_card"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_classification.py -v`

Expected: FAIL with "cannot import name 'Classification'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/classification.py
"""Classification schema."""
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class StatementType(str, Enum):
    """Statement type enumeration."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"


class Segment(str, Enum):
    """Customer segment enumeration."""
    PERSONAL = "personal"
    BUSINESS = "business"
    UNKNOWN = "unknown"


class CandidateTemplate(BsieBaseModel):
    """Candidate template match."""

    template_id: str
    version: str
    score: float = Field(..., ge=0.0, le=1.0)
    factors: Optional[Dict[str, float]] = None


class Classification(BsieBaseModel):
    """Schema for classification.json artifact."""

    statement_id: str
    bank_family: str
    statement_type: StatementType
    segment: Segment
    layout_fingerprint: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    candidate_templates: List[CandidateTemplate]
    classified_at: datetime

    # Optional confidence breakdowns
    bank_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    type_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    segment_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    classifier_version: Optional[str] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_classification.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/classification.py tests/schemas/test_classification.py
git commit -m "feat: add Classification schema"
```

---

### Task 2.4: Implement RouteDecision Schema

**Files:**
- Create: `src/bsie/schemas/routing.py`
- Test: `tests/schemas/test_routing.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_routing.py
"""Route decision schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.routing import RouteDecision, SelectedTemplate, RouteDecisionType


def test_route_decision_template_selected():
    decision = RouteDecision(
        statement_id="stmt_abc123",
        decision=RouteDecisionType.TEMPLATE_SELECTED,
        selected_template=SelectedTemplate(
            template_id="chase_checking_v1",
            version="1.0.0",
            score=0.95,
        ),
        selection_reason="Score 0.95 >= threshold 0.80",
        decided_at=datetime.now(timezone.utc),
    )
    assert decision.decision == RouteDecisionType.TEMPLATE_SELECTED
    assert decision.selected_template is not None


def test_route_decision_template_missing():
    decision = RouteDecision(
        statement_id="stmt_abc123",
        decision=RouteDecisionType.TEMPLATE_MISSING,
        selection_reason="No candidate templates found",
        decided_at=datetime.now(timezone.utc),
    )
    assert decision.decision == RouteDecisionType.TEMPLATE_MISSING
    assert decision.selected_template is None


def test_route_decision_with_alternatives():
    decision = RouteDecision(
        statement_id="stmt_abc123",
        decision=RouteDecisionType.TEMPLATE_MISSING,
        selection_reason="Top score 0.65 < threshold 0.80",
        alternatives_considered=[
            {"template_id": "chase_v1", "score": 0.65, "rejection_reason": "Below threshold"},
        ],
        confidence_threshold_used=0.80,
        decided_at=datetime.now(timezone.utc),
    )
    assert len(decision.alternatives_considered) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_routing.py -v`

Expected: FAIL with "cannot import name 'RouteDecision'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/routing.py
"""Route decision schema."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class RouteDecisionType(str, Enum):
    """Route decision type."""
    TEMPLATE_SELECTED = "template_selected"
    TEMPLATE_MISSING = "template_missing"


class SelectedTemplate(BsieBaseModel):
    """Selected template details."""

    template_id: str
    version: str
    score: float = Field(..., ge=0.0, le=1.0)


class RouteDecision(BsieBaseModel):
    """Schema for route_decision.json artifact."""

    statement_id: str
    decision: RouteDecisionType
    decided_at: datetime

    # Template selection details
    selected_template: Optional[SelectedTemplate] = None
    selection_reason: Optional[str] = None

    # Alternative consideration
    alternatives_considered: Optional[List[Dict[str, Any]]] = None
    confidence_threshold_used: Optional[float] = Field(None, ge=0.0, le=1.0)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_routing.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/routing.py tests/schemas/test_routing.py
git commit -m "feat: add RouteDecision schema"
```

---

### Task 2.5: Implement Transaction and Transactions Schema

**Files:**
- Create: `src/bsie/schemas/transactions.py`
- Test: `tests/schemas/test_transactions.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_transactions.py
"""Transaction schema tests."""
import pytest
from datetime import date, datetime, timezone
from pydantic import ValidationError

from bsie.schemas.transactions import Transaction, Transactions, TransactionType
from bsie.schemas.base import Provenance


def test_transaction_valid():
    tx = Transaction(
        row_id="row_001",
        posted_date=date(2024, 1, 15),
        description="AMAZON PURCHASE",
        amount=-45.99,
        provenance=Provenance(
            page=1,
            bbox=[0.1, 0.2, 0.9, 0.25],
            source_pdf="stmt_abc123",
        ),
    )
    assert tx.amount == -45.99


def test_transaction_with_all_fields():
    tx = Transaction(
        row_id="row_001",
        row_index=0,
        posted_date=date(2024, 1, 15),
        effective_date=date(2024, 1, 14),
        description="CHECK #1234",
        amount=-500.00,
        balance=1500.00,
        check_number="1234",
        reference_number="REF123",
        transaction_type=TransactionType.DEBIT,
        provenance=Provenance(
            page=1,
            bbox=[0.1, 0.2, 0.9, 0.25],
            source_pdf="stmt_abc123",
        ),
    )
    assert tx.check_number == "1234"
    assert tx.transaction_type == TransactionType.DEBIT


def test_transactions_container():
    txs = Transactions(
        statement_id="stmt_abc123",
        template_id="chase_checking_v1",
        transactions=[
            Transaction(
                row_id="row_001",
                posted_date=date(2024, 1, 15),
                description="DEPOSIT",
                amount=1000.00,
                provenance=Provenance(
                    page=1,
                    bbox=[0.1, 0.2, 0.9, 0.25],
                    source_pdf="stmt_abc123",
                ),
            ),
            Transaction(
                row_id="row_002",
                posted_date=date(2024, 1, 16),
                description="WITHDRAWAL",
                amount=-200.00,
                provenance=Provenance(
                    page=1,
                    bbox=[0.1, 0.25, 0.9, 0.30],
                    source_pdf="stmt_abc123",
                ),
            ),
        ],
        extracted_at=datetime.now(timezone.utc),
    )
    assert len(txs.transactions) == 2


def test_transaction_requires_provenance():
    with pytest.raises(ValidationError):
        Transaction(
            row_id="row_001",
            posted_date=date(2024, 1, 15),
            description="TEST",
            amount=100.00,
            # Missing provenance
        )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_transactions.py -v`

Expected: FAIL with "cannot import name 'Transaction'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/transactions.py
"""Transaction schemas."""
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel, Provenance


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    DEBIT = "debit"
    CREDIT = "credit"
    UNKNOWN = "unknown"


class RawData(BsieBaseModel):
    """Raw extraction data for debugging."""
    raw_row_text: Optional[str] = None
    raw_columns: Optional[List[str]] = None


class Transaction(BsieBaseModel):
    """Single transaction record."""

    row_id: str
    posted_date: date
    description: str
    amount: float
    provenance: Provenance

    # Optional fields
    row_index: Optional[int] = None
    effective_date: Optional[date] = None
    balance: Optional[float] = None
    check_number: Optional[str] = None
    reference_number: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    category: Optional[str] = None
    raw: Optional[RawData] = None


class TransactionSummary(BsieBaseModel):
    """Summary statistics for transactions."""
    total_transactions: Optional[int] = None
    total_debits: Optional[float] = None
    total_credits: Optional[float] = None
    date_range: Optional[Dict[str, date]] = None


class Transactions(BsieBaseModel):
    """Schema for transactions.json artifact."""

    statement_id: str
    template_id: str
    transactions: List[Transaction]
    extracted_at: datetime

    # Optional fields
    template_version: Optional[str] = None
    summary: Optional[TransactionSummary] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_transactions.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/transactions.py tests/schemas/test_transactions.py
git commit -m "feat: add Transaction and Transactions schemas"
```

---

### Task 2.6: Implement Reconciliation Schema

**Files:**
- Create: `src/bsie/schemas/reconciliation.py`
- Test: `tests/schemas/test_reconciliation.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_reconciliation.py
"""Reconciliation schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.reconciliation import (
    Reconciliation,
    ReconciliationStatus,
    ReconciliationType,
    RunningBalanceCheck,
)


def test_reconciliation_pass():
    recon = Reconciliation(
        statement_id="stmt_abc123",
        status=ReconciliationStatus.PASS,
        reconciled_at=datetime.now(timezone.utc),
        beginning_balance=1000.00,
        ending_balance=1500.00,
        calculated_ending_balance=1500.00,
        total_debits=-500.00,
        total_credits=1000.00,
        transaction_count=10,
        delta_cents=0,
        tolerance_cents=2,
        within_tolerance=True,
    )
    assert recon.status == ReconciliationStatus.PASS
    assert recon.within_tolerance is True


def test_reconciliation_fail():
    recon = Reconciliation(
        statement_id="stmt_abc123",
        status=ReconciliationStatus.FAIL,
        reconciled_at=datetime.now(timezone.utc),
        beginning_balance=1000.00,
        ending_balance=1500.00,
        calculated_ending_balance=1495.00,
        delta_cents=500,  # $5.00 off
        tolerance_cents=2,
        within_tolerance=False,
    )
    assert recon.status == ReconciliationStatus.FAIL


def test_reconciliation_with_running_balance():
    recon = Reconciliation(
        statement_id="stmt_abc123",
        status=ReconciliationStatus.WARNING,
        reconciled_at=datetime.now(timezone.utc),
        running_balance_check=RunningBalanceCheck(
            performed=True,
            passed=False,
            discontinuities=[
                {"row_id": "row_005", "expected": 1200.00, "actual": 1195.00},
            ],
        ),
    )
    assert recon.running_balance_check.passed is False


def test_reconciliation_status_enum():
    assert ReconciliationStatus.PASS == "pass"
    assert ReconciliationStatus.FAIL == "fail"
    assert ReconciliationStatus.WARNING == "warning"
    assert ReconciliationStatus.OVERRIDDEN == "overridden"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_reconciliation.py -v`

Expected: FAIL with "cannot import name 'Reconciliation'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/reconciliation.py
"""Reconciliation schema."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class ReconciliationStatus(str, Enum):
    """Reconciliation status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    OVERRIDDEN = "overridden"


class ReconciliationType(str, Enum):
    """Type of reconciliation."""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"


class BalanceDiscontinuity(BsieBaseModel):
    """Running balance discontinuity."""
    row_id: str
    expected: float
    actual: float


class RunningBalanceCheck(BsieBaseModel):
    """Running balance check results."""
    performed: bool
    passed: Optional[bool] = None
    discontinuities: Optional[List[Dict[str, Any]]] = None


class ReconciliationOverride(BsieBaseModel):
    """Manual override details."""
    overridden: bool
    reason: Optional[str] = None
    overridden_by: Optional[str] = None
    overridden_at: Optional[datetime] = None


class Reconciliation(BsieBaseModel):
    """Schema for reconciliation.json artifact."""

    statement_id: str
    status: ReconciliationStatus
    reconciled_at: datetime

    # Balance details
    reconciliation_type: Optional[ReconciliationType] = None
    beginning_balance: Optional[float] = None
    ending_balance: Optional[float] = None
    calculated_ending_balance: Optional[float] = None
    total_debits: Optional[float] = None
    total_credits: Optional[float] = None
    transaction_count: Optional[int] = None

    # Delta tracking
    delta_cents: Optional[int] = None
    tolerance_cents: Optional[int] = None
    within_tolerance: Optional[bool] = None

    # Running balance verification
    running_balance_check: Optional[RunningBalanceCheck] = None

    # Override
    override: Optional[ReconciliationOverride] = None

    # Notes
    notes: Optional[str] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_reconciliation.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/reconciliation.py tests/schemas/test_reconciliation.py
git commit -m "feat: add Reconciliation schema"
```

---

### Task 2.7: Implement ExtractionResult Schema

**Files:**
- Create: `src/bsie/schemas/extraction.py`
- Test: `tests/schemas/test_extraction.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_extraction.py
"""Extraction result schema tests."""
import pytest
from datetime import datetime, timezone

from bsie.schemas.extraction import (
    ExtractionResult,
    ExtractionStatus,
    ExtractionMethod,
    MethodAttempt,
    ExtractedBalances,
)


def test_extraction_result_complete():
    result = ExtractionResult(
        statement_id="stmt_abc123",
        template_id="chase_checking_v1",
        status=ExtractionStatus.COMPLETE,
        extracted_at=datetime.now(timezone.utc),
        method_used=ExtractionMethod.CAMELOT_STREAM,
        pages_processed=[1, 2, 3],
        tables_found=2,
        rows_extracted=45,
    )
    assert result.status == ExtractionStatus.COMPLETE
    assert result.rows_extracted == 45


def test_extraction_result_with_balances():
    result = ExtractionResult(
        statement_id="stmt_abc123",
        template_id="chase_checking_v1",
        status=ExtractionStatus.COMPLETE,
        extracted_at=datetime.now(timezone.utc),
        balances=ExtractedBalances(
            beginning_balance=1000.00,
            ending_balance=1500.00,
            beginning_balance_found=True,
            ending_balance_found=True,
        ),
    )
    assert result.balances.beginning_balance == 1000.00


def test_extraction_result_with_method_attempts():
    result = ExtractionResult(
        statement_id="stmt_abc123",
        template_id="chase_checking_v1",
        status=ExtractionStatus.COMPLETE,
        extracted_at=datetime.now(timezone.utc),
        method_used=ExtractionMethod.CAMELOT_STREAM,
        methods_attempted=[
            MethodAttempt(
                method="camelot_lattice",
                success=False,
                rows_extracted=0,
                error="No tables found with lattice detection",
            ),
            MethodAttempt(
                method="camelot_stream",
                success=True,
                rows_extracted=45,
            ),
        ],
    )
    assert len(result.methods_attempted) == 2


def test_extraction_status_enum():
    assert ExtractionStatus.COMPLETE == "complete"
    assert ExtractionStatus.PARTIAL == "partial"
    assert ExtractionStatus.FAILED == "failed"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_extraction.py -v`

Expected: FAIL with "cannot import name 'ExtractionResult'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/extraction.py
"""Extraction result schema."""
from typing import Optional, List
from datetime import datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class ExtractionStatus(str, Enum):
    """Extraction status."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class ExtractionMethod(str, Enum):
    """Extraction method used."""
    CAMELOT_LATTICE = "camelot_lattice"
    CAMELOT_STREAM = "camelot_stream"
    TABULA_STREAM = "tabula_stream"
    PDFPLUMBER_COLUMNS = "pdfplumber_columns"


class MethodAttempt(BsieBaseModel):
    """Record of an extraction method attempt."""
    method: str
    success: bool
    rows_extracted: Optional[int] = None
    error: Optional[str] = None


class RowIssue(BsieBaseModel):
    """Issue with a specific row."""
    row_index: int
    issue: str
    severity: Optional[str] = None


class ExtractedBalances(BsieBaseModel):
    """Extracted balance information."""
    beginning_balance: Optional[float] = None
    ending_balance: Optional[float] = None
    beginning_balance_found: Optional[bool] = None
    ending_balance_found: Optional[bool] = None


class ExtractionResult(BsieBaseModel):
    """Schema for extraction_result.json artifact."""

    statement_id: str
    template_id: str
    status: ExtractionStatus
    extracted_at: datetime

    # Method details
    template_version: Optional[str] = None
    method_used: Optional[ExtractionMethod] = None
    methods_attempted: Optional[List[MethodAttempt]] = None

    # Results
    pages_processed: Optional[List[int]] = None
    tables_found: Optional[int] = None
    rows_extracted: Optional[int] = None
    rows_with_issues: Optional[List[RowIssue]] = None

    # Balances
    balances: Optional[ExtractedBalances] = None

    # Metadata
    warnings: Optional[List[str]] = None
    processing_time_ms: Optional[int] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_extraction.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/extraction.py tests/schemas/test_extraction.py
git commit -m "feat: add ExtractionResult schema"
```

---

### Task 2.8: Implement PipelineState Schema

**Files:**
- Create: `src/bsie/schemas/pipeline_state.py`
- Test: `tests/schemas/test_pipeline_state.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_pipeline_state.py
"""Pipeline state schema tests."""
import pytest
from datetime import datetime, timezone

from bsie.schemas.pipeline_state import (
    PipelineState,
    PipelineStateEnum,
    StateHistoryEntry,
    TemplateBinding,
)


def test_pipeline_state_valid():
    state = PipelineState(
        statement_id="stmt_abc123",
        current_state=PipelineStateEnum.UPLOADED,
        state_history=[
            StateHistoryEntry(
                state="UPLOADED",
                entered_at=datetime.now(timezone.utc),
            ),
        ],
        updated_at=datetime.now(timezone.utc),
    )
    assert state.current_state == PipelineStateEnum.UPLOADED


def test_pipeline_state_all_states():
    """Verify all MVP states are defined."""
    states = [
        PipelineStateEnum.UPLOADED,
        PipelineStateEnum.INGESTED,
        PipelineStateEnum.CLASSIFIED,
        PipelineStateEnum.ROUTED,
        PipelineStateEnum.TEMPLATE_SELECTED,
        PipelineStateEnum.TEMPLATE_MISSING,
        PipelineStateEnum.EXTRACTION_READY,
        PipelineStateEnum.EXTRACTING,
        PipelineStateEnum.EXTRACTION_FAILED,
        PipelineStateEnum.RECONCILING,
        PipelineStateEnum.RECONCILIATION_FAILED,
        PipelineStateEnum.HUMAN_REVIEW_REQUIRED,
        PipelineStateEnum.COMPLETED,
    ]
    assert len(states) == 13


def test_pipeline_state_with_template_binding():
    state = PipelineState(
        statement_id="stmt_abc123",
        current_state=PipelineStateEnum.TEMPLATE_SELECTED,
        state_history=[],
        updated_at=datetime.now(timezone.utc),
        template_binding=TemplateBinding(
            template_id="chase_checking_v1",
            template_version="1.0.0",
            bound_at=datetime.now(timezone.utc),
        ),
    )
    assert state.template_binding.template_id == "chase_checking_v1"


def test_state_history_entry():
    entry = StateHistoryEntry(
        state="INGESTED",
        entered_at=datetime.now(timezone.utc),
        exited_at=datetime.now(timezone.utc),
        duration_ms=1500,
        trigger="ingestion_complete",
        metadata={"worker_id": "worker_01"},
    )
    assert entry.duration_ms == 1500
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_pipeline_state.py -v`

Expected: FAIL with "cannot import name 'PipelineState'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/pipeline_state.py
"""Pipeline state schema."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from bsie.schemas.base import BsieBaseModel


class PipelineStateEnum(str, Enum):
    """All valid pipeline states."""
    # Phase 1 MVP states
    UPLOADED = "UPLOADED"
    INGESTED = "INGESTED"
    CLASSIFIED = "CLASSIFIED"
    ROUTED = "ROUTED"
    TEMPLATE_SELECTED = "TEMPLATE_SELECTED"
    TEMPLATE_MISSING = "TEMPLATE_MISSING"
    EXTRACTION_READY = "EXTRACTION_READY"
    EXTRACTING = "EXTRACTING"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    RECONCILING = "RECONCILING"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"

    # Phase 2+ states
    TEMPLATE_DRAFTING = "TEMPLATE_DRAFTING"
    TEMPLATE_DRAFTED = "TEMPLATE_DRAFTED"
    TEMPLATE_REVIEW = "TEMPLATE_REVIEW"
    TEMPLATE_REVIEW_FAILED = "TEMPLATE_REVIEW_FAILED"
    TEMPLATE_APPROVED = "TEMPLATE_APPROVED"


class StateHistoryEntry(BsieBaseModel):
    """Single state history entry."""
    state: str
    entered_at: datetime
    exited_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    trigger: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TemplateBinding(BsieBaseModel):
    """Template binding information."""
    template_id: str
    template_version: str
    bound_at: datetime


class ErrorInfo(BsieBaseModel):
    """Error information."""
    code: str
    message: str
    occurred_at: datetime


class PipelineState(BsieBaseModel):
    """Schema for pipeline_state.json artifact."""

    statement_id: str
    current_state: PipelineStateEnum
    state_history: List[StateHistoryEntry]
    updated_at: datetime

    # Artifacts
    artifacts: Optional[Dict[str, str]] = None

    # Template binding
    template_binding: Optional[TemplateBinding] = None

    # Error info
    error: Optional[ErrorInfo] = None

    # Retry tracking
    retry_count: int = 0

    # Timestamps
    created_at: Optional[datetime] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_pipeline_state.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/pipeline_state.py tests/schemas/test_pipeline_state.py
git commit -m "feat: add PipelineState schema with all MVP states"
```

---

### Task 2.9: Implement ExtractionError Schema

**Files:**
- Create: `src/bsie/schemas/errors.py`
- Test: `tests/schemas/test_errors.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_errors.py
"""Error schema tests."""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from bsie.schemas.errors import ExtractionError, ErrorCategory


def test_extraction_error_valid():
    error = ExtractionError(
        statement_id="stmt_abc123",
        error_code="E3001",
        error_category=ErrorCategory.EXTRACTION,
        message="No tables found in PDF",
        occurred_at=datetime.now(timezone.utc),
    )
    assert error.error_code == "E3001"


def test_error_code_pattern():
    # Valid pattern
    error = ExtractionError(
        statement_id="stmt_abc123",
        error_code="E1234",
        error_category=ErrorCategory.VALIDATION,
        message="Test error",
        occurred_at=datetime.now(timezone.utc),
    )
    assert error.error_code == "E1234"

    # Invalid pattern
    with pytest.raises(ValidationError):
        ExtractionError(
            statement_id="stmt_abc123",
            error_code="INVALID",
            error_category=ErrorCategory.VALIDATION,
            message="Test error",
            occurred_at=datetime.now(timezone.utc),
        )


def test_extraction_error_with_details():
    error = ExtractionError(
        statement_id="stmt_abc123",
        error_code="E3002",
        error_category=ErrorCategory.EXTRACTION,
        message="Partial extraction - missing columns",
        occurred_at=datetime.now(timezone.utc),
        template_id="chase_checking_v1",
        method_attempted="camelot_stream",
        page=2,
        recoverable=True,
        suggested_actions=["Try different extraction method", "Check template configuration"],
        details={"missing_columns": ["balance", "date"]},
    )
    assert error.recoverable is True
    assert len(error.suggested_actions) == 2


def test_error_category_enum():
    assert ErrorCategory.VALIDATION == "VALIDATION"
    assert ErrorCategory.TRANSIENT == "TRANSIENT"
    assert ErrorCategory.EXTRACTION == "EXTRACTION"
    assert ErrorCategory.RECONCILIATION == "RECONCILIATION"
    assert ErrorCategory.CONFIGURATION == "CONFIGURATION"
    assert ErrorCategory.SYSTEM == "SYSTEM"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_errors.py -v`

Expected: FAIL with "cannot import name 'ExtractionError'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/errors.py
"""Error schemas."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import Field

from bsie.schemas.base import BsieBaseModel


class ErrorCategory(str, Enum):
    """Error category for classification."""
    VALIDATION = "VALIDATION"
    TRANSIENT = "TRANSIENT"
    EXTRACTION = "EXTRACTION"
    RECONCILIATION = "RECONCILIATION"
    CONFIGURATION = "CONFIGURATION"
    SYSTEM = "SYSTEM"


class ExtractionError(BsieBaseModel):
    """Schema for extraction_error.json artifact."""

    statement_id: str
    error_code: str = Field(..., pattern=r"^E[0-9]{4}$")
    error_category: ErrorCategory
    message: str
    occurred_at: datetime

    # Context
    template_id: Optional[str] = None
    method_attempted: Optional[str] = None
    page: Optional[int] = None

    # Recovery
    recoverable: Optional[bool] = None
    suggested_actions: Optional[List[str]] = None

    # Additional details
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_errors.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/errors.py tests/schemas/test_errors.py
git commit -m "feat: add ExtractionError schema"
```

---

### Task 2.10: Implement HumanReviewDecision and CorrectionOverlay Schemas

**Files:**
- Create: `src/bsie/schemas/human_review.py`
- Test: `tests/schemas/test_human_review.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_human_review.py
"""Human review schema tests."""
import pytest
from datetime import datetime, timezone

from bsie.schemas.human_review import (
    HumanReviewDecision,
    ReviewDecisionType,
    CorrectionOverlay,
    TransactionCorrection,
    CorrectionType,
)


def test_human_review_approve():
    decision = HumanReviewDecision(
        statement_id="stmt_abc123",
        decision=ReviewDecisionType.APPROVE,
        reviewer_id="user_123",
        decided_at=datetime.now(timezone.utc),
    )
    assert decision.decision == ReviewDecisionType.APPROVE


def test_human_review_approve_with_corrections():
    decision = HumanReviewDecision(
        statement_id="stmt_abc123",
        decision=ReviewDecisionType.APPROVE_WITH_CORRECTIONS,
        reviewer_id="user_123",
        decided_at=datetime.now(timezone.utc),
        correction_overlay_id="corr_xyz789",
        notes="Fixed date on row 5",
    )
    assert decision.correction_overlay_id == "corr_xyz789"


def test_human_review_reject():
    decision = HumanReviewDecision(
        statement_id="stmt_abc123",
        decision=ReviewDecisionType.REJECT,
        reviewer_id="user_123",
        decided_at=datetime.now(timezone.utc),
        rejection_reason="PDF is corrupted, transactions unreadable",
    )
    assert decision.rejection_reason is not None


def test_correction_overlay():
    overlay = CorrectionOverlay(
        statement_id="stmt_abc123",
        overlay_id="corr_xyz789",
        reviewer_id="user_123",
        corrections=[
            TransactionCorrection(
                row_id="row_005",
                correction_type=CorrectionType.EDIT,
                field="amount",
                original_value="-100.00",
                corrected_value="-1000.00",
                reason="OCR misread amount",
            ),
        ],
        created_at=datetime.now(timezone.utc),
    )
    assert len(overlay.corrections) == 1
    assert overlay.corrections[0].corrected_value == "-1000.00"


def test_correction_types():
    assert CorrectionType.EDIT == "edit"
    assert CorrectionType.ADD == "add"
    assert CorrectionType.DELETE == "delete"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_human_review.py -v`

Expected: FAIL with "cannot import name 'HumanReviewDecision'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/human_review.py
"""Human review schemas."""
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

from bsie.schemas.base import BsieBaseModel


class ReviewDecisionType(str, Enum):
    """Human review decision types."""
    APPROVE = "approve"
    APPROVE_WITH_CORRECTIONS = "approve_with_corrections"
    REQUEST_REPROCESSING = "request_reprocessing"
    REJECT = "reject"


class CorrectionType(str, Enum):
    """Type of correction."""
    EDIT = "edit"
    ADD = "add"
    DELETE = "delete"


class TransactionCorrection(BsieBaseModel):
    """Single transaction correction."""
    row_id: str
    correction_type: CorrectionType
    field: Optional[str] = None
    original_value: Optional[Any] = None
    corrected_value: Optional[Any] = None
    reason: Optional[str] = None


class CorrectionOverlay(BsieBaseModel):
    """Schema for correction_overlay.json artifact."""

    statement_id: str
    overlay_id: str
    reviewer_id: str
    corrections: List[TransactionCorrection]
    created_at: datetime

    # Metadata
    notes: Optional[str] = None


class HumanReviewDecision(BsieBaseModel):
    """Schema for human_review_decision.json artifact."""

    statement_id: str
    decision: ReviewDecisionType
    reviewer_id: str
    decided_at: datetime

    # For approve_with_corrections
    correction_overlay_id: Optional[str] = None

    # For request_reprocessing
    reprocessing_hints: Optional[str] = None

    # For reject
    rejection_reason: Optional[str] = None

    # Notes
    notes: Optional[str] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_human_review.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/human_review.py tests/schemas/test_human_review.py
git commit -m "feat: add HumanReviewDecision and CorrectionOverlay schemas"
```

---

### Task 2.11: Implement FinalTransactions Schema

**Files:**
- Create: `src/bsie/schemas/final_transactions.py`
- Test: `tests/schemas/test_final_transactions.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_final_transactions.py
"""Final transactions schema tests."""
import pytest
from datetime import date, datetime, timezone

from bsie.schemas.final_transactions import (
    FinalTransactions,
    FinalTransaction,
    FinalTransactionSource,
    CorrectionSource,
)
from bsie.schemas.base import Provenance


def test_final_transaction_from_original():
    tx = FinalTransaction(
        row_id="row_001",
        posted_date=date(2024, 1, 15),
        description="DEPOSIT",
        amount=1000.00,
        provenance=Provenance(
            page=1,
            bbox=[0.1, 0.2, 0.9, 0.25],
            source_pdf="stmt_abc123",
        ),
        correction_source=CorrectionSource.ORIGINAL,
    )
    assert tx.correction_source == CorrectionSource.ORIGINAL


def test_final_transaction_edited():
    tx = FinalTransaction(
        row_id="row_002",
        posted_date=date(2024, 1, 16),
        description="CORRECTED DESCRIPTION",
        amount=500.00,
        provenance=Provenance(
            page=1,
            bbox=[0.1, 0.3, 0.9, 0.35],
            source_pdf="stmt_abc123",
        ),
        correction_source=CorrectionSource.EDITED,
    )
    assert tx.correction_source == CorrectionSource.EDITED


def test_final_transactions_container():
    final = FinalTransactions(
        statement_id="stmt_abc123",
        transactions=[
            FinalTransaction(
                row_id="row_001",
                posted_date=date(2024, 1, 15),
                description="TEST",
                amount=100.00,
                provenance=Provenance(
                    page=1,
                    bbox=[0.1, 0.2, 0.9, 0.25],
                    source_pdf="stmt_abc123",
                ),
            ),
        ],
        source=FinalTransactionSource(
            raw_transactions_id="txn_abc123",
            correction_overlay_id=None,
            corrections_applied=0,
        ),
        finalized_at=datetime.now(timezone.utc),
    )
    assert final.source.corrections_applied == 0


def test_final_transactions_with_corrections():
    final = FinalTransactions(
        statement_id="stmt_abc123",
        transactions=[],
        source=FinalTransactionSource(
            raw_transactions_id="txn_abc123",
            correction_overlay_id="corr_xyz789",
            corrections_applied=3,
        ),
        finalized_at=datetime.now(timezone.utc),
    )
    assert final.source.correction_overlay_id == "corr_xyz789"
    assert final.source.corrections_applied == 3
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_final_transactions.py -v`

Expected: FAIL with "cannot import name 'FinalTransactions'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/final_transactions.py
"""Final transactions schema."""
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

from bsie.schemas.base import BsieBaseModel, Provenance


class CorrectionSource(str, Enum):
    """Source of the transaction data."""
    ORIGINAL = "original"
    EDITED = "edited"
    ADDED = "added"
    MERGED = "merged"


class FinalTransaction(BsieBaseModel):
    """Single final transaction."""
    row_id: str
    posted_date: date
    description: str
    amount: float
    provenance: Provenance

    # Optional fields
    balance: Optional[float] = None
    correction_source: Optional[CorrectionSource] = None


class FinalTransactionSource(BsieBaseModel):
    """Source information for final transactions."""
    raw_transactions_id: str
    correction_overlay_id: Optional[str] = None
    corrections_applied: int = 0


class FinalTransactionSummary(BsieBaseModel):
    """Summary of final transactions."""
    total_transactions: Optional[int] = None
    total_debits: Optional[float] = None
    total_credits: Optional[float] = None
    net_change: Optional[float] = None


class FinalTransactions(BsieBaseModel):
    """Schema for final_transactions.json artifact."""

    statement_id: str
    transactions: List[FinalTransaction]
    source: FinalTransactionSource
    finalized_at: datetime

    # Optional summary
    summary: Optional[FinalTransactionSummary] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_final_transactions.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/final_transactions.py tests/schemas/test_final_transactions.py
git commit -m "feat: add FinalTransactions schema"
```

---

### Task 2.12: Create Schema Registry and Validation Utilities

**Files:**
- Create: `src/bsie/schemas/registry.py`
- Modify: `src/bsie/schemas/__init__.py`
- Test: `tests/schemas/test_registry.py`

**Step 1: Write the failing test**

```python
# tests/schemas/test_registry.py
"""Schema registry tests."""
import pytest
from datetime import datetime, timezone

from bsie.schemas.registry import (
    get_schema_for_artifact,
    validate_artifact,
    ArtifactType,
    ValidationError as SchemaValidationError,
)


def test_get_schema_for_ingest_receipt():
    schema = get_schema_for_artifact(ArtifactType.INGEST_RECEIPT)
    assert schema is not None


def test_get_schema_for_all_artifact_types():
    for artifact_type in ArtifactType:
        schema = get_schema_for_artifact(artifact_type)
        assert schema is not None, f"No schema for {artifact_type}"


def test_validate_artifact_valid():
    data = {
        "statement_id": "stmt_abc123",
        "sha256": "a" * 64,
        "pages": 5,
        "stored": True,
        "original_path": "/uploads/test.pdf",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    result = validate_artifact(ArtifactType.INGEST_RECEIPT, data)
    assert result.statement_id == "stmt_abc123"


def test_validate_artifact_invalid():
    data = {
        "statement_id": "stmt_abc123",
        # Missing required fields
    }
    with pytest.raises(SchemaValidationError):
        validate_artifact(ArtifactType.INGEST_RECEIPT, data)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/schemas/test_registry.py -v`

Expected: FAIL with "cannot import name 'get_schema_for_artifact'"

**Step 3: Write minimal implementation**

```python
# src/bsie/schemas/registry.py
"""Schema registry and validation utilities."""
from enum import Enum
from typing import Any, Type

from pydantic import ValidationError as PydanticValidationError

from bsie.schemas.base import BsieBaseModel
from bsie.schemas.ingest import IngestReceipt
from bsie.schemas.classification import Classification
from bsie.schemas.routing import RouteDecision
from bsie.schemas.transactions import Transactions
from bsie.schemas.extraction import ExtractionResult
from bsie.schemas.reconciliation import Reconciliation
from bsie.schemas.pipeline_state import PipelineState
from bsie.schemas.errors import ExtractionError
from bsie.schemas.human_review import HumanReviewDecision, CorrectionOverlay
from bsie.schemas.final_transactions import FinalTransactions


class ValidationError(Exception):
    """Schema validation error."""

    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


class ArtifactType(str, Enum):
    """Artifact type enumeration."""
    INGEST_RECEIPT = "ingest_receipt"
    CLASSIFICATION = "classification"
    ROUTE_DECISION = "route_decision"
    TRANSACTIONS = "transactions"
    EXTRACTION_RESULT = "extraction_result"
    RECONCILIATION = "reconciliation"
    PIPELINE_STATE = "pipeline_state"
    EXTRACTION_ERROR = "extraction_error"
    HUMAN_REVIEW_DECISION = "human_review_decision"
    CORRECTION_OVERLAY = "correction_overlay"
    FINAL_TRANSACTIONS = "final_transactions"


# Registry mapping artifact types to schema classes
_SCHEMA_REGISTRY: dict[ArtifactType, Type[BsieBaseModel]] = {
    ArtifactType.INGEST_RECEIPT: IngestReceipt,
    ArtifactType.CLASSIFICATION: Classification,
    ArtifactType.ROUTE_DECISION: RouteDecision,
    ArtifactType.TRANSACTIONS: Transactions,
    ArtifactType.EXTRACTION_RESULT: ExtractionResult,
    ArtifactType.RECONCILIATION: Reconciliation,
    ArtifactType.PIPELINE_STATE: PipelineState,
    ArtifactType.EXTRACTION_ERROR: ExtractionError,
    ArtifactType.HUMAN_REVIEW_DECISION: HumanReviewDecision,
    ArtifactType.CORRECTION_OVERLAY: CorrectionOverlay,
    ArtifactType.FINAL_TRANSACTIONS: FinalTransactions,
}


def get_schema_for_artifact(artifact_type: ArtifactType) -> Type[BsieBaseModel]:
    """Get the schema class for an artifact type."""
    return _SCHEMA_REGISTRY[artifact_type]


def validate_artifact(artifact_type: ArtifactType, data: dict[str, Any]) -> BsieBaseModel:
    """Validate artifact data against its schema.

    Args:
        artifact_type: Type of artifact to validate
        data: Dictionary of artifact data

    Returns:
        Validated Pydantic model instance

    Raises:
        ValidationError: If validation fails
    """
    schema_class = get_schema_for_artifact(artifact_type)

    try:
        return schema_class.model_validate(data)
    except PydanticValidationError as e:
        raise ValidationError(
            f"Validation failed for {artifact_type.value}",
            errors=e.errors(),
        ) from e
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/schemas/test_registry.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/schemas/registry.py tests/schemas/test_registry.py
git commit -m "feat: add schema registry with validation utilities"
```

---

### Task 2.13: Export All Schemas from Package

**Files:**
- Modify: `src/bsie/schemas/__init__.py`

**Step 1: Update package exports**

```python
# src/bsie/schemas/__init__.py
"""Pydantic schemas for BSIE artifacts."""

# Base types
from bsie.schemas.base import BsieBaseModel, BoundingBox, Provenance

# Artifact schemas
from bsie.schemas.ingest import IngestReceipt
from bsie.schemas.classification import (
    Classification,
    CandidateTemplate,
    StatementType,
    Segment,
)
from bsie.schemas.routing import RouteDecision, SelectedTemplate, RouteDecisionType
from bsie.schemas.transactions import (
    Transaction,
    Transactions,
    TransactionType,
    TransactionSummary,
)
from bsie.schemas.extraction import (
    ExtractionResult,
    ExtractionStatus,
    ExtractionMethod,
    MethodAttempt,
    ExtractedBalances,
)
from bsie.schemas.reconciliation import (
    Reconciliation,
    ReconciliationStatus,
    ReconciliationType,
    RunningBalanceCheck,
)
from bsie.schemas.pipeline_state import (
    PipelineState,
    PipelineStateEnum,
    StateHistoryEntry,
    TemplateBinding,
)
from bsie.schemas.errors import ExtractionError, ErrorCategory
from bsie.schemas.human_review import (
    HumanReviewDecision,
    ReviewDecisionType,
    CorrectionOverlay,
    TransactionCorrection,
    CorrectionType,
)
from bsie.schemas.final_transactions import (
    FinalTransactions,
    FinalTransaction,
    FinalTransactionSource,
    CorrectionSource,
)

# Registry and validation
from bsie.schemas.registry import (
    ArtifactType,
    get_schema_for_artifact,
    validate_artifact,
    ValidationError,
)

__all__ = [
    # Base
    "BsieBaseModel",
    "BoundingBox",
    "Provenance",
    # Ingest
    "IngestReceipt",
    # Classification
    "Classification",
    "CandidateTemplate",
    "StatementType",
    "Segment",
    # Routing
    "RouteDecision",
    "SelectedTemplate",
    "RouteDecisionType",
    # Transactions
    "Transaction",
    "Transactions",
    "TransactionType",
    "TransactionSummary",
    # Extraction
    "ExtractionResult",
    "ExtractionStatus",
    "ExtractionMethod",
    "MethodAttempt",
    "ExtractedBalances",
    # Reconciliation
    "Reconciliation",
    "ReconciliationStatus",
    "ReconciliationType",
    "RunningBalanceCheck",
    # Pipeline State
    "PipelineState",
    "PipelineStateEnum",
    "StateHistoryEntry",
    "TemplateBinding",
    # Errors
    "ExtractionError",
    "ErrorCategory",
    # Human Review
    "HumanReviewDecision",
    "ReviewDecisionType",
    "CorrectionOverlay",
    "TransactionCorrection",
    "CorrectionType",
    # Final Transactions
    "FinalTransactions",
    "FinalTransaction",
    "FinalTransactionSource",
    "CorrectionSource",
    # Registry
    "ArtifactType",
    "get_schema_for_artifact",
    "validate_artifact",
    "ValidationError",
]
```

**Step 2: Verify imports work**

Run: `python -c "from bsie.schemas import *; print('All imports successful')"`

Expected: "All imports successful"

**Step 3: Commit**

```bash
git add src/bsie/schemas/__init__.py
git commit -m "feat: export all schemas from package"
```

---

### Task 2.14: Run Full Schema Test Suite and Verify Sprint 2 Complete

**Step 1: Run all schema tests**

Run: `pytest tests/schemas/ -v --tb=short`

Expected: All tests PASS (~25-30 tests)

**Step 2: Run full test suite**

Run: `pytest tests/ -v --tb=short`

Expected: All tests PASS

**Step 3: Verify type checking**

Run: `mypy src/bsie/schemas/`

Expected: No errors

**Step 4: Final commit for Sprint 2**

```bash
git add -A
git commit -m "chore: sprint 2 complete - schema validation"
```

---

## Sprint 2 Complete

**Milestone Achieved:**
- All 11 artifact schemas implemented
- Pydantic v2 models with strict validation
- Schema registry with lookup by artifact type
- Validation utilities with error handling
- Comprehensive test coverage

**Next:** Sprint 3 - State Controller

---

## Sprint 3: State Controller (18 tasks)

**Goal:** Implement the centralized State Controller that owns all pipeline state transitions.

**Milestone:** Full state machine working with transition validation, artifact requirements, and audit logging.

**Reference:** `/Users/brian/dev/BSIE/pipeline_state_machine_v2.md`, `/Users/brian/dev/BSIE/decisions_v2.md`

---

### Task 3.1: Define State and Transition Constants

**Files:**
- Create: `src/bsie/state/__init__.py`
- Create: `src/bsie/state/constants.py`
- Test: `tests/state/__init__.py`
- Test: `tests/state/test_constants.py`

**Step 1: Write the failing test**

```python
# tests/state/__init__.py
"""State controller tests."""
```

```python
# tests/state/test_constants.py
"""State constants tests."""
import pytest

from bsie.state.constants import (
    State,
    TRANSITION_MATRIX,
    STATE_TIMEOUTS,
    STATE_REQUIRED_ARTIFACTS,
    get_allowed_transitions,
)


def test_all_mvp_states_defined():
    mvp_states = [
        State.UPLOADED,
        State.INGESTED,
        State.CLASSIFIED,
        State.ROUTED,
        State.TEMPLATE_SELECTED,
        State.TEMPLATE_MISSING,
        State.EXTRACTION_READY,
        State.EXTRACTING,
        State.EXTRACTION_FAILED,
        State.RECONCILING,
        State.RECONCILIATION_FAILED,
        State.HUMAN_REVIEW_REQUIRED,
        State.COMPLETED,
    ]
    assert len(mvp_states) == 13


def test_transition_matrix_uploaded():
    """UPLOADED can transition to INGESTED or HUMAN_REVIEW_REQUIRED."""
    allowed = get_allowed_transitions(State.UPLOADED)
    assert State.INGESTED in allowed
    assert State.HUMAN_REVIEW_REQUIRED in allowed
    assert State.COMPLETED not in allowed


def test_transition_matrix_routed():
    """ROUTED can transition to TEMPLATE_SELECTED or TEMPLATE_MISSING."""
    allowed = get_allowed_transitions(State.ROUTED)
    assert State.TEMPLATE_SELECTED in allowed
    assert State.TEMPLATE_MISSING in allowed


def test_completed_is_terminal():
    """COMPLETED has no outgoing transitions."""
    allowed = get_allowed_transitions(State.COMPLETED)
    assert len(allowed) == 0


def test_state_timeouts():
    assert STATE_TIMEOUTS[State.UPLOADED] == 30
    assert STATE_TIMEOUTS[State.EXTRACTING] == 120
    assert STATE_TIMEOUTS.get(State.COMPLETED) is None  # Terminal, no timeout


def test_required_artifacts_for_ingested():
    required = STATE_REQUIRED_ARTIFACTS.get(State.INGESTED, [])
    assert "ingest_receipt" in required
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_constants.py -v`

Expected: FAIL with "cannot import name 'State'"

**Step 3: Write minimal implementation**

```python
# src/bsie/state/__init__.py
"""State controller package."""
```

```python
# src/bsie/state/constants.py
"""State machine constants and transition definitions."""
from enum import Enum
from typing import Dict, List, Set, Optional


class State(str, Enum):
    """Pipeline states."""
    # Phase 1 MVP states
    UPLOADED = "UPLOADED"
    INGESTED = "INGESTED"
    CLASSIFIED = "CLASSIFIED"
    ROUTED = "ROUTED"
    TEMPLATE_SELECTED = "TEMPLATE_SELECTED"
    TEMPLATE_MISSING = "TEMPLATE_MISSING"
    EXTRACTION_READY = "EXTRACTION_READY"
    EXTRACTING = "EXTRACTING"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    RECONCILING = "RECONCILING"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"


# Valid state transitions (from_state -> set of allowed to_states)
TRANSITION_MATRIX: Dict[State, Set[State]] = {
    State.UPLOADED: {State.INGESTED, State.HUMAN_REVIEW_REQUIRED},
    State.INGESTED: {State.CLASSIFIED},
    State.CLASSIFIED: {State.ROUTED},
    State.ROUTED: {State.TEMPLATE_SELECTED, State.TEMPLATE_MISSING},
    State.TEMPLATE_SELECTED: {State.EXTRACTION_READY},
    State.TEMPLATE_MISSING: {State.HUMAN_REVIEW_REQUIRED},
    State.EXTRACTION_READY: {State.EXTRACTING},
    State.EXTRACTING: {State.RECONCILING, State.EXTRACTION_FAILED},
    State.EXTRACTION_FAILED: {State.HUMAN_REVIEW_REQUIRED},
    State.RECONCILING: {State.COMPLETED, State.RECONCILIATION_FAILED},
    State.RECONCILIATION_FAILED: {State.HUMAN_REVIEW_REQUIRED},
    State.HUMAN_REVIEW_REQUIRED: {State.COMPLETED, State.EXTRACTION_READY},
    State.COMPLETED: set(),  # Terminal state
}


# State timeouts in seconds (None = no timeout)
STATE_TIMEOUTS: Dict[State, Optional[int]] = {
    State.UPLOADED: 30,
    State.INGESTED: None,  # Stable
    State.CLASSIFIED: None,  # Stable
    State.ROUTED: 5,
    State.TEMPLATE_SELECTED: None,  # Stable
    State.TEMPLATE_MISSING: None,  # Terminal in Phase 1
    State.EXTRACTION_READY: 10,
    State.EXTRACTING: 120,
    State.EXTRACTION_FAILED: None,  # Error state
    State.RECONCILING: 10,
    State.RECONCILIATION_FAILED: None,  # Error state
    State.HUMAN_REVIEW_REQUIRED: 7 * 24 * 3600,  # 7 days
    State.COMPLETED: None,  # Terminal
}


# Required artifacts to enter each state
STATE_REQUIRED_ARTIFACTS: Dict[State, List[str]] = {
    State.INGESTED: ["ingest_receipt"],
    State.CLASSIFIED: ["classification"],
    State.ROUTED: ["route_decision"],
    State.RECONCILING: ["extraction_result", "transactions"],
    State.COMPLETED: ["reconciliation", "final_transactions"],
}


def get_allowed_transitions(from_state: State) -> Set[State]:
    """Get allowed transitions from a state."""
    return TRANSITION_MATRIX.get(from_state, set())


def is_valid_transition(from_state: State, to_state: State) -> bool:
    """Check if a transition is valid."""
    return to_state in get_allowed_transitions(from_state)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_constants.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/ tests/state/
git commit -m "feat: add state machine constants and transition matrix"
```

---

### Task 3.2: Create Transition Result Types

**Files:**
- Create: `src/bsie/state/types.py`
- Test: `tests/state/test_types.py`

**Step 1: Write the failing test**

```python
# tests/state/test_types.py
"""State types tests."""
import pytest
from datetime import datetime, timezone

from bsie.state.types import TransitionResult, TransitionError


def test_transition_result_success():
    result = TransitionResult(
        success=True,
        previous_state="UPLOADED",
        current_state="INGESTED",
        statement_id="stmt_abc123",
        timestamp=datetime.now(timezone.utc),
    )
    assert result.success is True
    assert result.error is None


def test_transition_result_failure():
    result = TransitionResult(
        success=False,
        previous_state="UPLOADED",
        current_state="UPLOADED",
        statement_id="stmt_abc123",
        timestamp=datetime.now(timezone.utc),
        error="Invalid transition: UPLOADED -> COMPLETED",
    )
    assert result.success is False
    assert result.error is not None


def test_transition_error_categories():
    assert TransitionError.INVALID_TRANSITION.value == "invalid_transition"
    assert TransitionError.MISSING_ARTIFACT.value == "missing_artifact"
    assert TransitionError.VALIDATION_FAILED.value == "validation_failed"
    assert TransitionError.CONCURRENT_MODIFICATION.value == "concurrent_modification"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_types.py -v`

Expected: FAIL with "cannot import name 'TransitionResult'"

**Step 3: Write minimal implementation**

```python
# src/bsie/state/types.py
"""State controller type definitions."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class TransitionError(str, Enum):
    """Transition error categories."""
    INVALID_TRANSITION = "invalid_transition"
    MISSING_ARTIFACT = "missing_artifact"
    VALIDATION_FAILED = "validation_failed"
    CONCURRENT_MODIFICATION = "concurrent_modification"
    STATE_NOT_FOUND = "state_not_found"
    TIMEOUT = "timeout"


@dataclass
class TransitionResult:
    """Result of a state transition attempt."""
    success: bool
    previous_state: str
    current_state: str
    statement_id: str
    timestamp: datetime
    error: Optional[str] = None
    error_type: Optional[TransitionError] = None
    artifacts_created: List[str] = field(default_factory=list)
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransitionRequest:
    """Request to perform a state transition."""
    statement_id: str
    to_state: str
    trigger: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_types.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/types.py tests/state/test_types.py
git commit -m "feat: add transition result and request types"
```

---

### Task 3.3: Create State Controller Core Class

**Files:**
- Create: `src/bsie/state/controller.py`
- Test: `tests/state/test_controller.py`

**Step 1: Write the failing test**

```python
# tests/state/test_controller.py
"""State controller tests."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from bsie.state.controller import StateController
from bsie.state.constants import State
from bsie.state.types import TransitionResult, TransitionError


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def controller(mock_session):
    """Create a StateController instance."""
    return StateController(session=mock_session)


@pytest.mark.asyncio
async def test_validate_transition_valid(controller):
    """Valid transitions should pass validation."""
    is_valid = controller.validate_transition(State.UPLOADED, State.INGESTED)
    assert is_valid is True


@pytest.mark.asyncio
async def test_validate_transition_invalid(controller):
    """Invalid transitions should fail validation."""
    is_valid = controller.validate_transition(State.UPLOADED, State.COMPLETED)
    assert is_valid is False


@pytest.mark.asyncio
async def test_get_allowed_transitions(controller):
    """Should return allowed transitions for a state."""
    allowed = controller.get_allowed_transitions(State.ROUTED)
    assert State.TEMPLATE_SELECTED in allowed
    assert State.TEMPLATE_MISSING in allowed
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py -v`

Expected: FAIL with "cannot import name 'StateController'"

**Step 3: Write minimal implementation**

```python
# src/bsie/state/controller.py
"""State Controller - owns all pipeline state transitions."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set, List

from sqlalchemy.ext.asyncio import AsyncSession

from bsie.state.constants import (
    State,
    TRANSITION_MATRIX,
    STATE_REQUIRED_ARTIFACTS,
    get_allowed_transitions,
    is_valid_transition,
)
from bsie.state.types import TransitionResult, TransitionError, TransitionRequest


class StateController:
    """
    Centralized state controller for pipeline transitions.

    All state transitions MUST go through this controller.
    Workers and agents may NOT mutate state directly.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def validate_transition(self, from_state: State, to_state: State) -> bool:
        """Validate that a transition is allowed."""
        return is_valid_transition(from_state, to_state)

    def get_allowed_transitions(self, from_state: State) -> Set[State]:
        """Get the set of allowed target states from current state."""
        return get_allowed_transitions(from_state)

    def get_required_artifacts(self, to_state: State) -> List[str]:
        """Get required artifacts to enter a state."""
        return STATE_REQUIRED_ARTIFACTS.get(to_state, [])

    async def transition(
        self,
        statement_id: str,
        to_state: State,
        trigger: str,
        artifacts: Optional[Dict[str, Any]] = None,
        worker_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TransitionResult:
        """
        Attempt a state transition.

        Args:
            statement_id: Statement to transition
            to_state: Target state
            trigger: What triggered this transition
            artifacts: Artifacts to validate and store
            worker_id: ID of the worker performing the transition
            metadata: Additional metadata

        Returns:
            TransitionResult indicating success or failure
        """
        # Implementation will be added in subsequent tasks
        raise NotImplementedError("Full transition logic coming in Task 3.4")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py tests/state/test_controller.py
git commit -m "feat: add StateController core class with validation"
```

---

### Task 3.4: Implement State Lookup

**Files:**
- Modify: `src/bsie/state/controller.py`
- Modify: `tests/state/test_controller.py`

**Step 1: Write the failing test**

Add to `tests/state/test_controller.py`:

```python
from bsie.db.models import Statement


@pytest.fixture
async def db_session_with_statement(db_session):
    """Create a database session with a test statement."""
    stmt = Statement(
        id="stmt_test001",
        sha256="a" * 64,
        original_filename="test.pdf",
        file_size_bytes=1024,
        page_count=3,
        current_state="UPLOADED",
    )
    db_session.add(stmt)
    await db_session.commit()
    return db_session


@pytest.mark.asyncio
async def test_get_current_state(db_session_with_statement):
    """Should retrieve current state of a statement."""
    controller = StateController(session=db_session_with_statement)
    state = await controller.get_current_state("stmt_test001")
    assert state == State.UPLOADED


@pytest.mark.asyncio
async def test_get_current_state_not_found(db_session):
    """Should return None for non-existent statement."""
    controller = StateController(session=db_session)
    state = await controller.get_current_state("stmt_nonexistent")
    assert state is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py::test_get_current_state -v`

Expected: FAIL with "get_current_state" not implemented

**Step 3: Write implementation**

Update `src/bsie/state/controller.py`:

```python
from sqlalchemy import select
from bsie.db.models import Statement


class StateController:
    # ... existing code ...

    async def get_current_state(self, statement_id: str) -> Optional[State]:
        """Get the current state of a statement."""
        result = await self._session.execute(
            select(Statement.current_state).where(Statement.id == statement_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return State(row)

    async def get_statement(self, statement_id: str) -> Optional[Statement]:
        """Get a statement by ID."""
        result = await self._session.execute(
            select(Statement).where(Statement.id == statement_id)
        )
        return result.scalar_one_or_none()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py tests/state/test_controller.py
git commit -m "feat: add state lookup to StateController"
```

---

### Task 3.5: Implement Basic State Transition

**Files:**
- Modify: `src/bsie/state/controller.py`
- Modify: `tests/state/test_controller.py`

**Step 1: Write the failing test**

Add to `tests/state/test_controller.py`:

```python
@pytest.mark.asyncio
async def test_transition_success(db_session_with_statement):
    """Successful transition should update state."""
    controller = StateController(session=db_session_with_statement)

    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingestion_complete",
        artifacts={"ingest_receipt": {"statement_id": "stmt_test001"}},
    )

    assert result.success is True
    assert result.previous_state == "UPLOADED"
    assert result.current_state == "INGESTED"

    # Verify state was persisted
    new_state = await controller.get_current_state("stmt_test001")
    assert new_state == State.INGESTED


@pytest.mark.asyncio
async def test_transition_invalid(db_session_with_statement):
    """Invalid transition should fail."""
    controller = StateController(session=db_session_with_statement)

    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.COMPLETED,  # Invalid from UPLOADED
        trigger="test",
    )

    assert result.success is False
    assert result.error_type == TransitionError.INVALID_TRANSITION

    # Verify state was NOT changed
    current_state = await controller.get_current_state("stmt_test001")
    assert current_state == State.UPLOADED


@pytest.mark.asyncio
async def test_transition_not_found(db_session):
    """Transition on non-existent statement should fail."""
    controller = StateController(session=db_session)

    result = await controller.transition(
        statement_id="stmt_nonexistent",
        to_state=State.INGESTED,
        trigger="test",
    )

    assert result.success is False
    assert result.error_type == TransitionError.STATE_NOT_FOUND
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py::test_transition_success -v`

Expected: FAIL

**Step 3: Write implementation**

Update the `transition` method in `src/bsie/state/controller.py`:

```python
async def transition(
    self,
    statement_id: str,
    to_state: State,
    trigger: str,
    artifacts: Optional[Dict[str, Any]] = None,
    worker_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TransitionResult:
    """
    Attempt a state transition.
    """
    artifacts = artifacts or {}
    metadata = metadata or {}
    timestamp = datetime.now(timezone.utc)

    # Get current statement
    statement = await self.get_statement(statement_id)
    if statement is None:
        return TransitionResult(
            success=False,
            previous_state="UNKNOWN",
            current_state="UNKNOWN",
            statement_id=statement_id,
            timestamp=timestamp,
            error=f"Statement {statement_id} not found",
            error_type=TransitionError.STATE_NOT_FOUND,
        )

    from_state = State(statement.current_state)

    # Validate transition
    if not self.validate_transition(from_state, to_state):
        return TransitionResult(
            success=False,
            previous_state=from_state.value,
            current_state=from_state.value,
            statement_id=statement_id,
            timestamp=timestamp,
            error=f"Invalid transition: {from_state.value} -> {to_state.value}",
            error_type=TransitionError.INVALID_TRANSITION,
        )

    # Update state
    statement.current_state = to_state.value
    statement.state_version += 1

    await self._session.commit()

    return TransitionResult(
        success=True,
        previous_state=from_state.value,
        current_state=to_state.value,
        statement_id=statement_id,
        timestamp=timestamp,
        artifacts_created=list(artifacts.keys()),
        metadata=metadata,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py tests/state/test_controller.py
git commit -m "feat: implement basic state transitions"
```

---

### Task 3.6: Add Artifact Validation to Transitions

**Files:**
- Modify: `src/bsie/state/controller.py`
- Modify: `tests/state/test_controller.py`

**Step 1: Write the failing test**

Add to `tests/state/test_controller.py`:

```python
@pytest.mark.asyncio
async def test_transition_missing_required_artifact(db_session_with_statement):
    """Transition without required artifact should fail."""
    controller = StateController(session=db_session_with_statement)

    # INGESTED requires ingest_receipt artifact
    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingestion_complete",
        artifacts={},  # Missing required artifact
    )

    assert result.success is False
    assert result.error_type == TransitionError.MISSING_ARTIFACT
    assert "ingest_receipt" in result.error
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py::test_transition_missing_required_artifact -v`

Expected: FAIL (transition succeeds but should fail)

**Step 3: Write implementation**

Add artifact validation before state update in `transition()`:

```python
# In transition() method, after validating the transition is allowed:

# Check required artifacts
required_artifacts = self.get_required_artifacts(to_state)
missing = [a for a in required_artifacts if a not in artifacts]
if missing:
    return TransitionResult(
        success=False,
        previous_state=from_state.value,
        current_state=from_state.value,
        statement_id=statement_id,
        timestamp=timestamp,
        error=f"Missing required artifacts: {', '.join(missing)}",
        error_type=TransitionError.MISSING_ARTIFACT,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py
git commit -m "feat: add artifact validation to state transitions"
```

---

### Task 3.7: Add State History Recording

**Files:**
- Modify: `src/bsie/state/controller.py`
- Modify: `tests/state/test_controller.py`

**Step 1: Write the failing test**

Add to `tests/state/test_controller.py`:

```python
from sqlalchemy import select
from bsie.db.models import StateHistory


@pytest.mark.asyncio
async def test_transition_records_history(db_session_with_statement):
    """Successful transition should record history."""
    controller = StateController(session=db_session_with_statement)

    await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingestion_complete",
        artifacts={"ingest_receipt": {"statement_id": "stmt_test001"}},
        worker_id="worker_01",
    )

    # Check history was recorded
    result = await db_session_with_statement.execute(
        select(StateHistory).where(StateHistory.statement_id == "stmt_test001")
    )
    history = result.scalars().all()

    assert len(history) == 1
    assert history[0].from_state == "UPLOADED"
    assert history[0].to_state == "INGESTED"
    assert history[0].trigger == "ingestion_complete"
    assert history[0].worker_id == "worker_01"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py::test_transition_records_history -v`

Expected: FAIL

**Step 3: Write implementation**

Add history recording in `transition()` method:

```python
from bsie.db.models import StateHistory

# After updating state, before commit:
history_entry = StateHistory(
    statement_id=statement_id,
    from_state=from_state.value,
    to_state=to_state.value,
    trigger=trigger,
    worker_id=worker_id,
    artifacts_created=list(artifacts.keys()),
    metadata=metadata,
)
self._session.add(history_entry)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py
git commit -m "feat: record state transition history"
```

---

### Task 3.8: Add Optimistic Locking

**Files:**
- Modify: `src/bsie/state/controller.py`
- Modify: `tests/state/test_controller.py`

**Step 1: Write the failing test**

Add to `tests/state/test_controller.py`:

```python
@pytest.mark.asyncio
async def test_transition_with_expected_version(db_session_with_statement):
    """Transition should support optimistic locking."""
    controller = StateController(session=db_session_with_statement)

    # First transition should work with correct version
    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingestion_complete",
        artifacts={"ingest_receipt": {"statement_id": "stmt_test001"}},
        metadata={"expected_version": 1},
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_transition_stale_version(db_session_with_statement):
    """Transition with stale version should fail."""
    controller = StateController(session=db_session_with_statement)

    # First, do a successful transition to increment version
    await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="test",
        artifacts={"ingest_receipt": {}},
    )

    # Now try with old version - should fail
    result = await controller.transition(
        statement_id="stmt_test001",
        to_state=State.CLASSIFIED,
        trigger="test",
        artifacts={"classification": {}},
        metadata={"expected_version": 1},  # Old version
    )
    assert result.success is False
    assert result.error_type == TransitionError.CONCURRENT_MODIFICATION
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py::test_transition_stale_version -v`

Expected: FAIL

**Step 3: Write implementation**

Add version checking in `transition()`:

```python
# After getting statement, before validation:
expected_version = metadata.get("expected_version")
if expected_version is not None and statement.state_version != expected_version:
    return TransitionResult(
        success=False,
        previous_state=from_state.value,
        current_state=from_state.value,
        statement_id=statement_id,
        timestamp=timestamp,
        error=f"Version mismatch: expected {expected_version}, got {statement.state_version}",
        error_type=TransitionError.CONCURRENT_MODIFICATION,
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py
git commit -m "feat: add optimistic locking to state transitions"
```

---

### Task 3.9: Add Force Transition for Admin Override

**Files:**
- Modify: `src/bsie/state/controller.py`
- Modify: `tests/state/test_controller.py`

**Step 1: Write the failing test**

Add to `tests/state/test_controller.py`:

```python
@pytest.mark.asyncio
async def test_force_transition(db_session_with_statement):
    """Admin should be able to force invalid transitions."""
    controller = StateController(session=db_session_with_statement)

    # Force transition that would normally be invalid
    result = await controller.force_transition(
        statement_id="stmt_test001",
        to_state=State.COMPLETED,
        reason="Admin override for testing",
        actor="admin_user",
    )

    assert result.success is True
    assert result.current_state == "COMPLETED"
    assert "forced" in result.metadata.get("transition_type", "")


@pytest.mark.asyncio
async def test_force_transition_records_actor(db_session_with_statement):
    """Force transition should record who performed it."""
    controller = StateController(session=db_session_with_statement)

    await controller.force_transition(
        statement_id="stmt_test001",
        to_state=State.HUMAN_REVIEW_REQUIRED,
        reason="Manual escalation",
        actor="admin_user",
    )

    # Check history
    result = await db_session_with_statement.execute(
        select(StateHistory).where(StateHistory.statement_id == "stmt_test001")
    )
    history = result.scalar_one()
    assert history.metadata.get("actor") == "admin_user"
    assert history.metadata.get("reason") == "Manual escalation"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py::test_force_transition -v`

Expected: FAIL with "force_transition not found"

**Step 3: Write implementation**

Add to `StateController`:

```python
async def force_transition(
    self,
    statement_id: str,
    to_state: State,
    reason: str,
    actor: str,
) -> TransitionResult:
    """
    Force a state transition (admin override).

    This bypasses normal validation but still records full audit trail.
    """
    timestamp = datetime.now(timezone.utc)

    statement = await self.get_statement(statement_id)
    if statement is None:
        return TransitionResult(
            success=False,
            previous_state="UNKNOWN",
            current_state="UNKNOWN",
            statement_id=statement_id,
            timestamp=timestamp,
            error=f"Statement {statement_id} not found",
            error_type=TransitionError.STATE_NOT_FOUND,
        )

    from_state = State(statement.current_state)

    # Update state (no validation)
    statement.current_state = to_state.value
    statement.state_version += 1

    # Record history with override details
    history_entry = StateHistory(
        statement_id=statement_id,
        from_state=from_state.value,
        to_state=to_state.value,
        trigger="admin_force",
        metadata={
            "actor": actor,
            "reason": reason,
            "forced": True,
        },
    )
    self._session.add(history_entry)

    await self._session.commit()

    return TransitionResult(
        success=True,
        previous_state=from_state.value,
        current_state=to_state.value,
        statement_id=statement_id,
        timestamp=timestamp,
        metadata={"transition_type": "forced", "actor": actor},
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py
git commit -m "feat: add force_transition for admin overrides"
```

---

### Task 3.10: Add Get State History Method

**Files:**
- Modify: `src/bsie/state/controller.py`
- Modify: `tests/state/test_controller.py`

**Step 1: Write the failing test**

Add to `tests/state/test_controller.py`:

```python
@pytest.mark.asyncio
async def test_get_state_history(db_session_with_statement):
    """Should retrieve complete state history."""
    controller = StateController(session=db_session_with_statement)

    # Perform several transitions
    await controller.transition(
        statement_id="stmt_test001",
        to_state=State.INGESTED,
        trigger="ingest",
        artifacts={"ingest_receipt": {}},
    )
    await controller.transition(
        statement_id="stmt_test001",
        to_state=State.CLASSIFIED,
        trigger="classify",
        artifacts={"classification": {}},
    )

    # Get history
    history = await controller.get_state_history("stmt_test001")

    assert len(history) == 2
    assert history[0].from_state == "UPLOADED"
    assert history[0].to_state == "INGESTED"
    assert history[1].from_state == "INGESTED"
    assert history[1].to_state == "CLASSIFIED"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py::test_get_state_history -v`

Expected: FAIL

**Step 3: Write implementation**

Add to `StateController`:

```python
async def get_state_history(self, statement_id: str) -> List[StateHistory]:
    """Get complete state transition history for a statement."""
    result = await self._session.execute(
        select(StateHistory)
        .where(StateHistory.statement_id == statement_id)
        .order_by(StateHistory.created_at)
    )
    return list(result.scalars().all())
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py
git commit -m "feat: add get_state_history method"
```

---

### Task 3.11: Create Initial State Setter

**Files:**
- Modify: `src/bsie/state/controller.py`
- Modify: `tests/state/test_controller.py`

**Step 1: Write the failing test**

Add to `tests/state/test_controller.py`:

```python
@pytest.mark.asyncio
async def test_create_initial_state(db_session):
    """Should create statement with initial UPLOADED state."""
    controller = StateController(session=db_session)

    statement = await controller.create_statement(
        statement_id="stmt_new001",
        sha256="b" * 64,
        original_filename="new.pdf",
        file_size_bytes=2048,
        page_count=5,
    )

    assert statement.id == "stmt_new001"
    assert statement.current_state == State.UPLOADED.value
    assert statement.state_version == 1

    # Verify we can get it
    state = await controller.get_current_state("stmt_new001")
    assert state == State.UPLOADED
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/state/test_controller.py::test_create_initial_state -v`

Expected: FAIL

**Step 3: Write implementation**

Add to `StateController`:

```python
async def create_statement(
    self,
    statement_id: str,
    sha256: str,
    original_filename: str,
    file_size_bytes: int,
    page_count: int,
    storage_path: Optional[str] = None,
) -> Statement:
    """
    Create a new statement with initial UPLOADED state.

    This is the ONLY way to create a statement - ensures
    proper initial state.
    """
    statement = Statement(
        id=statement_id,
        sha256=sha256,
        original_filename=original_filename,
        file_size_bytes=file_size_bytes,
        page_count=page_count,
        storage_path=storage_path,
        current_state=State.UPLOADED.value,
        state_version=1,
    )
    self._session.add(statement)

    # Record initial state in history
    history_entry = StateHistory(
        statement_id=statement_id,
        from_state=None,
        to_state=State.UPLOADED.value,
        trigger="upload",
    )
    self._session.add(history_entry)

    await self._session.commit()
    return statement
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/state/test_controller.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/state/controller.py
git commit -m "feat: add create_statement for initial state"
```

---

### Task 3.12-3.18: Remaining State Controller Tasks

Due to space constraints, the remaining tasks follow the same TDD pattern:

- **Task 3.12:** Add artifact storage path tracking
- **Task 3.13:** Add template binding on TEMPLATE_SELECTED
- **Task 3.14:** Add error tracking on failure states
- **Task 3.15:** Add timeout handling
- **Task 3.16:** Export StateController from package
- **Task 3.17:** Add StateController dependency injection
- **Task 3.18:** Run full test suite and verify Sprint 3 complete

Each task follows the same structure:
1. Write failing test
2. Run test to verify failure
3. Write minimal implementation
4. Run test to verify pass
5. Commit

---

## Sprint 3 Complete

**Milestone Achieved:**
- StateController with full transition logic
- Transition validation against matrix
- Required artifact checking
- State history recording
- Optimistic locking for concurrency
- Admin force_transition override
- Initial state creation

**Next:** Sprint 4 - Template Registry

---

## Sprint 4: Template Registry (16 tasks)

**Goal:** Implement Git+Postgres hybrid template storage with TOML parsing and validation.

**Milestone:** Templates loadable from filesystem, metadata queryable from Postgres, version tracking working.

**Reference:** `/Users/brian/dev/BSIE/template_adapter_v2.md`, `/Users/brian/dev/BSIE/decisions_v2.md`

---

### Task 4.1: Create Template Database Model

**Files:**
- Create: `src/bsie/db/models/template.py`
- Modify: `src/bsie/db/models/__init__.py`
- Test: `tests/db/test_template_model.py`

**Step 1: Write the failing test**

```python
# tests/db/test_template_model.py
"""Template model tests."""
import pytest
from datetime import datetime, timezone

from bsie.db.models import TemplateMetadata


def test_template_metadata_model():
    meta = TemplateMetadata(
        template_id="chase_checking_v1",
        version="1.0.0",
        bank_family="chase",
        statement_type="checking",
        segment="personal",
        git_sha="abc123",
        file_path="templates/chase/checking_personal_v1.toml",
        status="stable",
    )
    assert meta.template_id == "chase_checking_v1"
    assert meta.status == "stable"


@pytest.mark.asyncio
async def test_template_metadata_persistence(db_session):
    meta = TemplateMetadata(
        template_id="chase_checking_v1",
        version="1.0.0",
        bank_family="chase",
        statement_type="checking",
        segment="personal",
        git_sha="abc123",
        file_path="templates/chase/checking_personal_v1.toml",
        status="stable",
    )
    db_session.add(meta)
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(
        select(TemplateMetadata).where(TemplateMetadata.template_id == "chase_checking_v1")
    )
    loaded = result.scalar_one()
    assert loaded.bank_family == "chase"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_template_model.py -v`

Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/bsie/db/models/template.py
"""Template metadata model."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column

from bsie.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TemplateMetadata(Base):
    """Template metadata for Postgres queries."""

    __tablename__ = "template_metadata"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Template identification
    template_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(32))
    bank_family: Mapped[str] = mapped_column(String(64), index=True)
    statement_type: Mapped[str] = mapped_column(String(32), index=True)
    segment: Mapped[str] = mapped_column(String(32), index=True)

    # Git tracking
    git_sha: Mapped[str] = mapped_column(String(40))
    file_path: Mapped[str] = mapped_column(String(512))

    # Status
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft, stable, deprecated

    # Statistics
    statements_processed: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    promoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

Update `src/bsie/db/models/__init__.py`:

```python
from bsie.db.models.template import TemplateMetadata
__all__ = ["Statement", "StateHistory", "TemplateMetadata"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_template_model.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/db/models/template.py tests/db/test_template_model.py
git commit -m "feat: add TemplateMetadata database model"
```

---

### Task 4.2: Create Template Pydantic Schema

**Files:**
- Create: `src/bsie/templates/__init__.py`
- Create: `src/bsie/templates/schema.py`
- Test: `tests/templates/__init__.py`
- Test: `tests/templates/test_schema.py`

**Step 1: Write the failing test**

```python
# tests/templates/__init__.py
"""Template tests."""
```

```python
# tests/templates/test_schema.py
"""Template schema tests."""
import pytest
from pydantic import ValidationError

from bsie.templates.schema import (
    TemplateMetadataSection,
    TemplateDetectSection,
    Template,
)


def test_metadata_section_valid():
    meta = TemplateMetadataSection(
        template_id="chase_checking_v1",
        version="1.0.0",
        bank_family="chase",
        statement_type="checking",
        segment="personal",
    )
    assert meta.template_id == "chase_checking_v1"


def test_metadata_section_requires_fields():
    with pytest.raises(ValidationError):
        TemplateMetadataSection(
            template_id="test",
            # Missing required fields
        )


def test_detect_section():
    detect = TemplateDetectSection(
        keywords=["CHASE", "JPMorgan"],
        required_text=["Account Activity"],
    )
    assert len(detect.keywords) == 2


def test_template_minimal():
    template = Template(
        metadata=TemplateMetadataSection(
            template_id="test_v1",
            version="1.0.0",
            bank_family="test",
            statement_type="checking",
            segment="personal",
        ),
        detect=TemplateDetectSection(
            keywords=["TEST"],
        ),
    )
    assert template.metadata.template_id == "test_v1"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/templates/test_schema.py -v`

Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/bsie/templates/__init__.py
"""Template package."""
```

```python
# src/bsie/templates/schema.py
"""Template Pydantic schema matching TOML structure."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TemplateMetadataSection(BaseModel):
    """Template metadata section."""
    template_id: str
    version: str
    bank_family: str
    statement_type: str  # checking, savings, credit_card
    segment: str  # personal, business, unknown
    description: Optional[str] = None


class TemplateDetectSection(BaseModel):
    """Template detection section."""
    keywords: List[str] = Field(default_factory=list)
    keyword_match_threshold: int = 1
    header_patterns: List[str] = Field(default_factory=list)
    required_text: List[str] = Field(default_factory=list)
    negative_patterns: List[str] = Field(default_factory=list)
    detect_pages: List[int] = Field(default_factory=lambda: [1])


class TemplateTableSection(BaseModel):
    """Template table location section."""
    primary: Optional[Dict[str, Any]] = None
    multi_page: Optional[Dict[str, Any]] = None


class TemplateColumnsSection(BaseModel):
    """Template column mapping section."""
    expected_count: Optional[int] = None
    map: Dict[str, str] = Field(default_factory=dict)


class Template(BaseModel):
    """Complete template schema."""
    metadata: TemplateMetadataSection
    detect: TemplateDetectSection
    preprocess: Optional[Dict[str, Any]] = None
    table: Optional[TemplateTableSection] = None
    extraction: Optional[Dict[str, Any]] = None
    columns: Optional[TemplateColumnsSection] = None
    parsing: Optional[Dict[str, Any]] = None
    normalization: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/templates/test_schema.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/templates/ tests/templates/
git commit -m "feat: add Template Pydantic schema"
```

---

### Task 4.3: Create TOML Parser

**Files:**
- Create: `src/bsie/templates/parser.py`
- Test: `tests/templates/test_parser.py`

**Step 1: Write the failing test**

```python
# tests/templates/test_parser.py
"""Template parser tests."""
import pytest
from pathlib import Path

from bsie.templates.parser import parse_template, TemplateParseError


def test_parse_template_from_string():
    toml_content = '''
[metadata]
template_id = "test_checking_v1"
version = "1.0.0"
bank_family = "test_bank"
statement_type = "checking"
segment = "personal"

[detect]
keywords = ["TEST BANK"]
required_text = ["Account Activity"]
'''
    template = parse_template(toml_content)
    assert template.metadata.template_id == "test_checking_v1"
    assert template.metadata.bank_family == "test_bank"
    assert "TEST BANK" in template.detect.keywords


def test_parse_template_missing_metadata():
    toml_content = '''
[detect]
keywords = ["TEST"]
'''
    with pytest.raises(TemplateParseError) as exc:
        parse_template(toml_content)
    assert "metadata" in str(exc.value).lower()


def test_parse_template_from_file(tmp_path):
    template_file = tmp_path / "test.toml"
    template_file.write_text('''
[metadata]
template_id = "file_test_v1"
version = "1.0.0"
bank_family = "test"
statement_type = "checking"
segment = "personal"

[detect]
keywords = ["TEST"]
''')
    template = parse_template(template_file)
    assert template.metadata.template_id == "file_test_v1"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/templates/test_parser.py -v`

Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/bsie/templates/parser.py
"""TOML template parser."""
from pathlib import Path
from typing import Union

import toml
from pydantic import ValidationError

from bsie.templates.schema import Template


class TemplateParseError(Exception):
    """Error parsing template."""
    pass


def parse_template(source: Union[str, Path]) -> Template:
    """
    Parse a template from TOML string or file path.

    Args:
        source: TOML string or path to TOML file

    Returns:
        Validated Template object

    Raises:
        TemplateParseError: If parsing or validation fails
    """
    try:
        if isinstance(source, Path):
            with open(source, "r") as f:
                data = toml.load(f)
        else:
            data = toml.loads(source)
    except toml.TomlDecodeError as e:
        raise TemplateParseError(f"Invalid TOML: {e}") from e

    try:
        return Template.model_validate(data)
    except ValidationError as e:
        raise TemplateParseError(f"Template validation failed: {e}") from e
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/templates/test_parser.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/templates/parser.py tests/templates/test_parser.py
git commit -m "feat: add TOML template parser"
```

---

### Task 4.4-4.16: Remaining Template Registry Tasks

The remaining tasks follow the same TDD pattern:

- **Task 4.4:** Create TemplateRegistry class
- **Task 4.5:** Implement template loading from filesystem
- **Task 4.6:** Implement template metadata sync to Postgres
- **Task 4.7:** Implement get_template_by_id
- **Task 4.8:** Implement find_templates_for_classification
- **Task 4.9:** Implement template version comparison
- **Task 4.10:** Add template validation on load
- **Task 4.11:** Add template caching
- **Task 4.12:** Add template statistics tracking
- **Task 4.13:** Export TemplateRegistry from package
- **Task 4.14:** Add TemplateRegistry dependency injection
- **Task 4.15:** Create sample Chase template fixture
- **Task 4.16:** Run full test suite and verify Sprint 4 complete

---

## Sprint 4 Complete

**Milestone Achieved:**
- Template Pydantic schema matching TOML structure
- TOML parser with validation
- TemplateMetadata database model
- TemplateRegistry with filesystem loading
- Template lookup by classification
- Version tracking

**Next:** Sprint 5 - Ingest Pipeline

---

## Sprint 5: Ingest Pipeline (15 tasks)

**Goal:** Implement PDF upload through INGESTED state with full provenance.

**Milestone:** PDF upload endpoint working, files stored, ingest_receipt generated, state transitions complete.

**Reference:** `/Users/brian/dev/BSIE/prd_v2.md`, `/Users/brian/dev/BSIE/pipeline_state_machine_v2.md`

---

### Task 5.1: Create Ingest Service

**Files:**
- Create: `src/bsie/services/__init__.py`
- Create: `src/bsie/services/ingest.py`
- Test: `tests/services/__init__.py`
- Test: `tests/services/test_ingest.py`

**Step 1: Write the failing test**

```python
# tests/services/__init__.py
"""Service tests."""
```

```python
# tests/services/test_ingest.py
"""Ingest service tests."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from bsie.services.ingest import IngestService
from bsie.schemas import IngestReceipt


@pytest.fixture
def ingest_service(db_session, tmp_path):
    from bsie.storage import StoragePaths
    from bsie.state.controller import StateController

    storage = StoragePaths(base_path=tmp_path)
    controller = StateController(session=db_session)
    return IngestService(
        session=db_session,
        storage=storage,
        state_controller=controller,
    )


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal PDF for testing."""
    pdf_path = tmp_path / "sample.pdf"
    # Minimal PDF content
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
    return pdf_path


@pytest.mark.asyncio
async def test_ingest_creates_statement(ingest_service, sample_pdf):
    """Ingesting PDF should create statement record."""
    result = await ingest_service.ingest(
        file_path=sample_pdf,
        original_filename="test_statement.pdf",
    )

    assert result.statement_id.startswith("stmt_")
    assert result.stored is True
    assert result.pages >= 1


@pytest.mark.asyncio
async def test_ingest_computes_sha256(ingest_service, sample_pdf):
    """Ingest should compute SHA256 of file."""
    result = await ingest_service.ingest(
        file_path=sample_pdf,
        original_filename="test.pdf",
    )

    assert len(result.sha256) == 64
    assert result.sha256.isalnum()


@pytest.mark.asyncio
async def test_ingest_stores_file(ingest_service, sample_pdf, tmp_path):
    """Ingest should copy file to storage."""
    result = await ingest_service.ingest(
        file_path=sample_pdf,
        original_filename="test.pdf",
    )

    # Verify file exists in storage
    stored_path = tmp_path / "pdfs" / f"{result.statement_id}.pdf"
    assert stored_path.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_ingest.py -v`

Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/bsie/services/__init__.py
"""Business logic services."""
```

```python
# src/bsie/services/ingest.py
"""PDF ingestion service."""
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from bsie.schemas import IngestReceipt
from bsie.state.controller import StateController
from bsie.state.constants import State
from bsie.storage import StoragePaths
from bsie.utils import generate_statement_id, compute_sha256


class IngestService:
    """Service for ingesting PDF statements."""

    def __init__(
        self,
        session: AsyncSession,
        storage: StoragePaths,
        state_controller: StateController,
    ):
        self._session = session
        self._storage = storage
        self._state_controller = state_controller

    async def ingest(
        self,
        file_path: Path,
        original_filename: str,
        uploaded_by: Optional[str] = None,
    ) -> IngestReceipt:
        """
        Ingest a PDF file.

        1. Generate statement_id
        2. Compute SHA256
        3. Copy to storage
        4. Get page count
        5. Create statement record (UPLOADED state)
        6. Transition to INGESTED with ingest_receipt
        """
        statement_id = generate_statement_id()
        sha256 = compute_sha256(file_path)
        file_size = file_path.stat().st_size

        # Copy to storage
        storage_path = self._storage.get_pdf_path(statement_id)
        shutil.copy2(file_path, storage_path)

        # Get page count (simplified - would use pypdf in real impl)
        page_count = self._get_page_count(storage_path)

        # Create statement in UPLOADED state
        await self._state_controller.create_statement(
            statement_id=statement_id,
            sha256=sha256,
            original_filename=original_filename,
            file_size_bytes=file_size,
            page_count=page_count,
            storage_path=str(storage_path),
        )

        # Create ingest receipt
        receipt = IngestReceipt(
            statement_id=statement_id,
            sha256=sha256,
            pages=page_count,
            stored=True,
            original_path=str(file_path),
            uploaded_at=datetime.now(timezone.utc),
            file_size_bytes=file_size,
            original_filename=original_filename,
            uploaded_by=uploaded_by,
        )

        # Save receipt artifact
        receipt_path = self._storage.get_artifact_path(statement_id, "ingest_receipt.json")
        receipt_path.write_text(receipt.model_dump_json(indent=2))

        # Transition to INGESTED
        await self._state_controller.transition(
            statement_id=statement_id,
            to_state=State.INGESTED,
            trigger="ingestion_complete",
            artifacts={"ingest_receipt": receipt.model_dump()},
        )

        return receipt

    def _get_page_count(self, pdf_path: Path) -> int:
        """Get page count from PDF. Simplified implementation."""
        # In real implementation, use pypdf
        # For now, return 1
        return 1
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_ingest.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/bsie/services/ tests/services/
git commit -m "feat: add IngestService for PDF ingestion"
```

---

### Task 5.2: Add PDF Page Count with pypdf

**Files:**
- Modify: `pyproject.toml` (add pypdf dependency)
- Modify: `src/bsie/services/ingest.py`
- Modify: `tests/services/test_ingest.py`

**Step 1: Add dependency**

Add `pypdf>=4.0.0` to pyproject.toml dependencies.

**Step 2: Update implementation**

```python
from pypdf import PdfReader

def _get_page_count(self, pdf_path: Path) -> int:
    """Get page count from PDF."""
    reader = PdfReader(pdf_path)
    return len(reader.pages)
```

**Step 3: Update test to use real PDF**

Create a proper test PDF fixture using pypdf.

**Step 4: Run tests**

**Step 5: Commit**

---

### Task 5.3: Create Upload API Endpoint

**Files:**
- Create: `src/bsie/api/routes/statements.py`
- Modify: `src/bsie/api/app.py`
- Test: `tests/api/test_statements.py`

**Step 1: Write the failing test**

```python
# tests/api/test_statements.py
"""Statement API tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path

from bsie.api.app import create_app


@pytest.fixture
def app():
    return create_app(database_url="sqlite+aiosqlite:///:memory:")


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_pdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
    return pdf_path


@pytest.mark.asyncio
async def test_upload_pdf(client, sample_pdf):
    """POST /api/v1/statements should accept PDF upload."""
    with open(sample_pdf, "rb") as f:
        response = await client.post(
            "/api/v1/statements",
            files={"file": ("test.pdf", f, "application/pdf")},
        )

    assert response.status_code == 201
    data = response.json()
    assert "statement_id" in data
    assert data["statement_id"].startswith("stmt_")
```

**Step 2: Run test to verify it fails**

**Step 3: Write implementation**

```python
# src/bsie/api/routes/statements.py
"""Statement API routes."""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import tempfile
from pathlib import Path

from bsie.api.deps import get_db
from bsie.services.ingest import IngestService
from bsie.storage import StoragePaths
from bsie.state.controller import StateController
from bsie.config import get_settings

router = APIRouter(prefix="/api/v1/statements", tags=["statements"])


@router.post("", status_code=201)
async def upload_statement(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF statement for processing."""
    if not file.filename.lower().endswith(".pdf"):
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
        receipt = await service.ingest(
            file_path=tmp_path,
            original_filename=file.filename,
        )
        return {
            "statement_id": receipt.statement_id,
            "sha256": receipt.sha256,
            "pages": receipt.pages,
            "status": "INGESTED",
        }
    finally:
        tmp_path.unlink(missing_ok=True)
```

**Step 4: Run tests**

**Step 5: Commit**

---

### Task 5.4-5.15: Remaining Ingest Pipeline Tasks

- **Task 5.4:** Add duplicate detection (same SHA256)
- **Task 5.5:** Add file validation (must be valid PDF)
- **Task 5.6:** Add has_text_layer detection
- **Task 5.7:** Add GET /statements/{id} endpoint
- **Task 5.8:** Add GET /statements/{id}/state endpoint
- **Task 5.9:** Add GET /statements/{id}/artifacts endpoint
- **Task 5.10:** Add pagination to GET /statements
- **Task 5.11:** Add WebSocket notification on state change
- **Task 5.12:** Export IngestService from package
- **Task 5.13:** Add integration tests
- **Task 5.14:** Add error handling for disk full
- **Task 5.15:** Run full test suite and verify Sprint 5 complete

---

## Sprint 5 Complete

**Milestone Achieved:**
- IngestService for PDF processing
- Upload endpoint with validation
- SHA256 deduplication
- File storage with path tracking
- Ingest receipt generation
- State transitions (UPLOADED -> INGESTED)
- API endpoints for statement queries

---

## P0 Implementation Complete

**All Milestones Achieved:**

| Sprint | Focus | Status |
|--------|-------|--------|
| 1 | Project Foundation | Ready |
| 2 | Schema Validation | Ready |
| 3 | State Controller | Ready |
| 4 | Template Registry | Ready |
| 5 | Ingest Pipeline | Ready |

**Total: 78 tasks across 5 sprints**

**Next Steps After P0:**
1. Implement Classification pipeline
2. Implement Extraction Engine
3. Implement Reconciliation
4. Implement Human Review UI

---

End of P0 Implementation Plan
