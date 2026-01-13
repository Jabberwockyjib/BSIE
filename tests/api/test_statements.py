"""Statement API tests."""
import pytest
from contextlib import asynccontextmanager
from io import BytesIO
from httpx import AsyncClient, ASGITransport

from bsie.api.app import create_app
from bsie.api.deps import init_db
from bsie.db.engine import create_engine
from bsie.db.base import Base


@pytest.fixture
async def app(tmp_path):
    """Create test app with temporary storage."""
    import bsie.config as config_module
    from bsie.config import Settings

    # Override settings with temp storage path
    config_module._settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        storage_path=tmp_path,
    )

    app = create_app(database_url="sqlite+aiosqlite:///:memory:")

    # Manually initialize the database (normally done in lifespan)
    engine = app.state.engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    init_db(engine)

    yield app

    # Cleanup
    await engine.dispose()
    config_module._settings = None


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def minimal_pdf():
    """Minimal valid PDF content."""
    # This is a minimal but valid PDF structure
    return b"""%PDF-1.4
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


@pytest.mark.asyncio
async def test_upload_pdf(client, minimal_pdf):
    """POST /api/v1/statements should accept PDF upload."""
    files = {"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}
    response = await client.post("/api/v1/statements", files=files)

    assert response.status_code == 201
    data = response.json()
    assert "statement_id" in data
    assert data["statement_id"].startswith("stmt_")
    assert "sha256" in data
    assert data["status"] == "INGESTED"


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client):
    """POST /api/v1/statements should reject non-PDF files."""
    files = {"file": ("test.txt", BytesIO(b"not a pdf"), "text/plain")}
    response = await client.post("/api/v1/statements", files=files)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_duplicate_detection(client, minimal_pdf):
    """POST /api/v1/statements should detect duplicates."""
    files = {"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}

    # First upload
    response1 = await client.post("/api/v1/statements", files=files)
    assert response1.status_code == 201

    # Second upload of same content
    files2 = {"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}
    response2 = await client.post("/api/v1/statements", files=files2)
    assert response2.status_code == 409
    assert "Duplicate" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_get_statement(client, minimal_pdf):
    """GET /api/v1/statements/{id} should return statement details."""
    # First upload
    files = {"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}
    upload_response = await client.post("/api/v1/statements", files=files)
    statement_id = upload_response.json()["statement_id"]

    # Then get
    response = await client.get(f"/api/v1/statements/{statement_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["statement_id"] == statement_id
    assert data["original_filename"] == "test.pdf"
    assert data["state"] == "INGESTED"


@pytest.mark.asyncio
async def test_get_statement_not_found(client):
    """GET /api/v1/statements/{id} should return 404 for unknown ID."""
    response = await client.get("/api/v1/statements/stmt_nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_statement_state(client, minimal_pdf):
    """GET /api/v1/statements/{id}/state should return state info."""
    files = {"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}
    upload_response = await client.post("/api/v1/statements", files=files)
    statement_id = upload_response.json()["statement_id"]

    response = await client.get(f"/api/v1/statements/{statement_id}/state")

    assert response.status_code == 200
    data = response.json()
    assert data["statement_id"] == statement_id
    assert data["current_state"] == "INGESTED"
    assert "version" in data


@pytest.mark.asyncio
async def test_get_statement_artifacts(client, minimal_pdf):
    """GET /api/v1/statements/{id}/artifacts should return artifact list."""
    files = {"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}
    upload_response = await client.post("/api/v1/statements", files=files)
    statement_id = upload_response.json()["statement_id"]

    response = await client.get(f"/api/v1/statements/{statement_id}/artifacts")

    assert response.status_code == 200
    data = response.json()
    assert data["statement_id"] == statement_id
    assert "artifacts" in data
    # Should have ingest_receipt artifact
    artifact_names = [a["name"] for a in data["artifacts"]]
    assert "ingest_receipt.json" in artifact_names


@pytest.mark.asyncio
async def test_list_statements_empty(client):
    """GET /api/v1/statements should return empty list initially."""
    response = await client.get("/api/v1/statements")

    assert response.status_code == 200
    data = response.json()
    assert data["statements"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_statements_with_data(client, minimal_pdf):
    """GET /api/v1/statements should return uploaded statements."""
    # Upload a statement
    files = {"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}
    await client.post("/api/v1/statements", files=files)

    response = await client.get("/api/v1/statements")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["statements"]) == 1


@pytest.mark.asyncio
async def test_list_statements_pagination(client, minimal_pdf):
    """GET /api/v1/statements should support pagination."""
    response = await client.get("/api/v1/statements?page=1&page_size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_list_statements_filter_by_state(client, minimal_pdf):
    """GET /api/v1/statements should filter by state."""
    # Upload a statement
    files = {"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}
    await client.post("/api/v1/statements", files=files)

    # Filter by INGESTED - should find it
    response = await client.get("/api/v1/statements?state=INGESTED")
    assert response.status_code == 200
    assert response.json()["total"] == 1

    # Filter by COMPLETED - should not find it
    response = await client.get("/api/v1/statements?state=COMPLETED")
    assert response.status_code == 200
    assert response.json()["total"] == 0
