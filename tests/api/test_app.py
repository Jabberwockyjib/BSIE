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
